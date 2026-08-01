from __future__ import annotations

import datetime as dt
import math

import pandas as pd

from tradingview_zy.domain import DataContractError
from tradingview_zy.kline_schema import normalize_kline_frame
from tradingview_zy.market_registry import descriptor_for


def _datetime_to_timestamp_seconds(value: dt.datetime | pd.Timestamp) -> int:
    return int(value.timestamp())


def _prepare_strict_history_frame(
    klines: pd.DataFrame,
    *,
    market: str | None,
    code: str | None,
) -> pd.DataFrame:
    """Adapt legacy provider frames before applying the strict Kline contract.

    Several existing providers return a single-symbol frame without repeating
    the requested symbol in every row, and expose exchange-local datetimes as
    naive values.  The history endpoint already owns both pieces of context, so
    it can make them explicit on a copy.  Frames that do provide a code still
    pass through the normal mismatch check; timezone-aware values are preserved
    and converted by ``normalize_kline_frame``.
    """

    result = klines.copy(deep=True)
    if code is not None and "code" not in result.columns:
        result["code"] = str(code)
    if market is not None and "date" in result.columns:
        dates = pd.to_datetime(result["date"], errors="raise")
        if dates.dt.tz is None:
            result["date"] = dates.dt.tz_localize(descriptor_for(market).timezone)
    return result


def _validate_history_frame(
    klines: pd.DataFrame,
    *,
    market: str | None,
    code: str | None,
    frequency: str | None,
) -> pd.DataFrame:
    # Production callers provide market/code and therefore receive the full
    # KlineFrame contract. The compatibility path still validates the payload
    # fields that TradingView consumes, without importing project config.
    if market is not None or code is not None:
        strict_frame = _prepare_strict_history_frame(
            klines,
            market=market,
            code=code,
        )
        return normalize_kline_frame(
            strict_frame,
            market=market,
            code=code,
            frequency=frequency,
            allow_empty=True,
        )
    required = ["date", "open", "close", "high", "low", "volume"]
    missing = [column for column in required if column not in klines.columns]
    if missing:
        raise DataContractError(f"K 线历史 payload 缺少字段 {missing}")
    result = klines.copy(deep=True)
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    for column in ["open", "close", "high", "low", "volume"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
        if not result[column].map(lambda value: math.isfinite(float(value))).all():
            raise DataContractError(f"K 线历史 payload 的 {column} 含非有限值")
    if result["date"].duplicated().any() or not result["date"].is_monotonic_increasing:
        raise DataContractError("K 线历史 payload 的 date 必须严格升序且不重复")
    if (result["high"] < result[["open", "close"]].max(axis=1)).any() or (
        result["low"] > result[["open", "close"]].min(axis=1)
    ).any():
        raise DataContractError("K 线历史 payload 的 OHLC 不变量失效")
    return result


def filter_klines_by_timestamp_range(
    klines: pd.DataFrame, start_ts: int, end_ts: int
) -> pd.DataFrame:
    if klines is None or len(klines) == 0:
        return klines
    if start_ts > end_ts:
        raise ValueError("start_ts 不得晚于 end_ts")
    timestamps = pd.to_datetime(klines["date"], errors="raise").map(
        _datetime_to_timestamp_seconds
    )
    return klines[(timestamps >= start_ts) & (timestamps <= end_ts)]


def klines_to_tv_history(
    klines: pd.DataFrame,
    update: bool,
    status: str = "ok",
    *,
    market: str | None = None,
    code: str | None = None,
    frequency: str | None = None,
) -> dict:
    if klines is None or len(klines) == 0:
        return {"s": "no_data"}
    normalized = _validate_history_frame(
        klines, market=market, code=code, frequency=frequency
    )
    return {
        "s": status,
        "t": [
            _datetime_to_timestamp_seconds(row["date"])
            for _, row in normalized.iterrows()
        ],
        "o": normalized["open"].tolist(),
        "c": normalized["close"].tolist(),
        "h": normalized["high"].tolist(),
        "l": normalized["low"].tolist(),
        "v": normalized["volume"].tolist(),
        "update": bool(update),
    }
