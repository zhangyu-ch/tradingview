import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.fun import datetime_to_int
from tradingview_zy.web_payloads import klines_to_tv_history


def test_klines_to_tv_history_returns_ohlcv_only():
    klines = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-05-03 09:30:00"),
                "open": 10.0,
                "close": 10.5,
                "high": 10.8,
                "low": 9.9,
                "volume": 100,
            }
        ]
    )

    payload = klines_to_tv_history(klines, update=False)

    assert payload == {
        "s": "ok",
        "t": [datetime_to_int(klines.iloc[0]["date"])],
        "o": [10.0],
        "c": [10.5],
        "h": [10.8],
        "l": [9.9],
        "v": [100],
        "update": False,
    }
    assert "bis" not in payload
    assert "mmds" not in payload
