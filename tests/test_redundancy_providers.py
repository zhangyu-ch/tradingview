"""Real provider/shared-workflow contracts with in-memory transports and caches."""
from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest
import pytz


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/tradingview_zy/exchange"
BINANCE = [("binance", "ExchangeBinance", "binanceusdm", "currency"),
           ("binance_spot", "ExchangeBinanceSpot", "binance", "currency_spot")]
TDX = [("fx", "ExchangeTDXFX", 4), ("hk", "ExchangeTDXHK", 31),
       ("us", "ExchangeTDXUS", 74), ("futures", "ExchangeTDXFutures", 28),
       ("ny_futures", "ExchangeTDXNYFutures", 60)]


@pytest.fixture
def load_provider(monkeypatch, tmp_path):
    import tradingview_zy

    # Never import personal configuration or the business DB. Restore package
    # attributes as well as sys.modules so later tests cannot inherit our fakes.
    before = {name: module for name, module in sys.modules.items()
              if name == "tradingview_zy" or name.startswith("tradingview_zy.")}
    attributes = {name: vars(module).copy() for name, module in before.items()
                  if hasattr(module, "__path__")}
    config = ModuleType("tradingview_zy.config")
    config.get_data_path = lambda: tmp_path
    db = ModuleType("tradingview_zy.db")
    db.db = object()
    environment = pytest.MonkeyPatch()
    environment.setitem(sys.modules, config.__name__, config)
    environment.setattr(tradingview_zy, "config", config, raising=False)
    environment.setitem(sys.modules, db.__name__, db)
    environment.setattr(tradingview_zy, "db", db, raising=False)

    def load(name):
        spec = importlib.util.spec_from_file_location(
            f"redundancy_{name}", SRC / f"exchange_{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    yield load
    environment.undo()
    for name in set(sys.modules) - set(before):
        if name.startswith("tradingview_zy."):
            sys.modules.pop(name, None)
    for name, attrs in attributes.items():
        module = before[name]
        for attr, value in list(vars(module).items()):
            if isinstance(value, ModuleType) and value.__name__.startswith("tradingview_zy."):
                if attr in attrs:
                    setattr(module, attr, attrs[attr])
                else:
                    delattr(module, attr)


class HistoryDB:
    def __init__(self, market):
        self.market = market
        self.cached = pd.DataFrame()
        self.reads, self.writes = [], []

    def klines(self, *args, **kwargs):
        self.reads.append((args, kwargs))
        return self.cached.copy(deep=True)

    def insert_klines(self, code, frequency, data):
        self.writes.append((code, frequency, data.copy(deep=True)))


class OhlcvClient:
    def __init__(self, params):
        self.params = params
        self.timeout = params["timeout"]
        self.calls, self.pages = [], []

    def fetch_ohlcv(self, **request):
        self.calls.append(request)
        return self.pages.pop(0)


@pytest.fixture(params=BINANCE, ids=lambda item: item[0])
def binance(request, load_provider, monkeypatch):
    name, class_name, sdk, market = request.param
    module = load_provider(name)
    monkeypatch.setattr(module, "config_get_proxy", lambda: {"host": "", "port": ""})
    monkeypatch.setattr(module, "resolve_config_secret", lambda *args: "")
    monkeypatch.setattr(module, "ExchangeDB", HistoryDB)
    monkeypatch.setattr(module.ccxt, sdk, OhlcvClient)
    instance = getattr(module, class_name)()
    assert instance.db_exchange.market == market
    assert instance.exchange.params == {"timeout": 4000, "maxRetriesOnFailure": 0}
    return instance


def test_binance_cache_resume_merge_and_online_corrections(binance):
    cached = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01T00:01Z", "2025-01-01T00:00Z"], utc=True),
        "code": "BTC/USDT", "open": 1, "close": 2, "high": 3, "low": 0, "volume": 4,
    })
    binance.db_exchange.cached = cached
    binance.exchange.pages = [[[1735689720000, 10, 13, 8, 12, 5],
                               [1735689660000, 20, 23, 18, 22, 6]]]
    args = {"request_id": "unchanged"}
    result = binance.klines("BTC/USDT", "1m", args=args)
    assert binance.exchange.calls == [{"symbol": "BTC/USDT", "timeframe": "1m",
                                      "limit": 1000, "params": {"startTime": 1735689660000}}]
    assert result.close.tolist() == [2, 22, 12]
    assert result.date.is_unique and result.date.is_monotonic_increasing
    assert str(result.date.dt.tz) == "UTC"
    assert binance.db_exchange.reads == [(("BTC/USDT", "1m"), {"args": {"limit": 10000}})]
    assert binance.db_exchange.writes[0][2].close.tolist() == [22, 12]
    pd.testing.assert_frame_equal(binance.db_exchange.cached, cached)
    assert args == {"request_id": "unchanged"}
    assert binance.exchange.timeout == 4000


