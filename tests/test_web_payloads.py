import importlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_import_web_payloads_does_not_import_config_dependent_fun():
    sys.modules.pop("tradingview_zy.web_payloads", None)
    sys.modules.pop("tradingview_zy.fun", None)
    sys.modules.pop("tradingview_zy.config", None)

    importlib.import_module("tradingview_zy.web_payloads")

    assert "tradingview_zy.fun" not in sys.modules
    assert "tradingview_zy.config" not in sys.modules


def test_klines_to_tv_history_returns_ohlcv_only():
    from tradingview_zy.web_payloads import klines_to_tv_history

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
        "t": [int(klines.iloc[0]["date"].timestamp())],
        "o": [10.0],
        "c": [10.5],
        "h": [10.8],
        "l": [9.9],
        "v": [100],
        "update": False,
    }
    assert "bis" not in payload
    assert "mmds" not in payload
