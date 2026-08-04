from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from test_support.web_routes import route_source

ROOT = Path(__file__).resolve().parents[1]
QUOTE_HELPER = ROOT / "src/tradingview_zy/exchange/tdx_quotes.py"
CALENDAR_HELPER = ROOT / "src/tradingview_zy/trading_calendar.py"
TDX_FILES = [
    ROOT / "src/tradingview_zy/exchange/exchange_tdx.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_hk.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_us.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_fx.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_futures.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_ny_futures.py",
]
CALENDAR_ADAPTERS = {
    ROOT / "src/tradingview_zy/exchange/exchange_tdx.py": "a",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_hk.py": "hk",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_us.py": "us",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_fx.py": "fx",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _aware(year: int, month: int, day: int, hour: int, minute: int, zone: str):
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(zone))


def test_change_rate_uses_previous_close_and_marks_invalid_quotes_unavailable() -> None:
    quotes = _load_module("me12_tdx_quotes", QUOTE_HELPER)

    assert quotes.calculate_change_rate(110, 100) == 10.0
    assert quotes.calculate_change_rate(90, 100) == -10.0
    assert quotes.calculate_change_rate("101.25", "100") == 1.25

    for last, previous in [
        (100, 0),
        (100, None),
        (0, 100),
        (float("nan"), 100),
        (100, float("inf")),
        ("bad", 100),
    ]:
        assert quotes.calculate_change_rate(last, previous) is None


def test_a_share_calendar_handles_lunch_weekends_and_2026_holidays() -> None:
    calendar = _load_module("me12_trading_calendar_a", CALENDAR_HELPER)
    shanghai = "Asia/Shanghai"

    assert calendar.is_market_open("a", _aware(2026, 8, 3, 9, 30, shanghai))
    assert calendar.is_market_open("a", _aware(2026, 8, 3, 11, 29, shanghai))
    assert not calendar.is_market_open("a", _aware(2026, 8, 3, 11, 30, shanghai))
    assert not calendar.is_market_open("a", _aware(2026, 8, 3, 12, 30, shanghai))
    assert calendar.is_market_open("a", _aware(2026, 8, 3, 13, 0, shanghai))
    assert not calendar.is_market_open("a", _aware(2026, 8, 3, 15, 0, shanghai))
    assert not calendar.is_market_open("a", _aware(2026, 8, 1, 10, 0, shanghai))
    assert not calendar.is_market_open("a", _aware(2026, 10, 1, 10, 0, shanghai))

    metadata = calendar.market_calendar_metadata("a")
    assert metadata["version"] == "SSE-2026-v1"
    assert metadata["covered_years"] == (2026,)


def test_hk_calendar_handles_lunch_holidays_and_half_days() -> None:
    calendar = _load_module("me12_trading_calendar_hk", CALENDAR_HELPER)
    hk = "Asia/Hong_Kong"

    assert calendar.is_market_open("hk", _aware(2026, 8, 3, 9, 30, hk))
    assert not calendar.is_market_open("hk", _aware(2026, 8, 3, 12, 30, hk))
    assert calendar.is_market_open("hk", _aware(2026, 8, 3, 13, 0, hk))
    assert not calendar.is_market_open("hk", _aware(2026, 2, 17, 10, 0, hk))
    assert calendar.is_market_open("hk", _aware(2026, 2, 16, 11, 59, hk))
    assert not calendar.is_market_open("hk", _aware(2026, 2, 16, 13, 0, hk))


def test_us_calendar_is_dst_aware_and_honours_early_close() -> None:
    calendar = _load_module("me12_trading_calendar_us", CALENDAR_HELPER)
    ny = "America/New_York"

    assert calendar.is_market_open("us", _aware(2026, 1, 5, 9, 30, ny))
    assert calendar.is_market_open("us", _aware(2026, 7, 6, 9, 30, ny))
    assert not calendar.is_market_open("us", _aware(2026, 11, 26, 10, 0, ny))
    assert calendar.is_market_open("us", _aware(2026, 11, 27, 12, 59, ny))
    assert not calendar.is_market_open("us", _aware(2026, 11, 27, 13, 0, ny))

    # UTC conversion must follow America/New_York DST, not a fixed offset.
    assert calendar.is_market_open(
        "us", datetime(2026, 7, 6, 13, 30, tzinfo=timezone.utc)
    )
    assert not calendar.is_market_open(
        "us", datetime(2026, 1, 5, 13, 30, tzinfo=timezone.utc)
    )


