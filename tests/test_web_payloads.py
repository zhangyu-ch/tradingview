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


def test_market_localization_happens_before_history_window_filtering():
    from tradingview_zy.web_payloads import (
        filter_klines_by_timestamp_range,
        klines_to_tv_history,
    )

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
    expected = int(pd.Timestamp("2026-05-03 09:30:00", tz="Asia/Shanghai").timestamp())

    filtered = filter_klines_by_timestamp_range(
        klines, expected, expected, market="a"
    )
    assert len(filtered) == 1
    assert str(filtered.iloc[0]["date"].tzinfo) == "Asia/Shanghai"
    assert klines.iloc[0]["date"].tzinfo is None  # caller frame was not mutated

    payload = klines_to_tv_history(filtered, update=True, market="a")
    assert payload["t"] == [expected]


def test_unknown_market_timezone_fails_closed():
    from tradingview_zy.web_payloads import normalize_klines_for_market

    klines = pd.DataFrame([{"date": pd.Timestamp("2026-05-03 09:30:00")}])
    try:
        normalize_klines_for_market(klines, "not-a-market")
    except ValueError as exc:
        assert "unsupported market timezone" in str(exc)
    else:
        raise AssertionError("unknown market must not fall back to host timezone")
