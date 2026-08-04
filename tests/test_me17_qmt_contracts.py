from __future__ import annotations

import datetime as dt
import importlib
import inspect
import math
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

config_module = sys.modules.get("tradingview_zy.config")
if config_module is None:
    config_module = types.ModuleType("tradingview_zy.config")
    config_module.get_data_path = lambda: ROOT / ".test-qmt-data"
    sys.modules["tradingview_zy.config"] = config_module

if "tzlocal" not in sys.modules:
    tzlocal_module = types.ModuleType("tzlocal")
    tzlocal_module.get_localzone = lambda: dt.timezone.utc
    sys.modules["tzlocal"] = tzlocal_module

xtquant_module = sys.modules.get("xtquant")
if xtquant_module is None:
    xtquant_module = types.ModuleType("xtquant")
    xtquant_module.xtdata = types.SimpleNamespace(enable_hello=True)
    sys.modules["xtquant"] = xtquant_module

qmt = importlib.import_module("tradingview_zy.exchange.exchange_qmt")


class FakeXTData:
    def __init__(self) -> None:
        self.enable_hello = True
        self.market_response = None
        self.full_tick_response = {}
        self.instrument_types: dict[str, dict] = {}
        self.instrument_details: dict[str, dict] = {}
        self.downloads: list[tuple[tuple, dict]] = []
        self.reads: list[dict] = []
        self.full_tick_calls: list[list[str]] = []

    def download_history_data(self, *args, **kwargs):
        self.downloads.append((args, kwargs))
        return None

    def get_market_data_ex(self, **kwargs):
        self.reads.append(dict(kwargs))
        return self.market_response

    def get_full_tick(self, codes):
        self.full_tick_calls.append(list(codes))
        return self.full_tick_response

    def get_instrument_type(self, code):
        return self.instrument_types.get(code)

    def get_instrument_detail(self, code, complete):
        return self.instrument_details.get(code)

    def get_divid_factors(self, code):
        return None

    def subscribe_whole_quote(self, codes, callback):
        return 1

    def run(self):
        return None


@pytest.fixture()
def fake(monkeypatch: pytest.MonkeyPatch) -> FakeXTData:
    value = FakeXTData()
    monkeypatch.setattr(qmt, "xtdata", value)
    return value


def _ms(value: str) -> int:
    return int(pd.Timestamp(value, tz="Asia/Shanghai").timestamp() * 1000)


def _frame(*times: str) -> pd.DataFrame:
    size = len(times)
    return pd.DataFrame(
        {
            "time": [_ms(value) for value in times],
            "open": [10.0] * size,
            "high": [10.3] * size,
            "low": [9.8] * size,
            "close": [10.1] * size,
            "volume": [100.0] * size,
        }
    )


def _valid_tick(*, last_close=10.0, bid=None, ask=None):
    return {
        "lastPrice": 11.0,
        "lastClose": last_close,
        "bidPrice": [10.9] if bid is None else bid,
        "askPrice": [11.1] if ask is None else ask,
        "high": 11.2,
        "low": 9.9,
        "open": 10.0,
        "volume": 1000,
    }


def test_exact_time_range_is_forwarded_and_reapplied_without_download(fake) -> None:
    fake.market_response = {
        "600000.SH": _frame(
            "2026-08-03 09:29:00",
            "2026-08-03 09:30:00",
            "2026-08-03 10:00:00",
            "2026-08-03 10:01:00",
        )
    }
    exchange = qmt.ExchangeQMT()

    result = exchange.klines(
        "SH.600000",
        "1m",
        start_date="2026-08-03 09:30:00",
        end_date="2026-08-03 10:00:00",
    )

    assert result["date"].dt.strftime("%H:%M:%S").tolist() == ["09:30:00", "10:00:00"]
    assert fake.downloads == []
    assert fake.reads == [
        {
            "field_list": [],
            "stock_list": ["600000.SH"],
            "period": "1m",
            "start_time": "20260803093000",
            "end_time": "20260803100000",
            "count": -1,
            "dividend_type": "front",
            "fill_data": False,
        }
    ]


def test_date_only_end_includes_the_whole_market_day(fake) -> None:
    fake.market_response = {
        "600000.SH": _frame("2026-08-03 15:00:00", "2026-08-04 09:30:00")
    }
    result = qmt.ExchangeQMT().klines(
        "SH.600000", "1m", start_date="2026-08-03", end_date="2026-08-03"
    )

    assert result["date"].dt.strftime("%Y-%m-%d %H:%M:%S").tolist() == [
        "2026-08-03 15:00:00"
    ]
    assert fake.reads[0]["start_time"] == "20260803000000"
    assert fake.reads[0]["end_time"] == "20260803235959"