def test_fx_calendar_is_24x5_with_new_york_week_boundary() -> None:
    calendar = _load_module("me12_trading_calendar_fx", CALENDAR_HELPER)
    ny = "America/New_York"

    assert calendar.is_market_open("fx", _aware(2026, 8, 7, 16, 59, ny))
    assert not calendar.is_market_open("fx", _aware(2026, 8, 7, 17, 0, ny))
    assert not calendar.is_market_open("fx", _aware(2026, 8, 9, 16, 59, ny))
    assert calendar.is_market_open("fx", _aware(2026, 8, 9, 17, 0, ny))
    assert calendar.is_market_open("fx", _aware(2026, 8, 10, 3, 0, ny))


def test_calendar_rejects_naive_times_and_fails_closed_outside_versioned_coverage() -> None:
    calendar = _load_module("me12_trading_calendar_boundaries", CALENDAR_HELPER)

    with pytest.raises(ValueError, match="timezone-aware"):
        calendar.is_market_open("a", datetime(2026, 8, 3, 10, 0))
    with pytest.raises(ValueError, match="unsupported"):
        calendar.is_market_open("crypto", datetime.now(timezone.utc))

    assert not calendar.is_market_open(
        "a", _aware(2027, 1, 4, 10, 0, "Asia/Shanghai")
    )


def test_all_tdx_tick_paths_use_shared_rate_contract() -> None:
    for path in TDX_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        tick_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Tick"
        ]
        assert tick_calls, path
        for call in tick_calls:
            rate_keywords = [kw for kw in call.keywords if kw.arg == "rate"]
            assert len(rate_keywords) == 1, (path, call.lineno)
            value = rate_keywords[0].value
            assert isinstance(value, ast.Call), (path, call.lineno)
            assert isinstance(value.func, ast.Name), (path, call.lineno)
            assert value.func.id == "calculate_change_rate", (path, call.lineno)


def test_a_catalog_retry_is_bounded_and_non_recursive() -> None:
    path = ROOT / "src/tradingview_zy/exchange/exchange_tdx.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    provider = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ExchangeTDX"
    )
    all_stocks = next(
        node
        for node in provider.body
        if isinstance(node, ast.FunctionDef) and node.name == "all_stocks"
    )

    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
        and node.func.attr == "all_stocks"
        for node in ast.walk(all_stocks)
    )
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "call_with_bounded_retry"
        for node in ast.walk(all_stocks)
    )


def test_tdx_cash_adapters_delegate_trading_state_to_shared_calendar() -> None:
    for path, market in CALENDAR_ADAPTERS.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        provider = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        method = next(
            node
            for node in provider.body
            if isinstance(node, ast.FunctionDef) and node.name == "now_trading"
        )
        calls = [
            node
            for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "is_market_open"
        ]
        assert len(calls) == 1, path
        assert isinstance(calls[0].args[0], ast.Constant)
        assert calls[0].args[0].value == market


def test_nullable_rate_is_serialized_and_rendered_as_unavailable() -> None:
    tick_route_source = route_source("ticks")
    js_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/static/js/zixuan.js"
    ).read_text(encoding="utf-8")
    exchange_source = (
        ROOT / "src/tradingview_zy/exchange/exchange.py"
    ).read_text(encoding="utf-8")

    assert "float | None" in exchange_source
    assert "if tick.rate is None" in tick_route_source
    assert "rateAvailable" in js_source
    assert "rateText" in js_source
    assert 'tick["rate"] + "%"' in js_source


