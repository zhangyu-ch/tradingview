"""Validation and normalisation for OHLCV frames at module boundaries."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from tradingview_zy.domain import DataContractError
from tradingview_zy.market_registry import descriptor_for

REQUIRED_COLUMNS = ("date", "code", "open", "high", "low", "close", "volume")
NUMERIC_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class KlineValidationResult:
    rows: int
    first: pd.Timestamp | None
    last: pd.Timestamp | None
    timezone: str | None


def _fail(message: str) -> DataContractError:
    return DataContractError(f"K 线数据协议错误：{message}")


def normalize_kline_frame(
    frame: pd.DataFrame | None,
    *,
    market: str | None = None,
    code: str | None = None,
    frequency: str | None = None,
    allow_empty: bool = True,
    copy: bool = True,
) -> pd.DataFrame:
    if frame is None:
        if allow_empty:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
        raise _fail("数据为空")
    if not isinstance(frame, pd.DataFrame):
        raise _fail(f"预期 DataFrame，实际为 {type(frame).__name__}")
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise _fail(f"缺少字段 {missing}")
    result = frame.copy(deep=True) if copy else frame
    if result.empty:
        if allow_empty:
            return result
        raise _fail("数据为空")

    try:
        result["date"] = pd.to_datetime(result["date"], errors="raise")
    except Exception as error:
        raise _fail(f"date 无法解析：{error}") from error

    timezone = result["date"].dt.tz
    if timezone is None:
        raise _fail("date 必须是带时区时间")
    if market is not None:
        expected = ZoneInfo(descriptor_for(market).timezone)
        try:
            result["date"] = result["date"].dt.tz_convert(expected)
        except Exception as error:
            raise _fail(f"无法转换到市场时区 {expected}: {error}") from error

    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")
        invalid = ~result[column].map(lambda value: math.isfinite(float(value)))
        if invalid.any():
            bad = result.index[invalid].tolist()[:5]
            raise _fail(f"{column} 含非有限值，行 {bad}")
    if (result["volume"] < 0).any():
        raise _fail("volume 不得为负")

    max_oc = result[["open", "close"]].max(axis=1)
    min_oc = result[["open", "close"]].min(axis=1)
    invalid_ohlc = (
        (result["high"] < max_oc)
        | (result["low"] > min_oc)
        | (result["high"] < result["low"])
    )
    if invalid_ohlc.any():
        raise _fail(f"OHLC 不变量失效，行 {result.index[invalid_ohlc].tolist()[:5]}")

    result["code"] = result["code"].astype(str)
    if code is not None and not (result["code"] == str(code)).all():
        values = sorted(result["code"].unique().tolist())[:5]
        raise _fail(f"code 与请求 {code!r} 不一致：{values}")
    if result["code"].eq("").any():
        raise _fail("code 不能为空")

    if result["date"].duplicated().any():
        duplicates = result.loc[result["date"].duplicated(), "date"].tolist()[:5]
        raise _fail(f"date 重复：{duplicates}")
    if not result["date"].is_monotonic_increasing:
        raise _fail("date 必须严格升序")

    if frequency is not None:
        if "frequency" in result.columns:
            values = result["frequency"].dropna().astype(str).unique().tolist()
            if values and values != [str(frequency)]:
                raise _fail(f"frequency 与请求 {frequency!r} 不一致：{values}")
        else:
            result["frequency"] = str(frequency)
    return result.reset_index(drop=True)


def validate_kline_frame(frame: pd.DataFrame, **kwargs) -> KlineValidationResult:
    normalized = normalize_kline_frame(frame, **kwargs)
    if normalized.empty:
        return KlineValidationResult(0, None, None, None)
    tz = str(normalized["date"].dt.tz)
    return KlineValidationResult(
        len(normalized), normalized["date"].iloc[0], normalized["date"].iloc[-1], tz
    )
