from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
from typing import Union

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/tradingview_zy/exchange"


def _load_helper(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reliability = _load_helper("b18_tdx_reliability", SRC / "tdx_reliability.py")


class FakeClock:
    now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeSocket:
    def __init__(self, clock=None):
        self.timeouts = []
        self.clock = clock

    def settimeout(self, seconds):
        self.timeouts.append(seconds)

    def recv(self, size):
        if self.clock:
            self.clock.now += min(2.0, self.timeouts[-1])
        return b"x" * size

    def send(self, data):
        return len(data)


class FakeSdkError(Exception):
    def __init__(self, original):
        super().__init__("SDK hid the failure")
        self.original_exception = original


class FakeClient:
    need_setup = True
    auto_retry = True

    def __init__(self, action=None, clock=None):
        self.action = action
        self.calls = 0
        self.closed = False
        self.client = FakeSocket(clock)
        self.setup_seen = False
        self.connection_options = []

    def connect(self, ip, port, **kwargs):
        self.connection_options.append(kwargs)
        assert not self.need_setup
        return self

    def setup(self):
        self.setup_seen = True
        assert isinstance(self.client, reliability._DeadlineSocket)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def disconnect(self):
        self.closed = True

    def get_instrument_bars(self, *args):
        self.calls += 1
        if isinstance(self.action, Exception):
            raise self.action
        return self.action or []

    get_security_bars = get_instrument_bars
    get_index_bars = get_instrument_bars

    @staticmethod
    def to_df(rows):
        return pd.DataFrame(rows)


CONNECTION = {"ip": "test.invalid", "port": 7709}


def test_tdx_deadline_covers_handshake_and_partial_reads():
    clock = FakeClock()
    client = FakeClient(clock=clock)
    raw_socket = client.client
    with pytest.raises(TimeoutError, match="deadline"):
        with reliability.tdx_kline_connection(client, CONNECTION, 5.0, clock=clock):
            while True:
                client.client.recv(1)
    assert clock.now == 5.0
    assert raw_socket.timeouts == [4.0, 3.0, 1.0]
    assert client.closed and client.setup_seen
    assert client.auto_retry is False
    assert client.need_setup is True


def test_tdx_unwraps_sdk_errors_without_retrying_programming_failures():
    bug = ValueError("bad parser")
    client = FakeClient(FakeSdkError(bug))
    with pytest.raises(ValueError, match="bad parser") as error:
        with reliability.tdx_kline_connection(client, CONNECTION, 12.0):
            client.get_instrument_bars()
    assert error.value is bug
    assert isinstance(error.value.__cause__, FakeSdkError)
    assert client.closed


TDX_TARGETS = [
    "exchange_tdx", "exchange_tdx_futures", "exchange_tdx_fx",
    "exchange_tdx_hk", "exchange_tdx_ny_futures", "exchange_tdx_us",
]


class InvalidRequestError(ValueError):
    pass


class FakeConnectionError(ConnectionError):
    pass


def _tdx_method(name, action=None):
    tree = ast.parse((SRC / f"{name}.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "klines")
    clients = []

    def factory(**options):
        assert not options.get("auto_retry", False)
        client = FakeClient(action)
        clients.append(client)
        return client

    def retry(operation, **options):
        return reliability.call_with_bounded_retry(
            operation, **options, base_delay_seconds=0, max_delay_seconds=0,
        )

    namespace = {
        "pd": pd, "Union": Union, "InvalidRequestError": InvalidRequestError,
        "datetime": __import__("datetime"),
        "refresh_tdx_window": _load_helper("b18_tdx_cache", SRC / "tdx_cache.py").refresh_tdx_window,
        "tdx_cache_key": _load_helper("b18_tdx_cache_key", SRC / "tdx_cache.py").tdx_cache_key,
        "normalize_tdx_us_bars": _load_helper("b18_us_payloads", SRC / "tdx_us_payloads.py").normalize_tdx_us_bars,
        "time": SimpleNamespace(monotonic=lambda: 0.0),
        "remaining_request_seconds": lambda deadline: deadline,
        "TdxHq_API": factory, "TdxConnectionError": FakeConnectionError,
        "NodeSelectionError": FakeConnectionError,
        "tdx_kline_connection": reliability.tdx_kline_connection,
        "call_with_bounded_retry": retry,
        "Market": SimpleNamespace(**{
            market: SimpleNamespace(value=market.lower())
            for market in ["A", "FUTURES", "FX", "HK", "NY_FUTURES", "US"]
        }),
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SRC / f"{name}.py"), "exec"), namespace)
    provider = SimpleNamespace(
        _new_tdx_client=factory, connect_info=CONNECTION,
        reset_tdx_ip=lambda **kwargs: None,
        to_tdx_code=lambda code: (1, "TEST", "stock_cn") if name == "exchange_tdx" else (1, "TEST"),
        fdb=SimpleNamespace(
            get_tdx_klines=lambda *args: None,
            save_tdx_klines=lambda *args: True,
        ),
        tz=__import__("pytz").timezone("Asia/Shanghai"),
        fix_yp_date=lambda code, date: date,
        klines_qfq=lambda code, frame, **kwargs: frame,
        xdxr=lambda *args: pd.DataFrame([]),
        klines_fq=lambda frame, *args: frame,
    )
    provider.__convert_date = lambda date: date
    return lambda **kwargs: namespace["klines"](provider, "TEST.CODE", **kwargs), clients


@pytest.mark.parametrize("name", TDX_TARGETS)
@pytest.mark.parametrize("kwargs", [
    {"frequency": "invalid"},
    {"frequency": "d", "args": {"pages": 0}},
    {"frequency": "d", "args": {"pages": "bad"}},
    {"frequency": "d", "start_date": "2026-01-01"},
])
def test_all_tdx_invalid_requests_never_connect(name, kwargs):
    invoke, clients = _tdx_method(name)
    with pytest.raises(InvalidRequestError):
        invoke(**kwargs)
    assert clients == []


@pytest.mark.parametrize("name", TDX_TARGETS)
def test_all_tdx_network_exhaustion_preserves_cause(name):
    network = TimeoutError("socket timeout")
    invoke, clients = _tdx_method(name, FakeSdkError(network))
    with pytest.raises(reliability.ProviderUnavailableError) as error:
        invoke(frequency="d", args={"pages": 1})
    assert len(clients) == 3
    assert all(client.closed for client in clients)
    assert error.value.__cause__ is network


@pytest.mark.parametrize("name", TDX_TARGETS)
def test_all_tdx_programming_errors_are_not_retried(name):
    invoke, clients = _tdx_method(name, FakeSdkError(KeyError("malformed payload")))
    with pytest.raises(KeyError, match="malformed payload"):
        invoke(frequency="d", args={"pages": 1})
    assert len(clients) == 1


def test_tq_timeout_is_one_wait_and_not_a_no_data_result():
    tree = ast.parse((SRC / "exchange_tq.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "klines")
    assert method.decorator_list == []
    commands, waits = [], []

    class UnavailableError(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)

    provider = SimpleNamespace(
        res_klines={}, _put_command=commands.append,
        _wait_for_cache=lambda *args, **kwargs: waits.append(kwargs),
    )
    namespace = {"pd": pd, "Union": Union, "InvalidRequestError": InvalidRequestError,
                 "ProviderUnavailableError": UnavailableError}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "tq", "exec"), namespace)
    with pytest.raises(UnavailableError):
        namespace["klines"](provider, "SHFE.rb2610", "1m")
    assert len(commands) == len(waits) == 1
    assert waits[0]["timeout"] == 5.0


def test_ib_empty_history_returns_immediately_without_retry():
    tree = ast.parse((SRC / "exchange_ib.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeIB")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "klines")
    assert method.decorator_list == []
    calls = []
    provider = SimpleNamespace(_rpc=lambda *args, **kwargs: calls.append(args) or [])
    namespace = {"pd": pd, "Union": Union, "InvalidRequestError": InvalidRequestError,
                 "CmdEnum": SimpleNamespace(KLINES="klines")}
    exec(compile(ast.Module(body=[method], type_ignores=[]), "ib", "exec"), namespace)
    assert namespace["klines"](provider, "AAPL", "d").empty
    assert len(calls) == 1


@pytest.mark.parametrize("outcome", ["empty", "network", "bug"])
def test_binance_retries_only_network_errors_and_restores_timeout(monkeypatch, outcome):
    import ccxt
    from tradingview_zy.exchange import binance_reliability

    clock = FakeClock()
    monkeypatch.setattr(binance_reliability, "time", SimpleNamespace(monotonic=clock))
    monkeypatch.setattr(
        binance_reliability, "call_with_bounded_retry",
        lambda operation, **kwargs: reliability.call_with_bounded_retry(
            operation, **kwargs, clock=clock, sleeper=clock.sleep,
        ),
    )

    class Client:
        timeout = 10000
        calls = 0

        def fetch_ohlcv(self, **request):
            self.calls += 1
            assert self.timeout <= 4000
            assert request["symbol"] == "BTC/USDT"
            if outcome == "network":
                raise ccxt.NetworkError("private network details")
            if outcome == "bug":
                raise ValueError("bad response")
            return []

    client, lock = Client(), RLock()
    if outcome == "network":
        with pytest.raises(reliability.ProviderUnavailableError) as error:
            binance_reliability.fetch_ohlcv_with_retry(client, lock, deadline=12, symbol="BTC/USDT")
        assert isinstance(error.value.__cause__, ccxt.NetworkError)
        assert client.calls == 3
    elif outcome == "bug":
        with pytest.raises(ValueError, match="bad response"):
            binance_reliability.fetch_ohlcv_with_retry(client, lock, deadline=12, symbol="BTC/USDT")
        assert client.calls == 1
    else:
        assert binance_reliability.fetch_ohlcv_with_retry(client, lock, deadline=12, symbol="BTC/USDT") == []
        assert client.calls == 1
    assert client.timeout == 10000


def test_binance_all_pages_share_one_deadline(monkeypatch):
    from tradingview_zy.exchange import binance_reliability
    from tradingview_zy.exchange.binance_pagination import paginate_ohlcv

    clock = FakeClock()
    monkeypatch.setattr(binance_reliability, "time", SimpleNamespace(monotonic=clock))
    monkeypatch.setattr(
        binance_reliability, "call_with_bounded_retry",
        lambda operation, **kwargs: reliability.call_with_bounded_retry(
            operation, **kwargs, clock=clock, sleeper=clock.sleep,
        ),
    )

    class Client:
        timeout = 10000
        calls = 0

        def fetch_ohlcv(self, **request):
            self.calls += 1
            clock.now += self.timeout / 1000
            return [[self.calls * 1000, 1, 1, 1, 1, 1]]

    client, lock = Client(), RLock()
    with pytest.raises(binance_reliability.ProviderUnavailableError, match="deadline"):
        paginate_ohlcv(
            lambda params: binance_reliability.fetch_ohlcv_with_retry(
                client, lock, deadline=5, symbol="BTC/USDT", params=params,
            ),
            start_ms=0, page_limit=1, max_pages=100,
        )
    assert client.calls == 2
    assert clock.now == 5


def test_adjustment_timeout_keeps_slot_and_reports_retryable_error(monkeypatch):
    import threading
    import time
    from tradingview_zy.domain import ProviderUnavailableError
    from tradingview_zy.exchange import adjustment_reliability
    from tradingview_zy.sync_batch import DeadlineCaller, SyncCallBusyError, SyncCallTimeoutError

    calls = DeadlineCaller(max_concurrent=1)
    monkeypatch.setattr(adjustment_reliability, "_factor_calls", calls)
    entered, release = threading.Event(), threading.Event()

    def blocking_fetch():
        entered.set()
        release.wait(2)
        return "late result"

    try:
        with pytest.raises(ProviderUnavailableError) as timeout:
            adjustment_reliability.fetch_adjustment_factors(
                blocking_fetch, deadline=time.monotonic() + 0.05, provider="tdx_hk",
            )
        assert entered.is_set()
        assert timeout.value.retryable
        assert isinstance(timeout.value.__cause__, SyncCallTimeoutError)
        with pytest.raises(ProviderUnavailableError) as busy:
            adjustment_reliability.fetch_adjustment_factors(
                lambda: "must not start", deadline=time.monotonic() + 1, provider="tdx_us",
            )
        assert busy.value.retryable
        assert isinstance(busy.value.__cause__, SyncCallBusyError)
    finally:
        release.set()
        assert calls._slots.acquire(timeout=2)
        calls._slots.release()
    assert adjustment_reliability.fetch_adjustment_factors(
        lambda: "ready", deadline=time.monotonic() + 1, provider="tdx_us",
    ) == "ready"


def test_adjustment_io_error_cause_is_preserved_and_bugs_are_not_hidden():
    import time
    from requests.exceptions import ConnectionError as HttpConnectionError
    from tradingview_zy.domain import ProviderUnavailableError
    from tradingview_zy.exchange.adjustment_reliability import fetch_adjustment_factors

    network = HttpConnectionError("private-url")

    def fail():
        raise network

    with pytest.raises(ProviderUnavailableError) as error:
        fetch_adjustment_factors(fail, deadline=time.monotonic() + 1, provider="tdx_hk")
    assert error.value.__cause__ is network
    assert "private-url" not in str(error.value.to_dict())

    bug = ValueError("invalid factor")

    def broken():
        raise bug

    with pytest.raises(ValueError) as error:
        fetch_adjustment_factors(broken, deadline=time.monotonic() + 1, provider="tdx_us")
    assert error.value is bug


def test_binance_sdk_that_ignores_timeout_does_not_spawn_unbounded_workers(monkeypatch):
    import threading
    import time
    from tradingview_zy.exchange import binance_reliability
    from tradingview_zy.sync_batch import DeadlineCaller, SyncCallBusyError, SyncCallTimeoutError

    calls = DeadlineCaller(max_concurrent=1)
    monkeypatch.setattr(binance_reliability, "_ohlcv_calls", calls)
    release = threading.Event()

    class Client:
        timeout = 10000
        count = 0

        def fetch_ohlcv(self, **kwargs):
            self.count += 1
            release.wait(2)
            return []

    client, lock = Client(), RLock()
    try:
        with pytest.raises(binance_reliability.ProviderUnavailableError) as error:
            binance_reliability.fetch_ohlcv_with_retry(client, lock, deadline=time.monotonic() + 0.05)
        assert isinstance(error.value.__cause__, SyncCallTimeoutError)
        with pytest.raises(binance_reliability.ProviderUnavailableError) as error:
            binance_reliability.fetch_ohlcv_with_retry(client, lock, deadline=time.monotonic() + 1)
        assert isinstance(error.value.__cause__, SyncCallBusyError)
        assert client.count == 1
    finally:
        release.set()
        assert calls._slots.acquire(timeout=2)
        calls._slots.release()
    assert client.timeout == 10000


@pytest.mark.parametrize("name", TDX_TARGETS)
def test_all_tdx_successful_transport_keeps_canonical_bar_values(name):
    row = {
        "datetime": "2026-07-01 09:30:00", "open": 1.0, "high": 2.0,
        "low": 0.5, "close": 1.5, "vol": 10, "trade": 10, "amount": 10,
    }
    invoke, clients = _tdx_method(name, [row])
    frame = invoke(frequency="d", args={"pages": 1})
    assert list(frame.columns) == ["code", "date", "open", "close", "high", "low", "volume"]
    assert len(frame) == 1
    assert frame.iloc[0]["open"] == 1.0
    assert frame.iloc[0]["close"] == 1.5
    assert frame.iloc[0]["volume"] == 10.0
    assert frame.iloc[0]["date"].tzinfo is not None
    assert len(clients) == 1 and clients[0].closed
