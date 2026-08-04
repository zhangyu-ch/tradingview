from __future__ import annotations

import datetime as dt
import importlib.util
import sys
import zipfile
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

MODULE_PATH = SRC / "tradingview_zy/exchange/tdx_us_payloads.py"
spec = importlib.util.spec_from_file_location("test_me14_tdx_us_payloads", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
TdxUsPayloadError = module.TdxUsPayloadError
normalize_tdx_us_bars = module.normalize_tdx_us_bars


def _payload(*datetimes: object) -> pd.DataFrame:
    rows = []
    for index, value in enumerate(datetimes):
        open_value = 100.0 + index
        close_value = 101.0 + index
        rows.append(
            {
                "datetime": value,
                "open": open_value,
                "close": close_value,
                "high": close_value + 1,
                "low": open_value - 1,
                "position": 0,
                "trade": 1000 + index,
                "amount": 9000000 + index,
            }
        )
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    ("source_time", "expected_offset", "expected_utc"),
    [
        ("2026-01-05 22:30:00", dt.timedelta(hours=-5), "2026-01-05 14:30:00+00:00"),
        ("2026-07-06 21:30:00", dt.timedelta(hours=-4), "2026-07-06 13:30:00+00:00"),
    ],
)
def test_intraday_wall_clock_uses_new_york_dst(
    source_time: str,
    expected_offset: dt.timedelta,
    expected_utc: str,
) -> None:
    result = normalize_tdx_us_bars(_payload(source_time), code="AAPL", frequency="1m")
    market_time = result.iloc[0]["date"]

    assert market_time.hour == 9 and market_time.minute == 30
    assert market_time.utcoffset() == expected_offset
    assert pd.Timestamp(market_time).tz_convert("UTC") == pd.Timestamp(expected_utc)
    assert market_time.utcoffset() != dt.timedelta(hours=-4, minutes=-56)


@pytest.mark.parametrize(
    ("source_time", "expected_offset"),
    [
        ("2026-01-05 15:00:00", dt.timedelta(hours=-5)),
        ("2026-07-06 15:00:00", dt.timedelta(hours=-4)),
    ],
)
def test_daily_bar_is_anchored_to_regular_new_york_close(
    source_time: str,
    expected_offset: dt.timedelta,
) -> None:
    result = normalize_tdx_us_bars(_payload(source_time), code="AAPL", frequency="d")
    market_time = result.iloc[0]["date"]

    assert (market_time.hour, market_time.minute) == (16, 0)
    assert market_time.utcoffset() == expected_offset
    assert str(market_time.tzinfo) == "America/New_York"


def test_early_shanghai_wall_clock_retains_the_us_trading_date() -> None:
    result = normalize_tdx_us_bars(
        _payload("2026-05-04 04:00:00"), code="AAPL", frequency="1m"
    )
    market_time = result.iloc[0]["date"]

    assert market_time.date() == dt.date(2026, 5, 4)
    assert (market_time.hour, market_time.minute) == (16, 0)
    assert market_time.utcoffset() == dt.timedelta(hours=-4)


def test_cross_midnight_source_rows_are_sorted_after_market_conversion() -> None:
    payload = _payload("2026-05-04 04:00:00", "2026-05-04 21:30:00")
    result = normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")

    assert [(value.hour, value.minute) for value in result["date"]] == [(9, 30), (16, 0)]
    assert [value.date() for value in result["date"]] == [
        dt.date(2026, 5, 4),
        dt.date(2026, 5, 4),
    ]


def test_canonical_volume_uses_trade_and_never_amount() -> None:
    payload = _payload("2026-05-04 21:30:00")
    payload.loc[0, "trade"] = 123
    payload.loc[0, "amount"] = 987654321

    result = normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")

    assert result["volume"].tolist() == [123]
    assert "amount" not in result.columns
    assert "trade" not in result.columns


def test_missing_trade_does_not_fall_back_to_amount() -> None:
    payload = _payload("2026-05-04 21:30:00").drop(columns=["trade"])

    with pytest.raises(TdxUsPayloadError, match="trade"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_negative_trade_volume_is_rejected() -> None:
    payload = _payload("2026-05-04 21:30:00")
    payload.loc[0, "trade"] = -1

    with pytest.raises(TdxUsPayloadError, match="negative"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_infinite_trade_volume_is_rejected() -> None:
    payload = _payload("2026-05-04 21:30:00")
    payload["trade"] = payload["trade"].astype(float)
    payload.loc[0, "trade"] = float("inf")

    with pytest.raises(TdxUsPayloadError, match="finite"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_duplicate_market_timestamp_is_rejected() -> None:
    payload = _payload("2026-05-04 21:30:00", "2026-05-04 21:30:00")

    with pytest.raises(TdxUsPayloadError, match="unique"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_null_source_datetime_is_rejected() -> None:
    payload = _payload(None)

    with pytest.raises(TdxUsPayloadError, match="null"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_timezone_aware_source_datetime_is_rejected() -> None:
    payload = _payload(pd.Timestamp("2026-05-04 21:30:00", tz="UTC"))

    with pytest.raises(TdxUsPayloadError, match="timezone-naive"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_inconsistent_ohlc_is_rejected() -> None:
    payload = _payload("2026-05-04 21:30:00")
    payload.loc[0, "high"] = payload.loc[0, "close"] - 1

    with pytest.raises(TdxUsPayloadError, match="OHLC"):
        normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")


def test_normalizer_does_not_mutate_the_provider_dataframe() -> None:
    payload = _payload("2026-05-04 21:30:00", "2026-05-04 21:31:00")
    original = payload.copy(deep=True)

    normalize_tdx_us_bars(payload, code="AAPL", frequency="1m")

    pd.testing.assert_frame_equal(payload, original)


def test_bundled_pytdx_parser_exposes_independent_trade_and_amount_fields() -> None:
    wheel = next((ROOT / "package").glob("pytdx-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        source = archive.read("pytdx/parser/ex_get_instrument_bars.py").decode("utf-8")

    assert '("trade", trade)' in source
    assert '("amount", amount)' in source
    assert "struct.unpack(\"<ffffIIf\"" in source


def test_exchange_adapter_uses_the_normalizer_without_legacy_pytz_or_amount_mapping() -> None:
    source = (ROOT / "src/tradingview_zy/exchange/exchange_tdx_us.py").read_text(
        encoding="utf-8"
    )

    assert "normalize_tdx_us_bars(" in source
    assert 'ZoneInfo("America/New_York")' in source
    assert "import pytz" not in source
    assert "def _convert_dt" not in source
    assert 'klines_df["amount"]' not in source
    assert "replace(tzinfo=pytz" not in source
