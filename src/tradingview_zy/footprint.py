"""成交量足迹（Volume Footprint）数据聚合。

把低一级频率的子K线按价格分箱，聚合出每根显示K线内部的分价成交量。
纯计算模块，不依赖 Flask 与交易所对象，便于单元测试。

时间戳约定（已用 TDX 真实数据验证）：所有频率的 K 线 date 均为"段尾"时刻
（日线也带 15:00），因此子K线归属显示K线的规则统一为
prev_display_date < sub_date <= display_date。

注意：TDX 部分品种（如指数）不同频率的成交量单位不一致，
分价量只保证与子K线自身守恒，渲染端只应使用 bar 内的相对比例。
"""

from __future__ import annotations

import math
import threading
import time

import numpy as np
import pandas as pd

from tradingview_zy.web_payloads import _datetime_to_timestamp_seconds

# 显示频率 -> 聚合用的子频率。未列出的频率不支持足迹。
# 子频率的选择在"分价粒度"与"历史覆盖深度"（交易所仅缓存约 5600 根）间权衡。
SUB_FREQUENCY_MAP = {
    "y": "d",
    "m": "d",
    "w": "60m",
    "d": "5m",
    "120m": "5m",
    "60m": "5m",
    "30m": "5m",
    "15m": "1m",
    "10m": "1m",
    "5m": "1m",
}

# 每根显示K线的目标分箱行数
DEFAULT_ROWS = 18


def nice_tick(raw: float) -> float:
    """把原始分箱高度归整为 1/2/5 x 10^n 系列中不小于 raw 的最小值。"""
    if raw <= 0:
        return 0.01
    exp = math.floor(math.log10(raw))
    base = 10**exp
    for m in (1, 2, 5, 10):
        if m * base >= raw - 1e-12:
            return round(m * base, 10)
    return round(10 * base, 10)  # 数值兜底，逻辑上不可达


def _bin_sub_bar(bar_rows: dict, base: float, tick: float, low: float, high: float, volume: float, is_buy: bool):
    """把一根子K线的成交量按价格区间摊到各分箱，bin key 为整数下标。"""
    k_low = int(math.floor((low - base) / tick + 1e-9))
    k_high = int(math.floor((high - base) / tick + 1e-9))
    span = high - low
    for k in range(k_low, k_high + 1):
        if span <= 0:
            share = volume  # 一字子K线，全部记入所在分箱
        else:
            seg_low = max(low, base + k * tick)
            seg_high = min(high, base + (k + 1) * tick)
            share = volume * max(0.0, seg_high - seg_low) / span
        if share <= 0:
            continue
        cell = bar_rows.setdefault(k, [0.0, 0.0])
        cell[0 if is_buy else 1] += share


def aggregate_footprint(
    display_klines: pd.DataFrame | None,
    sub_klines: pd.DataFrame | None,
    rows: int = DEFAULT_ROWS,
) -> dict[int, dict]:
    """聚合分价成交量。

    返回 {显示K线时间戳(秒): {"tick": 分箱高度, "rows": [{"p": 箱底价, "vb": 买量, "vs": 卖量}, ...]}}
    rows 按价格从低到高排列；没有子数据覆盖的显示K线不出现在结果中。
    """
    if display_klines is None or len(display_klines) == 0:
        return {}
    if sub_klines is None or len(sub_klines) == 0:
        return {}

    display_dates = display_klines["date"].to_numpy()
    sub_dates = sub_klines["date"].to_numpy()
    # 段尾时间戳约定下，子K线归属第一个 date >= sub_date 的显示K线
    owners = np.searchsorted(display_dates, sub_dates, side="left")

    result: dict[int, dict] = {}
    sub_open = sub_klines["open"].to_numpy(dtype=float)
    sub_close = sub_klines["close"].to_numpy(dtype=float)
    sub_low = sub_klines["low"].to_numpy(dtype=float)
    sub_high = sub_klines["high"].to_numpy(dtype=float)
    sub_volume = sub_klines["volume"].to_numpy(dtype=float)

    for owner_idx in np.unique(owners):
        if owner_idx >= len(display_dates):
            continue  # 子K线晚于最后一根显示K线，数据异常，丢弃
        mask = owners == owner_idx
        lo = float(sub_low[mask].min())
        hi = float(sub_high[mask].max())
        tick = nice_tick((hi - lo) / rows) if hi > lo else nice_tick(abs(hi) * 0.001)
        base = math.floor(lo / tick) * tick

        bar_rows: dict[int, list[float]] = {}
        for i in np.flatnonzero(mask):
            _bin_sub_bar(
                bar_rows,
                base,
                tick,
                float(sub_low[i]),
                float(sub_high[i]),
                float(sub_volume[i]),
                is_buy=sub_close[i] >= sub_open[i],
            )

        ts = _datetime_to_timestamp_seconds(display_klines.iloc[int(owner_idx)]["date"])
        result[ts] = {
            "tick": tick,
            "rows": [
                {
                    "p": round(base + k * tick, 6),
                    "vb": round(vb, 3),
                    "vs": round(vs, 3),
                }
                for k, (vb, vs) in sorted(bar_rows.items())
            ],
        }
    return result


class TTLCache:
    """带过期时间的简易缓存，避免频繁重复拉取子K线与聚合计算。"""

    def __init__(self, ttl_seconds: float = 10.0, clock=time.monotonic):
        self.ttl = ttl_seconds
        self._clock = clock
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            saved_at, value = item
            if self._clock() - saved_at > self.ttl:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key, value):
        with self._lock:
            self._data[key] = (self._clock(), value)