@pytest.mark.parametrize("cache_count,empty", [(0, False), (1, False), (10002, False), (0, True), (1, True)])
def test_binance_cold_single_row_bounded_cache_and_empty_response(binance, cache_count, empty):
    binance.db_exchange.cached = pd.DataFrame({
        "date": pd.date_range("2025-01-01", periods=cache_count, freq="min", tz="UTC"),
        "code": "BTC/USDT", "open": 1, "close": 2, "high": 3, "low": 0, "volume": 4,
    })
    stamp = 1735689600000 + max(cache_count - 1, 0) * 60000
    binance.exchange.pages = [[] if empty else [[stamp, 8, 10, 7, 9, 3]]]
    result = binance.klines("BTC/USDT", "1m")
    assert len(result) == min(max(cache_count, int(not empty)), 10000)
    assert len(binance.db_exchange.writes) == int(not empty)
    expected_params = {} if cache_count == 0 else {"startTime": stamp}
    assert binance.exchange.calls[0]["params"] == expected_params
    if not empty:
        assert result.close.iloc[-1] == 9


@pytest.mark.parametrize("offset", [0, 8, -5])
def test_binance_online_utc_bounds_do_not_depend_on_host(binance, monkeypatch, offset):
    history = importlib.import_module("tradingview_zy.exchange.binance_history")

    class HostDatetime(dt.datetime):
        def timestamp(self):
            if self.tzinfo is None:
                return self.replace(tzinfo=dt.timezone(dt.timedelta(hours=offset))).timestamp()
            return super().timestamp()

        @classmethod
        def fromtimestamp(cls, value, tz=None):
            if tz is None:
                return dt.datetime.fromtimestamp(value, dt.timezone(dt.timedelta(hours=offset))).replace(tzinfo=None)
            return dt.datetime.fromtimestamp(value, tz)

    monkeypatch.setattr(history, "datetime", SimpleNamespace(datetime=HostDatetime, timezone=dt.timezone))
    assert int(HostDatetime(2025, 1, 1).timestamp() * 1000) == 1735689600000 - offset * 3600000
    binance.exchange.pages = [[[1735689600000, 1, 3, 0, 2, 10]]] * 2
    args = {"use_online": True}
    output = binance.klines("BTC/USDT", "60m", "2025-01-01 00:00:00", "2025-01-01T09:00+08:00", args)
    assert binance.exchange.calls[-1]["params"] == {"startTime": 1735689600000, "endTime": 1735693200000}
    assert output.date.iloc[0].isoformat() == "2025-01-01T00:00:00+00:00"
    assert binance.db_exchange.reads == binance.db_exchange.writes == []
    binance.increment_klines_by_online("BTC/USDT", "60m", output.date.iloc[0].isoformat())
    assert binance.exchange.calls[-1]["params"] == {"startTime": 1735689600000}
    assert args == {"use_online": True}


