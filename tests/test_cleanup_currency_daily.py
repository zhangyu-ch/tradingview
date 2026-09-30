import importlib.util
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal


ROOT = Path(__file__).resolve().parents[1]


def test_currency_daily_keeps_all_bars_at_eight_hour_boundary():
    # Load the pure converter without importing config/provider/database singletons.
    spec = importlib.util.spec_from_file_location(
        "cleanup_exchange_converters", ROOT / "src/tradingview_zy/exchange/exchange.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = pd.DataFrame(
        {
            "date": pd.to_datetime([
                "2025-01-02 07:59:00", "2025-01-02 08:00:00",
                "2025-01-02 23:59:00", "2025-01-03 07:59:00",
                "2025-01-03 08:00:00",
            ]).tz_localize("Asia/Shanghai"),
            "code": ["BTC/USDT"] * 5,
            "open": [10, 20, 30, 40, 50],
            "close": [11, 21, 31, 41, 51],
            "high": [12, 22, 32, 42, 52],
            "low": [9, 19, 29, 39, 49],
            "volume": [1, 2, 3, 4, 5],
        }
    )
    original = source.copy(deep=True)
    result = module.convert_currency_kline_frequency(source, "d")
    assert str(result["date"].dt.tz) == "UTC"
    assert result["date"].dt.strftime("%Y-%m-%d %H:%M").tolist() == [
        "2025-01-01 00:00", "2025-01-02 00:00", "2025-01-03 00:00"
    ]
    assert result["date"].dt.tz_convert("Asia/Shanghai").dt.hour.tolist() == [8, 8, 8]
    assert result["open"].tolist() == [10, 20, 50]
    assert result["close"].tolist() == [11, 41, 51]
    assert result["high"].tolist() == [12, 42, 52]
    assert result["low"].tolist() == [9, 19, 49]
    assert result["volume"].tolist() == [1, 9, 5]
    assert_frame_equal(source, original)
