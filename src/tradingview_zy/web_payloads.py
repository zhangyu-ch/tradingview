from __future__ import annotations

import pandas as pd

from tradingview_zy import fun


def klines_to_tv_history(klines: pd.DataFrame, update: bool, status: str = "ok") -> dict:
    if klines is None or len(klines) == 0:
        return {"s": "no_data"}
    return {
        "s": status,
        "t": [fun.datetime_to_int(row["date"]) for _, row in klines.iterrows()],
        "o": klines["open"].tolist(),
        "c": klines["close"].tolist(),
        "h": klines["high"].tolist(),
        "l": klines["low"].tolist(),
        "v": klines["volume"].tolist(),
        "update": update,
    }
