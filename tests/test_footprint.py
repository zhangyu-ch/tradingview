import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradingview_zy.footprint import (
    DEFAULT_ROWS,
    SUB_FREQUENCY_MAP,
    TTLCache,
    aggregate_footprint,
    nice_tick,
)


def _klines(rows):
    """rows: [(date_str, open, high, low, close, volume), ...]"""
    df = pd.DataFrame(
        rows, columns=["date", "open", "high", "low", "close", "volume"]
    )
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize("Asia/Shanghai")
    return df


def _ts(date_str):
    return int(pd.Timestamp(date_str, tz="Asia/Shanghai").timestamp())


def test_nice_tick_snaps_to_1_2_5_series():
    assert nice_tick(0.013) == 0.02
    assert nice_tick(0.02) == 0.02
    assert nice_tick(0.04) == 0.05
    assert nice_tick(0.9) == 1
    assert nice_tick(3) == 5
    assert nice_tick(0) == 0.01  # 兜底


def test_sub_bars_assigned_by_end_timestamp():
    # 段尾约定：显示K线 10:00 拥有 (09:00, 10:00] 的子K线
    display = _klines(
        [
            ("2026-07-30 10:00", 10, 11, 9, 10.5, 300),
            ("2026-07-30 11:00", 10.5, 12, 10, 11, 200),
        ]
    )
    sub = _klines(
        [
            ("2026-07-30 09:30", 10, 10.5, 9.5, 10.2, 100),
            ("2026-07-30 10:00", 10.2, 11, 9, 10.5, 200),  # 边界：归属第一根
            ("2026-07-30 10:30", 10.5, 12, 10, 11, 200),
        ]
    )
    result = aggregate_footprint(display, sub)
    assert set(result.keys()) == {_ts("2026-07-30 10:00"), _ts("2026-07-30 11:00")}
    bar1 = result[_ts("2026-07-30 10:00")]
    total1 = sum(r["vb"] + r["vs"] for r in bar1["rows"])
    assert total1 == pytest.approx(300)  # 前两根子K线
    bar2 = result[_ts("2026-07-30 11:00")]
    total2 = sum(r["vb"] + r["vs"] for r in bar2["rows"])
    assert total2 == pytest.approx(200)


def test_volume_conserved_and_prices_within_range():
    display = _klines([("2026-07-30 15:00", 10, 12, 9, 11, 1000)])
    sub = _klines(
        [
            ("2026-07-30 09:35", 10.0, 10.8, 9.0, 10.5, 400),
            ("2026-07-30 09:40", 10.5, 12.0, 10.2, 11.8, 350),
            ("2026-07-30 09:45", 11.8, 11.9, 11.0, 11.0, 250),
        ]
    )
    result = aggregate_footprint(display, sub)
    bar = result[_ts("2026-07-30 15:00")]
    total = sum(r["vb"] + r["vs"] for r in bar["rows"])
    # 输出端每格 round(,3)，守恒断言给出对应的绝对容差
    assert total == pytest.approx(1000, abs=0.001 * 2 * len(bar["rows"]))
    tick = bar["tick"]
    for row in bar["rows"]:
        # 分箱下沿必须落在子K线价格范围附近（允许一个分箱的对齐余量）
        assert 9.0 - tick < row["p"] < 12.0 + tick
    # 行数不应显著超过目标行数（1/2/5 归整会略有出入）
    assert len(bar["rows"]) <= DEFAULT_ROWS + 2


def test_buy_sell_split_by_sub_bar_direction():
    display = _klines([("2026-07-30 15:00", 10, 11, 10, 11, 300)])
    sub = _klines(
        [
            ("2026-07-30 09:35", 10.0, 10.0, 10.0, 10.0, 100),  # 平：收>=开算买
            ("2026-07-30 09:40", 10.5, 10.5, 10.5, 10.5, 80),  # 涨（同价，一字）
            ("2026-07-30 09:45", 11.0, 11.0, 10.9, 10.9, 120),  # 跌
        ]
    )
    result = aggregate_footprint(display, sub)
    bar = result[_ts("2026-07-30 15:00")]
    assert sum(r["vb"] for r in bar["rows"]) == pytest.approx(180)
    assert sum(r["vs"] for r in bar["rows"]) == pytest.approx(120)


def test_flat_sub_bar_lands_in_single_bin():
    display = _klines([("2026-07-30 15:00", 10, 10, 10, 10, 50)])
    sub = _klines([("2026-07-30 09:35", 10.0, 10.0, 10.0, 10.0, 50)])
    result = aggregate_footprint(display, sub)
    rows = result[_ts("2026-07-30 15:00")]["rows"]
    assert len(rows) == 1
    assert rows[0]["vb"] == pytest.approx(50)


def test_sub_bar_after_last_display_bar_is_dropped():
    display = _klines([("2026-07-30 10:00", 10, 11, 9, 10.5, 100)])
    sub = _klines(
        [
            ("2026-07-30 09:30", 10, 10.5, 9.5, 10.2, 100),
            ("2026-07-30 10:30", 99, 99, 99, 99, 999),  # 晚于最后一根显示K线
        ]
    )
    result = aggregate_footprint(display, sub)
    assert set(result.keys()) == {_ts("2026-07-30 10:00")}
    total = sum(r["vb"] + r["vs"] for r in result[_ts("2026-07-30 10:00")]["rows"])
    assert total == pytest.approx(100)


def test_empty_inputs_return_empty_dict():
    display = _klines([("2026-07-30 15:00", 10, 11, 9, 10.5, 100)])
    assert aggregate_footprint(None, None) == {}
    assert aggregate_footprint(display, None) == {}
    assert aggregate_footprint(display, display.iloc[0:0]) == {}


def test_sub_frequency_map_only_uses_finer_frequencies():
    order = ["1m", "2m", "5m", "10m", "15m", "30m", "60m", "120m", "d", "w", "m", "y"]
    for display_freq, sub_freq in SUB_FREQUENCY_MAP.items():
        assert order.index(sub_freq) < order.index(display_freq)


def test_ttl_cache_expires():
    now = [0.0]
    cache = TTLCache(ttl_seconds=10, clock=lambda: now[0])
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
    now[0] = 9.9
    assert cache.get("k") == {"v": 1}
    now[0] = 10.1
    assert cache.get("k") is None
