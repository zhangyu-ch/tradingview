from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

import pandas as pd


MARKET_TIMEZONES: dict[str, str] = {
    "a": "Asia/Shanghai",
    "hk": "Asia/Shanghai",
    "futures": "Asia/Shanghai",
    "ny_futures": "America/New_York",
    "us": "America/New_York",
    "fx": "UTC",
    "currency": "UTC",
    "currency_spot": "UTC",
    "utc": "UTC",
}
_REQUIRED_COLUMNS = ("date", "open", "close", "high", "low", "volume")
_NUMERIC_COLUMNS = ("open", "close", "high", "low", "volume")


class KlinePayloadError(ValueError):
    """A provider K-line payload violates the canonical Web contract."""


def market_timezone(market: str) -> ZoneInfo:
    """Return the canonical timezone for a market or fail closed."""
    try:
        return ZoneInfo(MARKET_TIMEZONES[market.lower()])
    except (AttributeError, KeyError) as exc:
        raise KlinePayloadError(f"unsupported market timezone: {market!r}") from exc


def _localize_market_dates(values: pd.Series, zone: ZoneInfo) -> pd.Series:
    try:
        dates = pd.to_datetime(values, errors="raise")
    except Exception as exc:
        raise KlinePayloadError("K-line date values are invalid") from exc
    try:
        if isinstance(dates.dtype, pd.DatetimeTZDtype):
            return dates.dt.tz_convert(zone)
        return dates.dt.tz_localize(zone, ambiguous="raise", nonexistent="raise")
    except Exception as exc:
        raise KlinePayloadError(
            "K-line date is ambiguous or nonexistent in the market timezone"
        ) from exc


def _bind_identity(
    frame: pd.DataFrame, column: str, expected: str | None
) -> None:
    if expected is None:
        return
    if column not in frame.columns:
        frame[column] = expected
        return
    values = frame[column].astype(str)
    if not values.eq(expected).all():
        raise KlinePayloadError(
            f"K-line {column} does not match the requested {column}"
        )


def prepare_klines_for_market(
    klines: pd.DataFrame | None,
    market: str,
    *,
    expected_code: str | None = None,
    expected_frequency: str | None = None,
) -> pd.DataFrame | None:
    """Copy and validate a provider frame before any timestamp operation.

    Providers must return one strictly increasing, unique OHLCV series.  The
    Web boundary localizes naive wall-clock values to the market timezone and
    rejects malformed values instead of silently sorting or deduplicating them.
    """
    if klines is None:
        return None
    if not isinstance(klines, pd.DataFrame):
        raise KlinePayloadError("K-line payload must be a pandas DataFrame")
    frame = klines.copy(deep=True)
    if len(frame) == 0:
        return frame

    zone = market_timezone(market)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise KlinePayloadError(
            "K-line frame is missing required columns: " + ", ".join(missing)
        )

    frame["date"] = _localize_market_dates(frame["date"], zone)
    if frame["date"].isna().any():
        raise KlinePayloadError("K-line date must not be null")
    if frame["date"].duplicated().any():
        raise KlinePayloadError("K-line dates must be unique")
    if not frame["date"].is_monotonic_increasing:
        raise KlinePayloadError("K-line dates must be strictly increasing")

    for column in _NUMERIC_COLUMNS:
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except Exception as exc:
            raise KlinePayloadError(f"K-line {column} must be numeric") from exc
        if not frame[column].map(lambda value: math.isfinite(float(value))).all():
            raise KlinePayloadError(f"K-line {column} must be finite")
    if (frame["volume"] < 0).any():
        raise KlinePayloadError("K-line volume must not be negative")

    row_max = frame[["open", "close", "low"]].max(axis=1)
    row_min = frame[["open", "close", "high"]].min(axis=1)
    if (frame["high"] < row_max).any() or (frame["low"] > row_min).any():
        raise KlinePayloadError("K-line OHLC values are inconsistent")

    _bind_identity(frame, "code", expected_code)
    _bind_identity(frame, "frequency", expected_frequency)
    return frame


def normalize_klines_for_market(
    klines: pd.DataFrame | None, market: str
) -> pd.DataFrame | None:
    """Copy a frame and normalize only its date column for legacy callers."""
    if klines is None:
        return None
    if not isinstance(klines, pd.DataFrame):
        raise KlinePayloadError("K-line payload must be a pandas DataFrame")
    frame = klines.copy(deep=True)
    zone = market_timezone(market)
    if len(frame) == 0:
        return frame
    if "date" not in frame.columns:
        raise KlinePayloadError("K-line frame is missing required 'date' column")
    frame["date"] = _localize_market_dates(frame["date"], zone)
    return frame


def datetime_to_timestamp_seconds(value: dt.datetime | pd.Timestamp) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise KlinePayloadError(
            "timestamp must be timezone-aware before epoch conversion"
        )
    return int(timestamp.timestamp())


def filter_klines_by_timestamp_range(
    klines: pd.DataFrame | None,
    start_ts: int,
    end_ts: int,
    *,
    market: str = "utc",
) -> pd.DataFrame | None:
    normalized = normalize_klines_for_market(klines, market)
    if normalized is None or len(normalized) == 0:
        return normalized
    timestamps = normalized["date"].map(datetime_to_timestamp_seconds)
    return normalized[(timestamps >= start_ts) & (timestamps <= end_ts)]


def klines_to_tv_history(
    klines: pd.DataFrame | None,
    update: bool,
    status: str = "ok",
    *,
    market: str = "utc",
) -> dict:
    normalized = prepare_klines_for_market(klines, market)
    if normalized is None or len(normalized) == 0:
        return {"s": "no_data"}
    return {
        "s": status,
        "t": [
            datetime_to_timestamp_seconds(row["date"])
            for _, row in normalized.iterrows()
        ],
        "o": normalized["open"].tolist(),
        "c": normalized["close"].tolist(),
        "h": normalized["high"].tolist(),
        "l": normalized["low"].tolist(),
        "v": normalized["volume"].tolist(),
        "update": update,
    }
