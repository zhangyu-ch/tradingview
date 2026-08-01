from __future__ import annotations

import pandas as pd
from pandas.testing import assert_frame_equal

from tradingview_zy.backtesting.klines_generator import KlinesGenerator
from tradingview_zy.exchange.exchange import (
    convert_currency_kline_frequency,
    convert_futures_kline_frequency,
)

TZ = "Asia/Shanghai"


def _bars(start: str, periods: int) -> pd.DataFrame:
    dates = pd.date_range(start, periods=periods, freq="1min", tz=TZ)
    values = list(range(1, periods + 1))
    return pd.DataFrame(
        {
            "date": dates,
            "frequency": "1m",
            "code": "TEST.CODE",
            "open": values,
            "high": [value + 1 for value in values],
            "low": [value - 1 for value in values],
            "close": [value + 0.5 for value in values],
            "volume": [10] * periods,
        }
    )


def test_bob_and_eob_have_explicit_interval_semantics_and_do_not_mutate_input():
    source = _bars("2026-01-02 10:00", 31)
    original = source.copy(deep=True)

    bob = KlinesGenerator(15, "bob").update_klines(source)
    eob = KlinesGenerator(15, "eob").update_klines(source)

    assert_frame_equal(source, original)
    assert list(bob["date"].dt.strftime("%H:%M"))[:2] == ["10:00", "10:15"]
    assert bob.iloc[0]["open"] == 1
    assert bob.iloc[0]["close"] == 15.5
    assert list(eob["date"].dt.strftime("%H:%M"))[:2] == ["10:00", "10:15"]
    assert eob.iloc[1]["open"] == 2
    assert eob.iloc[1]["close"] == 16.5


def test_incremental_aggregation_matches_one_shot_result():
    source = _bars("2026-01-02 10:00", 75)
    one_shot = KlinesGenerator(15, "bob").update_klines(source)

    incremental = KlinesGenerator(15, "bob")
    incremental.update_klines(source.iloc[:31])
    actual = incremental.update_klines(source.iloc[31:])

    assert_frame_equal(actual.reset_index(drop=True), one_shot.reset_index(drop=True))


def test_gm_night_windows_are_mutually_exclusive_for_30_and_60_minutes():
    source = _bars("2026-01-02 21:00", 120)
    original = source.copy(deep=True)

    bars_30 = convert_futures_kline_frequency(source, "30m", "gm")
    bars_60 = convert_futures_kline_frequency(source, "60m", "gm")

    assert_frame_equal(source, original)
    assert list(bars_30["date"].dt.strftime("%H:%M")) == [
        "21:00",
        "21:30",
        "22:00",
        "22:30",
    ]
    assert list(bars_30["volume"]) == [300, 300, 300, 300]
    assert list(bars_60["date"].dt.strftime("%H:%M")) == ["21:00", "22:00"]
    assert list(bars_60["volume"]) == [600, 600]


def test_crypto_daily_boundary_is_0800_shanghai_time():
    source = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-01-02 07:59", "2026-01-02 08:00", "2026-01-03 07:59"]
            ).tz_localize(TZ),
            "frequency": ["1m"] * 3,
            "code": ["BTC/USDT"] * 3,
            "open": [1.0, 2.0, 3.0],
            "high": [1.0, 2.0, 3.0],
            "low": [1.0, 2.0, 3.0],
            "close": [1.0, 2.0, 3.0],
            "volume": [1.0, 1.0, 1.0],
        }
    )
    original = source.copy(deep=True)

    daily = convert_currency_kline_frequency(source, "d")

    assert_frame_equal(source, original)
    assert list(daily["date"].dt.strftime("%Y-%m-%d %H:%M")) == [
        "2026-01-01 08:00",
        "2026-01-02 08:00",
    ]
    assert daily.iloc[0]["open"] == 1.0
    assert daily.iloc[1]["open"] == 2.0
    assert daily.iloc[1]["close"] == 3.0