def test_download_is_explicit_and_receives_both_boundaries(fake) -> None:
    fake.market_response = {"600000.SH": _frame("2026-08-03 09:30:00")}
    exchange = qmt.ExchangeQMT()

    exchange.klines(
        "SH.600000",
        "1m",
        start_date="2026-08-03 09:30:00",
        end_date="2026-08-03 10:00:00",
        args={"download": True, "incrementally": False},
    )

    assert len(fake.downloads) == 1
    args, kwargs = fake.downloads[0]
    assert args == ("600000.SH", "1m")
    assert kwargs == {
        "start_time": "20260803093000",
        "end_time": "20260803100000",
        "incrementally": False,
    }


def test_invalid_requests_fail_before_any_sdk_call(fake) -> None:
    exchange = qmt.ExchangeQMT()
    cases = [
        ("SH.600000", "1m", "2026-08-04", "2026-08-03", None),
        ("SH.600000", "2m", None, None, None),
        ("SH.600000", "1m", None, None, {"req_counts": True}),
        ("bad-code", "1m", None, None, None),
        ("SH.600000", "1m", None, None, {"download": "yes"}),
    ]
    for code, frequency, start, end, args in cases:
        with pytest.raises(qmt.QMTRequestError):
            exchange.klines(code, frequency, start, end, args)
    assert fake.downloads == []
    assert fake.reads == []


def test_empty_unavailable_and_malformed_kline_payloads_have_stable_outcomes(fake) -> None:
    exchange = qmt.ExchangeQMT()

    fake.market_response = None
    with pytest.raises(qmt.QMTDataUnavailableError):
        exchange.klines("SH.600000", "1m")

    fake.market_response = {}
    with pytest.raises(qmt.QMTDataUnavailableError):
        exchange.klines("SH.600000", "1m")

    fake.market_response = {"600000.SH": pd.DataFrame()}
    empty = exchange.klines("SH.600000", "1m")
    assert empty.empty
    assert empty.columns.tolist() == qmt.ExchangeQMT._KLINE_COLUMNS

    malformed = _frame("2026-08-03 09:30:00").drop(columns="volume")
    fake.market_response = {"600000.SH": malformed}
    with pytest.raises(qmt.QMTDataSchemaError, match="missing columns"):
        exchange.klines("SH.600000", "1m")

    duplicate = _frame("2026-08-03 09:30:00", "2026-08-03 09:30:00")
    fake.market_response = {"600000.SH": duplicate}
    with pytest.raises(qmt.QMTDataSchemaError, match="duplicate"):
        exchange.klines("SH.600000", "1m")

    nonfinite = _frame("2026-08-03 09:30:00")
    nonfinite.loc[0, "close"] = math.nan
    fake.market_response = {"600000.SH": nonfinite}
    with pytest.raises(qmt.QMTDataSchemaError, match="non-finite"):
        exchange.klines("SH.600000", "1m")


def test_tick_schema_is_validated_and_zero_previous_close_is_unavailable(fake) -> None:
    fake.full_tick_response = {"600000.SH": _valid_tick(last_close=0)}
    result = qmt.ExchangeQMT().ticks(["SH.600000"])
    assert result["SH.600000"].rate is None
    assert result["SH.600000"].buy1 == 10.9

    fake.full_tick_response = {"600000.SH": _valid_tick(bid=[])}
    with pytest.raises(qmt.QMTDataSchemaError, match="bidPrice"):
        qmt.ExchangeQMT().ticks(["SH.600000"])


def test_catalog_cache_is_instance_local_and_defensive(fake) -> None:
    fake.full_tick_response = {"600000.SH": _valid_tick()}
    fake.instrument_types = {"600000.SH": {"stock": True}}
    fake.instrument_details = {
        "600000.SH": {"InstrumentName": "浦发银行", "PriceTick": 0.01}
    }
    first = qmt.ExchangeQMT()
    catalogue = first.all_stocks()
    catalogue[0]["name"] = "mutated"
    assert first.all_stocks()[0]["name"] == "浦发银行"

    fake.full_tick_response = {"000001.SZ": _valid_tick()}
    fake.instrument_types = {"000001.SZ": {"stock": True}}
    fake.instrument_details = {
        "000001.SZ": {"InstrumentName": "平安银行", "PriceTick": 0.01}
    }
    second = qmt.ExchangeQMT()
    assert second.all_stocks()[0]["code"] == "SZ.000001"
    assert first.all_stocks()[0]["code"] == "SH.600000"
    assert not hasattr(qmt.ExchangeQMT, "g_all_stocks")


def test_subscribe_default_and_source_contract_have_no_mutable_or_hidden_download() -> None:
    signature = inspect.signature(qmt.ExchangeQMT.subscribe_all_ticks)
    assert signature.parameters["market_list"].default is None
    source = (ROOT / "src/tradingview_zy/exchange/exchange_qmt.py").read_text(
        encoding="utf-8"
    )
    klines_block = source[source.index("    def klines(") : source.index("    def stock_info(")]
    assert "get_market_data_ex" in klines_block
    assert "get_market_data(" not in klines_block
    assert "download_history_data" not in klines_block
    assert "calculate_change_rate" in source