def test_binance_real_pagination_shares_deadline_lock_and_revised_rows(binance, monkeypatch):
    history = importlib.import_module("tradingview_zy.exchange.binance_history")
    fetch = history.fetch_ohlcv_with_retry
    calls = []

    def observe(client, lock, **kwargs):
        calls.append((client, lock, kwargs["deadline"]))
        return fetch(client, lock, **kwargs)

    monkeypatch.setattr(history, "fetch_ohlcv_with_retry", observe)
    binance.exchange.pages = [
        [[i * 60000, 1, 4, 0, 2, 1] for i in reversed(range(1000))],
        [[999 * 60000, 3, 6, 2, 5, 8]],
    ]
    result = binance.increment_klines_by_online("BTC/USDT", "1m", "1970-01-01")
    assert [call["params"] for call in binance.exchange.calls] == [{"startTime": 0}, {"startTime": 59940001}]
    assert len(result) == 1000 and result.close.iloc[-1] == 5
    assert result.date.is_unique and result.date.is_monotonic_increasing
    assert len(calls) == 2 and calls[0] == calls[1]
    assert calls[0][:2] == (binance.exchange, binance._ohlcv_lock)


@pytest.mark.parametrize("frequency,step,timeframe", [("2m", 60000, "1m"), ("10m", 300000, "5m"), ("3h", 3600000, "1h")])
@pytest.mark.parametrize("method", ["online_klines", "increment_klines_by_online"])
def test_binance_shared_ohlcv_mapping_and_custom_periods(binance, frequency, step, timeframe, method):
    rows = [[0, 10, 12, 9, 11, 1], [step, 20, 29, 8, 21, 2]]
    # Pagination owns ordering/deduplication before the period conversion.
    binance.exchange.pages = [rows if method == "online_klines" else [rows[1], rows[0], rows[1]]]
    result = getattr(binance, method)("BTC/USDT", frequency)
    assert result.code.tolist() == ["BTC/USDT"]
    assert result.frequency.tolist() == [frequency]
    assert result.date.iloc[0] == pd.Timestamp("1970-01-01T00:00Z")
    assert result[["open", "close", "high", "low", "volume"]].values.tolist() == [[10, 21, 29, 8, 3]]
    assert binance.exchange.calls[0]["timeframe"] == timeframe


@pytest.mark.parametrize("method", ["online_klines", "increment_klines_by_online"])
def test_binance_invalid_frequency_fails_before_sdk(binance, method):
    from tradingview_zy.domain import InvalidRequestError
    with pytest.raises(InvalidRequestError):
        getattr(binance, method)("BTC/USDT", "invalid")
    assert binance.exchange.calls == []


def test_binance_account_quote_and_frequency_boundaries_remain_separate(binance, monkeypatch):
    from tradingview_zy.domain import UnsupportedCapabilityError
    from tradingview_zy.exchange.exchange import LiveTradingDisabledError

    spot = type(binance).__name__ == "ExchangeBinanceSpot"
    assert "ExchangeBinance" not in [cls.__name__ for cls in type(binance).__mro__[1:]]
    assert ("3h" in binance.support_frequencys()) is not spot
    account = {"USDT": {"total": 12, "free": 10, "used": 2},
               "info": {"totalUnrealizedProfit": 3, "assets": []}}
    monkeypatch.setattr(binance.exchange, "fetch_balance", lambda: account, raising=False)
    monkeypatch.setattr(binance.exchange, "fetch_positions", lambda **kwargs: [
        {"symbol": "BTC/USDT:USDT", "entryPrice": 2},
        {"symbol": "ETH/USDT:USDT", "entryPrice": 0},
    ], raising=False)
    if spot:
        with pytest.raises(UnsupportedCapabilityError):
            binance.balance()
        with pytest.raises(UnsupportedCapabilityError):
            binance.positions()
    else:
        assert binance.balance() == {"total": 12, "free": 10, "used": 2, "profit": 3}
        assert binance.positions() == [{"symbol": "BTC/USDT", "entryPrice": 2}]
    for action in [lambda: binance.order("BTC/USDT", "buy", 1),
                   lambda: binance.cancel_all_order("BTC/USDT")]:
        with pytest.raises(LiveTradingDisabledError):
            action()
    symbol = "BTC/USDT" if spot else "BTC/USDT:USDT"
    raw = {"last": 10, "bid": 9, "ask": 11, "high": 15, "low": 5,
           "open": 8, "quoteVolume": 20, "percentage": 25}
    monkeypatch.setattr(binance.exchange, "fetch_tickers", lambda codes: {symbol: raw}, raising=False)
    tick = binance.ticks(["BTC/USDT"])["BTC/USDT"]
    assert (tick.buy1, tick.sell1) == ((9, 11) if spot else (10, 10))
    raw["bid"] = None
    assert bool(binance.ticks(["BTC/USDT"])) is not spot


