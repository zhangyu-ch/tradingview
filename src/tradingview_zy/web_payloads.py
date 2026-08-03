from __future__ import annotations

import datetime as dt
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


def market_timezone(market: str) -> ZoneInfo:
    """Return the canonical timezone for a market or fail closed."""
    try:
        return ZoneInfo(MARKET_TIMEZONES[market.lower()])
    except (AttributeError, KeyError) as exc:
        raise ValueError(f"unsupported market timezone: {market!r}") from exc


def normalize_klines_for_market(
    klines: pd.DataFrame | None, market: str
) -> pd.DataFrame | None:
    """Copy a K-line frame and make every ``date`` market-timezone aware.

    Data providers commonly return naive timestamps that represent exchange-local
    wall clock time.  Treating those values as host-local time makes epoch
    conversion and range filtering depend on the server timezone.  This function
    is deliberately called before *any* timestamp comparison.
    """
    if klines is None:
        return None
    normalized = klines.copy(deep=True)
    if len(normalized) == 0:
        return normalized
    if "date" not in normalized.columns:
        raise ValueError("K-line frame is missing required 'date' column")

    dates = pd.to_datetime(normalized["date"], errors="raise")
    tz = market_timezone(market)
    if isinstance(dates.dtype, pd.DatetimeTZDtype):
        normalized["date"] = dates.dt.tz_convert(tz)
    else:
        normalized["date"] = dates.dt.tz_localize(
            tz, ambiguous="raise", nonexistent="raise"
        )
    return normalized


def datetime_to_timestamp_seconds(value: dt.datetime | pd.Timestamp) -> int:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware before epoch conversion")
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
    normalized = normalize_klines_for_market(klines, market)
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
