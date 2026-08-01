import importlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _temporarily_remove_module(monkeypatch, module_name: str) -> None:
    """Remove a module and its parent attribute, restoring both after the test."""

    monkeypatch.delitem(sys.modules, module_name, raising=False)
    parent_name, attribute = module_name.rsplit(".", 1)
    parent = sys.modules.get(parent_name)
    if parent is not None:
        monkeypatch.delattr(parent, attribute, raising=False)


def test_import_web_payloads_does_not_import_config_dependent_fun(monkeypatch):
    _temporarily_remove_module(monkeypatch, "tradingview_zy.web_payloads")
    _temporarily_remove_module(monkeypatch, "tradingview_zy.fun")
    _temporarily_remove_module(monkeypatch, "tradingview_zy.config")

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


def test_filter_klines_by_timestamp_range_keeps_requested_window():
    from tradingview_zy.web_payloads import filter_klines_by_timestamp_range

    klines = pd.DataFrame(
        [
            {"date": pd.Timestamp("2026-05-03 09:30:00"), "open": 1},
            {"date": pd.Timestamp("2026-05-03 09:35:00"), "open": 2},
            {"date": pd.Timestamp("2026-05-03 09:40:00"), "open": 3},
        ]
    )

    result = filter_klines_by_timestamp_range(
        klines,
        int(pd.Timestamp("2026-05-03 09:34:00").timestamp()),
        int(pd.Timestamp("2026-05-03 09:36:00").timestamp()),
    )

    assert result["open"].tolist() == [2]


def test_filter_klines_by_timestamp_range_returns_empty_for_empty_window():
    from tradingview_zy.web_payloads import filter_klines_by_timestamp_range

    klines = pd.DataFrame(
        [
            {"date": pd.Timestamp("2026-05-03 09:30:00"), "open": 1},
        ]
    )

    result = filter_klines_by_timestamp_range(
        klines,
        int(pd.Timestamp("2026-05-03 09:34:00").timestamp()),
        int(pd.Timestamp("2026-05-03 09:36:00").timestamp()),
    )

    assert result.empty