class ExHqClient:
    need_setup = False
    auto_retry = False
    client = None

    def __init__(self):
        self.events, self.pages = [], []
        self.quotes = {}

    def connect(self, ip, port, **kwargs):
        self.events.append(("connect", ip, port))
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.disconnect()

    def disconnect(self):
        self.events.append(("close",))

    def get_instrument_quote(self, market, code):
        self.events.append(("quote", market, code))
        value = self.quotes[code]
        if isinstance(value, Exception):
            raise value
        return value

    def get_instrument_bars(self, frequency, market, code, offset, count):
        self.events.append(("bars", frequency, market, code, offset, count))
        return self.pages.pop(0)

    @staticmethod
    def to_df(rows):
        return pd.DataFrame(rows)


def quote(previous=100):
    return {"price": 110, "bid1": 109, "ask1": 111, "high": 120,
            "low": 90, "open": 101, "zongliang": 42, "pre_close": previous}


@pytest.fixture(params=TDX, ids=lambda item: item[0])
def tdx(request, load_provider):
    name, class_name, market = request.param
    module = load_provider(f"tdx_{name}")
    cls = getattr(module, class_name)
    provider = cls.__new__(cls)
    provider.connect_info = {"ip": "test.invalid", "port": 7709}
    provider.market_maps = {"TEST": {"market": market}, "VOID": {"market": None}}
    provider.tz = pytz.timezone("Asia/Shanghai")
    client = ExHqClient()
    created = []

    def factory(**kwargs):
        created.append(kwargs)
        return client

    provider._tdx_client_factory = factory
    provider._tdx_client_kwargs = {"raise_exception": True, "auto_retry": False}
    return SimpleNamespace(provider=provider, client=client, created=created, name=name, market=market)


def test_exhq_real_providers_preserve_code_order_empty_quotes_and_nullable_rate(tdx):
    prefix = "" if tdx.name == "us" else "TEST."
    codes = [prefix + name for name in ["B", "EMPTY", "A", "B"]]
    tdx.client.quotes = {"A": [quote(0)], "B": [quote(), quote(200)], "EMPTY": []}
    result = tdx.provider.ticks(codes)
    assert list(result) == [prefix + "B", prefix + "A"]
    assert vars(result[prefix + "B"]) == dict(code=prefix + "B", last=110, buy1=109, sell1=111,
                                             high=120, low=90, open=101, volume=42, rate=10.0)
    assert result[prefix + "A"].rate is None
    assert tdx.client.events == [("connect", "test.invalid", 7709)] + [
        ("quote", tdx.market, name) for name in ["B", "EMPTY", "A", "B"]
    ] + [("close",)]
    assert tdx.created == [{"raise_exception": True, "auto_retry": False}]


@pytest.mark.parametrize("failure", [KeyError("bad quote"), OSError("transport failed")])
def test_exhq_tick_failure_is_not_retried_or_swallowed(tdx, failure):
    code = "BAD" if tdx.name == "us" else "TEST.BAD"
    tdx.client.quotes = {"BAD": failure}
    with pytest.raises(type(failure)) as error:
        tdx.provider.ticks([code, code])
    assert error.value is failure
    assert len(tdx.created) == 1
    assert tdx.client.events[-1] == ("close",)
    assert len(tdx.client.events) == 3


def test_exhq_empty_request_still_connects_once_and_provider_conversion_is_retained(tdx):
    assert tdx.provider.ticks([]) == {}
    assert tdx.client.events == [("connect", "test.invalid", 7709), ("close",)]
    if tdx.name != "us":
        assert tdx.provider.ticks(["VOID.SKIP"]) == {}
        with pytest.raises(KeyError):
            tdx.provider.ticks(["MISSING.CODE"])
        assert not any(event[0] == "quote" for event in tdx.client.events)
        assert tdx.client.events[-1] == ("close",)


