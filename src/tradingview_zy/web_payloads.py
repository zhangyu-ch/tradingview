from __future__ import annotations

import datetime as dt

import pandas as pd


def _datetime_to_timestamp_seconds(value: dt.datetime | pd.Timestamp) -> int:
    return int(value.timestamp())


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
