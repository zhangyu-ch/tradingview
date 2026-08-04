"""Shared request and payload boundary for US historical market data."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime, time, timedelta
from typing import Any

from tradingview_zy.data_contracts import KlineBar, ProviderBarPayload
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


US_MARKET_TIMEZONE = "America/New_York"
CANONICAL_COLUMNS = ["code", "date", "open", "close", "high", "low", "volume"]
_DAILY_FREQUENCIES = frozenset({"d", "w", "m", "q", "y"})
_LOOKBACK_DAYS = {
    "1m": 15,
    "2m": 15,
    "3m": 15,
    "5m": 15,
    "10m": 30,
    "15m": 45,
    "30m": 75,
    "60m": 150,
    "120m": 150,
    "d": 5000,
    "w": 7800,
    "m": 10000,
    "q": 12000,
    "y": 15000,
}


class UsHistoryPayloadError(ValueError):
    """A US history request or provider payload violates the shared contract."""


def _market_datetime(value: Any, timezone: ZoneInfo, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str):
        if not value.strip():
            raise UsHistoryPayloadError(f"{field} must not be empty")
        try:
            timestamp = pd.Timestamp(value.strip())
        except (TypeError, ValueError) as exc:
            raise UsHistoryPayloadError(f"{field} is not a valid datetime") from exc
        if pd.isna(timestamp):
            raise UsHistoryPayloadError(f"{field} is not a valid datetime")
        parsed = timestamp.to_pydatetime()
    elif isinstance(value, pd.Timestamp):
        if pd.isna(value):
            raise UsHistoryPayloadError(f"{field} is not a valid datetime")
        parsed = value.to_pydatetime()
    else:
        raise UsHistoryPayloadError(
            f"{field} must be a date, datetime or datetime string"
        )

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def parse_us_history_window(
    frequency: str,
    *,
    start_date: Any = None,
    end_date: Any = None,
    now: datetime | None = None,
    end_day_offset: int = 0,
    timezone_name: str = US_MARKET_TIMEZONE,
) -> tuple[datetime, datetime]:
    """Return one timezone-aware and ordered US history request window."""
    frequency = str(frequency).strip()
    if frequency not in _LOOKBACK_DAYS:
        raise UsHistoryPayloadError(f"unsupported US history frequency: {frequency!r}")
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise UsHistoryPayloadError(f"unknown market timezone: {timezone_name!r}") from exc
    if isinstance(end_day_offset, bool):
        raise UsHistoryPayloadError("end_day_offset must be an integer")
    try:
        offset = int(end_day_offset)
    except (TypeError, ValueError) as exc:
        raise UsHistoryPayloadError("end_day_offset must be an integer") from exc

    if end_date is None:
        current = now or datetime.now(tz=timezone)
        current_market = _market_datetime(current, timezone, field="now")
        end = datetime.combine(
            current_market.date() + timedelta(days=offset), time.min, tzinfo=timezone
        )
    else:
        end = _market_datetime(end_date, timezone, field="end_date")

    if start_date is None:
        start = end - timedelta(days=_LOOKBACK_DAYS[frequency])
    else:
        start = _market_datetime(start_date, timezone, field="start_date")

    if start > end:
        raise UsHistoryPayloadError("start_date must not be after end_date")
    return start, end


def _empty_history_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_COLUMNS)


def build_us_history_frame(
    records: pd.DataFrame | Iterable[Mapping[str, Any] | ProviderBarPayload] | None,
    *,
    code: str,
    frequency: str,
    timestamp_field: str = "timestamp",
    timestamp_unit: str | None = None,
    timezone_name: str = US_MARKET_TIMEZONE,
) -> pd.DataFrame:
    """Validate provider records and return a canonical, ordered OHLCV frame."""
    normalized_code = str(code).strip().upper()
    if not normalized_code:
        raise UsHistoryPayloadError("code must not be empty")
    frequency = str(frequency).strip()
    if frequency not in _LOOKBACK_DAYS:
        raise UsHistoryPayloadError(f"unsupported US history frequency: {frequency!r}")
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise UsHistoryPayloadError(f"unknown market timezone: {timezone_name!r}") from exc

    if records is None:
        return _empty_history_frame()
    if isinstance(records, pd.DataFrame):
        frame = records.copy(deep=True)
    else:
        try:
            materialized = [
                record.to_mapping(timestamp_field=timestamp_field)
                if isinstance(record, ProviderBarPayload)
                else dict(record)
                for record in records
            ]
            frame = pd.DataFrame(materialized)
        except (TypeError, ValueError) as exc:
            raise UsHistoryPayloadError("provider history records are invalid") from exc
    if frame.empty:
        return _empty_history_frame()

    required = {timestamp_field, "open", "close", "high", "low", "volume"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise UsHistoryPayloadError(
            "provider history is missing columns: " + ", ".join(missing)
        )

    timestamp_values = frame[timestamp_field]
    try:
        if timestamp_unit is None:
            parsed_dates = pd.to_datetime(timestamp_values, utc=True, errors="coerce")
        else:
            parsed_dates = pd.to_datetime(
                timestamp_values, unit=timestamp_unit, utc=True, errors="coerce"
            )
    except (TypeError, ValueError, OverflowError) as exc:
        raise UsHistoryPayloadError("provider history contains invalid timestamps") from exc
    if parsed_dates.isna().any():
        raise UsHistoryPayloadError("provider history contains invalid timestamps")
    market_dates = parsed_dates.dt.tz_convert(timezone)
    if frequency in _DAILY_FREQUENCIES:
        market_dates = market_dates.dt.normalize() + pd.Timedelta(hours=16)

    output = pd.DataFrame(
        {
            "code": normalized_code,
            "date": market_dates,
            "open": pd.to_numeric(frame["open"], errors="coerce"),
            "close": pd.to_numeric(frame["close"], errors="coerce"),
            "high": pd.to_numeric(frame["high"], errors="coerce"),
            "low": pd.to_numeric(frame["low"], errors="coerce"),
            "volume": pd.to_numeric(frame["volume"], errors="coerce"),
        }
    )
    numeric_columns = ["open", "close", "high", "low", "volume"]
    numeric_values = output[numeric_columns].to_numpy(dtype=float, copy=False)
    if not np.isfinite(numeric_values).all():
        raise UsHistoryPayloadError("provider history contains non-finite OHLCV values")
    if (output["volume"] < 0).any():
        raise UsHistoryPayloadError("provider history contains negative volume")

    expected_high = output[["open", "close", "low"]].max(axis=1)
    expected_low = output[["open", "close", "high"]].min(axis=1)
    if (output["high"] < expected_high).any() or (output["low"] > expected_low).any():
        raise UsHistoryPayloadError("provider history contains inconsistent OHLC values")

    output.sort_values("date", kind="mergesort", inplace=True)
    output.drop_duplicates(subset=["date"], keep="last", inplace=True)
    bars = [
        KlineBar(
            code=row.code,
            date=row.date.to_pydatetime() if isinstance(row.date, pd.Timestamp) else row.date,
            open=row.open,
            close=row.close,
            high=row.high,
            low=row.low,
            volume=row.volume,
        )
        for row in output.itertuples(index=False)
    ]
    return pd.DataFrame([bar.to_mapping() for bar in bars], columns=CANONICAL_COLUMNS)