def test_a_catalog_stops_after_three_connection_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib
    import types
    from dataclasses import dataclass

    class FakeTdxConnectionError(ConnectionError):
        pass

    attempts = 0

    class FailingContext:
        def __enter__(self):
            nonlocal attempts
            attempts += 1
            raise FakeTdxConnectionError("node down")

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTdxApi:
        def __init__(self, **_kwargs) -> None:
            pass

        def connect(self, *_args, **_kwargs):
            return FailingContext()

    pytdx = types.ModuleType("pytdx")
    pytdx_errors = types.ModuleType("pytdx.errors")
    pytdx_errors.TdxConnectionError = FakeTdxConnectionError
    pytdx_hq = types.ModuleType("pytdx.hq")
    pytdx_hq.TdxHq_API = FakeTdxApi
    monkeypatch.setitem(sys.modules, "pytdx", pytdx)
    monkeypatch.setitem(sys.modules, "pytdx.errors", pytdx_errors)
    monkeypatch.setitem(sys.modules, "pytdx.hq", pytdx_hq)

    tenacity = types.ModuleType("tenacity")
    tenacity.retry = lambda *args, **kwargs: (lambda function: function)
    tenacity.retry_if_result = lambda *args, **kwargs: object()
    tenacity.stop_after_attempt = lambda *args, **kwargs: object()
    tenacity.wait_random = lambda *args, **kwargs: object()
    monkeypatch.setitem(sys.modules, "tenacity", tenacity)

    fun = types.ModuleType("tradingview_zy.fun")
    fun.singleton = lambda cls: cls
    monkeypatch.setitem(sys.modules, "tradingview_zy.fun", fun)

    exchange = types.ModuleType("tradingview_zy.exchange.exchange")

    class FakeExchange:
        pass

    @dataclass
    class FakeTick:
        code: str
        last: float
        buy1: float
        sell1: float
        high: float
        low: float
        open: float
        volume: float
        rate: float | None = 0.0

    exchange.Exchange = FakeExchange
    exchange.Tick = FakeTick
    exchange.LiveTradingDisabledError = RuntimeError
    exchange.convert_stock_kline_frequency = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "tradingview_zy.exchange.exchange", exchange)

    config = types.ModuleType("tradingview_zy.config")
    config.get_data_path = lambda: ROOT / "data"
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config)

    db_module = types.ModuleType("tradingview_zy.db")
    db_module.db = types.SimpleNamespace(cache_get=lambda _key: None, cache_set=lambda *a, **k: True)
    monkeypatch.setitem(sys.modules, "tradingview_zy.db", db_module)

    stocks = types.ModuleType("tradingview_zy.exchange.stocks_bkgn")
    stocks.StocksBKGN = object
    monkeypatch.setitem(sys.modules, "tradingview_zy.exchange.stocks_bkgn", stocks)
    codes = types.ModuleType("tradingview_zy.exchange.tdx_a_codes")
    codes.tdx_codes_by_bj = {}
    codes.tdx_codes_by_error = []
    monkeypatch.setitem(sys.modules, "tradingview_zy.exchange.tdx_a_codes", codes)
    file_db = types.ModuleType("tradingview_zy.file_db")
    file_db.FileCacheDB = object
    monkeypatch.setitem(sys.modules, "tradingview_zy.file_db", file_db)
    best_ip = types.ModuleType("tradingview_zy.tools.tdx_best_ip")
    best_ip.select_best_ip = lambda _kind: {"ip": "127.0.0.1", "port": 7709}
    best_ip.cache_expiry_epoch = lambda: 0
    monkeypatch.setitem(sys.modules, "tradingview_zy.tools.tdx_best_ip", best_ip)

    sys.modules.pop("tradingview_zy.exchange.exchange_tdx", None)
    module = importlib.import_module("tradingview_zy.exchange.exchange_tdx")
    # ``fun.singleton`` wraps classes with ``functools.wraps``.  Another test
    # may already have imported the real decorator before our module stubs are
    # installed, so always unwrap the provider type instead of assuming the
    # exported symbol itself is a class.
    provider_type = getattr(module.ExchangeTDX, "__wrapped__", module.ExchangeTDX)
    provider = provider_type.__new__(provider_type)
    provider.g_all_stocks = []
    provider.connect_info = {"ip": "127.0.0.1", "port": 7709}
    recoveries = 0

    def recover():
        nonlocal recoveries
        recoveries += 1
        return provider.connect_info

    provider.reset_tdx_ip = recover

    error_type = module.call_with_bounded_retry.__globals__["ProviderUnavailableError"]
    with pytest.raises(error_type, match="after 3 attempts"):
        provider.all_stocks()

    assert attempts == 3
    assert recoveries == 2
