from __future__ import annotations

import datetime as dt
import math
from zoneinfo import ZoneInfo

import pandas as pd

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_NEW_YORK = ZoneInfo("America/New_York")
_DAILY_OR_HIGHER = frozenset({"d", "w", "m", "q", "y"})
_REQUIRED_COLUMNS = ("datetime", "open", "close", "high", "low", "trade")


class TdxUsPayloadError(ValueError):
    """Raised when a TDX ExHQ US bar payload violates the local contract."""


def _source_datetime(value: object) -> dt.datetime:
    try:
        timestamp = pd.Timestamp(value)
    except Exception as error:
        raise TdxUsPayloadError("TDX US datetime is invalid") from error
    if pd.isna(timestamp):
        raise TdxUsPayloadError("TDX US datetime must not be null")
    if timestamp.tzinfo is not None:
        raise TdxUsPayloadError("TDX US source datetime must be timezone-naive")
    return timestamp.to_pydatetime()


def _market_datetime(source: dt.datetime, frequency: str) -> dt.datetime:
    if frequency in _DAILY_OR_HIGHER:
        # The provider date is the US trading date for daily and higher bars. The
        # source hour is a transport placeholder, so anchor it to the regular NY
        # close without interpreting it as a Shanghai instant.
        return dt.datetime(
            source.year,
            source.month,
            source.day,
            16,
            0,
            tzinfo=_NEW_YORK,
        )

    # Intraday ExHQ US bars use Shanghai wall-clock hours while retaining the US
    # trading-date label. 00:00-05:59 therefore belongs to the following Shanghai
    # civil day before conversion back to New York.
    if 0 <= source.hour <= 5:
        source = source + dt.timedelta(days=1)
    source_in_shanghai = source.replace(tzinfo=_SHANGHAI)
    return source_in_shanghai.astimezone(_NEW_YORK)


def normalize_tdx_us_bars(
    payload: pd.DataFrame,
    *,
    code: str,
    frequency: str,
) -> pd.DataFrame:
    """Return canonical US OHLCV bars from a raw pytdx ExHQ payload.

    The bundled pytdx parser exposes ``trade`` and ``amount`` as independent
    fields. Canonical volume is sourced only from ``trade``; ``amount`` is never
    used as a fallback.
    """

    if not isinstance(payload, pd.DataFrame):
        raise TypeError("TDX US payload must be a pandas DataFrame")
    if payload.empty:
        raise TdxUsPayloadError("TDX US payload must not be empty")
    if not isinstance(code, str) or code.strip() == "":
        raise TdxUsPayloadError("TDX US code must be a non-empty string")
    if not isinstance(frequency, str) or frequency.strip() == "":
        raise TdxUsPayloadError("TDX US frequency must be a non-empty string")

    missing = [column for column in _REQUIRED_COLUMNS if column not in payload.columns]
    if missing:
        raise TdxUsPayloadError(f"TDX US payload is missing required columns: {missing}")

    normalized = payload.copy(deep=True)
    normalized["date"] = normalized["datetime"].map(
        lambda value: _market_datetime(_source_datetime(value), frequency)
    )

    for column in ("open", "close", "high", "low", "trade"):
        try:
            values = pd.to_numeric(normalized[column], errors="raise")
        except Exception as error:
            raise TdxUsPayloadError(f"TDX US {column} must be numeric") from error
        if values.isna().any() or not values.map(math.isfinite).all():
            raise TdxUsPayloadError(
                f"TDX US {column} must contain only finite values"
            )
        normalized[column] = values

    if (normalized["trade"] < 0).any():
        raise TdxUsPayloadError("TDX US trade volume must not be negative")

    row_max = normalized[["open", "close", "low"]].max(axis=1)
    row_min = normalized[["open", "close", "high"]].min(axis=1)
    if (normalized["high"] < row_max).any() or (normalized["low"] > row_min).any():
        raise TdxUsPayloadError("TDX US OHLC values are inconsistent")

    if normalized["date"].duplicated().any():
        raise TdxUsPayloadError("TDX US market timestamps must be unique")

    normalized["code"] = code.strip()
    normalized["volume"] = normalized["trade"]
    normalized = normalized.sort_values("date", kind="mergesort").reset_index(drop=True)
    return normalized[["code", "date", "open", "close", "high", "low", "volume"]]