def test_real_tdx_cache_refresh_preserves_raw_and_market_specific_fields(tdx):
    from test_b5_tdx_cache import MemoryCache
    prefix = "" if tdx.name == "us" else "TEST."
    code = prefix + "CODE"
    # Night-session remapping reverses input date order for both futures markets.
    times = ["2026-08-03 10:00:00", "2026-08-03 21:00:00", "2026-08-03 02:00:00"]
    raw = pd.DataFrame({"datetime": times + [times[0]], "open": [1, 2, 3, 8],
                        "close": [2, 3, 4, 9], "high": 10, "low": 0,
                        "trade": 30, "amount": 20})
    tdx.client.pages = [raw, pd.DataFrame()]
    tdx.provider.fdb = MemoryCache()
    tdx.provider.klines_qfq = lambda code, data, **kwargs: data
    args = {"pages": 2, "fq_type": "bfq"}
    result = tdx.provider.klines(code, "1m", args=args)
    saved = tdx.provider.fdb.cached
    assert saved.date.is_unique and saved.date.is_monotonic_increasing
    assert saved.date.dt.tz is None
    assert result.date.is_unique and result.date.is_monotonic_increasing
    assert sorted(result.close) == [3, 4, 9]
    assert result.volume.tolist() == [20 if tdx.name == "hk" else 30] * 3
    if tdx.name == "futures":
        assert saved.date.iloc[0] == pd.Timestamp("2026-08-02 21:00:00")
    if tdx.name == "ny_futures":
        assert saved.date.iloc[-1] == pd.Timestamp("2026-08-04 02:00:00")
    assert args == {"pages": 2, "fq_type": "bfq"}
    assert tdx.client.events[-1] == ("close",)
    assert len(tdx.created) == 1


@pytest.mark.parametrize("name,class_name", [("futures", "ExchangeTDXFutures"), ("ny_futures", "ExchangeTDXNYFutures")])
def test_exhq_all_ticks_keeps_its_distinct_payload_and_rate(load_provider, name, class_name):
    module = load_provider(f"tdx_{name}")
    cls = getattr(module, class_name)
    provider = cls.__new__(cls)
    provider.market_maps = {"TEST": {"market": 28, "category": 3}}
    provider.connect_info = {"ip": "test.invalid", "port": 7709}
    client = ExHqClient()
    provider._tdx_client_factory = lambda **kwargs: client
    provider._tdx_client_kwargs = {}
    row = {"code": "CODE", "MaiChu": 110, "MaiRuJia": 109, "MaiChuJia": 111,
           "ZuiDi": 90, "ZuiGao": 120, "ZongLiang": 42, "JinKai": 101, "ZuoJie": 100}
    client.get_instrument_quote_list = lambda *args, **kwargs: [row]
    assert provider.all_ticks()["TEST.CODE"].rate == 10.0
    row["ZuoJie"] = 0
    assert provider.all_ticks()["TEST.CODE"].rate is None
    assert client.events[-1] == ("close",)


def test_a_share_tick_keeps_batch_payload_and_etf_price_scaling(load_provider, monkeypatch):
    module = load_provider("tdx")
    cls = module.ExchangeTDX
    provider = cls.__new__(cls)
    provider.connect_info = {"ip": "test.invalid", "port": 7709}
    provider.to_tdx_code = lambda code: (1, "510300", "etf_cn")
    client = ExHqClient()
    monkeypatch.setattr(module, "TdxHq_API", lambda **kwargs: client)
    requests = []

    def quotes(codes):
        requests.append(codes)
        return [{"market": 1, "code": "510300", "price": 110, "bid1": 109,
                 "ask1": 111, "low": 90, "high": 120, "open": 101,
                 "last_close": 100, "vol": 42}]

    client.get_security_quotes = quotes
    tick = provider.ticks(["SH.510300"])["SH.510300"]
    assert requests == [[(1, "510300")]]
    assert tick.last == 11 and tick.buy1 == 10.9 and tick.volume == 42 and tick.rate == 10.0
    assert client.events[-1] == ("close",)
