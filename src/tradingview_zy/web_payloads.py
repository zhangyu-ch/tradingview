from __future__ import annotations

import datetime as dt

import pandas as pd


def _datetime_to_timestamp_seconds(value: dt.datetime | pd.Timestamp) -> int:
    return int(value.timestamp())


def filter_klines_by_timestamp_range(
    klines: pd.DataFrame, start_ts: int, end_ts: int
) -> pd.DataFrame:
    if klines is None or len(klines) == 0:
        return klines
    timestamps = klines["date"].map(_datetime_to_timestamp_seconds)
    return klines[(timestamps >= start_ts) & (timestamps <= end_ts)]


def klines_to_tv_history(klines: pd.DataFrame, update: bool, status: str = "ok") -> dict:
    if klines is None or len(klines) == 0:
        return {"s": "no_data"}
    return {
        "s": status,
        "t": [_datetime_to_timestamp_seconds(row["date"]) for _, row in klines.iterrows()],
        "o": klines["open"].tolist(),
        "c": klines["close"].tolist(),
        "h": klines["high"].tolist(),
        "l": klines["low"].tolist(),
        "v": klines["volume"].tolist(),
        "update": update,
    }
