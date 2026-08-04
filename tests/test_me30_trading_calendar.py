from __future__ import annotations

import ast
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
CALENDAR = ROOT / "src/tradingview_zy/trading_calendar.py"
EXCHANGE_ROOT = ROOT / "src/tradingview_zy/exchange"
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
ALERT_TASKS = ROOT / "web/tradingview_zy_chart/cl_app/alert_tasks.py"


def _load_calendar():
    name = "me30_trading_calendar"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, CALENDAR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _aware(year: int, month: int, day: int, hour: int, minute: int, zone: str):
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(zone))


def test_cn_futures_day_sessions_are_instrument_specific() -> None:
    calendar = _load_calendar()
    sh = "Asia/Shanghai"

    # Commodity exchanges: 09:00-10:15, 10:30-11:30, 13:30-15:00.
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 9, 0, sh))
    assert not calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 10, 15, sh))
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 10, 30, sh))
    assert not calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 11, 30, sh))
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 13, 30, sh))
    assert not calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 15, 0, sh))

    # CFFEX index and treasury products have different afternoon closes.
    assert not calendar.is_market_open("futures", "CFFEX.IF2608", _aware(2026, 8, 3, 9, 29, sh))
    assert calendar.is_market_open("futures", "CFFEX.IF2608", _aware(2026, 8, 3, 9, 30, sh))
    assert not calendar.is_market_open("futures", "CFFEX.IF2608", _aware(2026, 8, 3, 15, 0, sh))
    assert calendar.is_market_open("futures", "CFFEX.T2609", _aware(2026, 8, 3, 15, 14, sh))
    assert not calendar.is_market_open("futures", "CFFEX.T2609", _aware(2026, 8, 3, 15, 15, sh))


def test_cn_futures_night_profiles_have_distinct_endpoints() -> None:
    calendar = _load_calendar()
    sh = "Asia/Shanghai"

    # 23:00, 01:00 and 02:30 profiles are half-open at their close.
    assert calendar.is_market_open("futures", "QS.RBL8", _aware(2026, 8, 3, 21, 0, sh))
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 22, 59, sh))
    assert not calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 3, 23, 0, sh))

    assert calendar.is_market_open("futures", "SHFE.CU2608", _aware(2026, 8, 4, 0, 59, sh))
    assert not calendar.is_market_open("futures", "SHFE.CU2608", _aware(2026, 8, 4, 1, 0, sh))

    assert calendar.is_market_open("futures", "SHFE.AU2612", _aware(2026, 8, 4, 2, 29, sh))
    assert not calendar.is_market_open("futures", "SHFE.AU2612", _aware(2026, 8, 4, 2, 30, sh))
    assert not calendar.is_market_open("futures", "CZCE.AP610", _aware(2026, 8, 3, 21, 0, sh))


def test_cn_futures_weekend_holiday_and_unknown_inputs_fail_closed() -> None:
    calendar = _load_calendar()
    sh = "Asia/Shanghai"

    # Friday night may continue into Saturday; Saturday night/Sunday early does not.
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 8, 7, 21, 0, sh))
    assert calendar.is_market_open("futures", "SHFE.AU2612", _aware(2026, 8, 8, 0, 30, sh))
    assert not calendar.is_market_open("futures", "SHFE.AU2612", _aware(2026, 8, 9, 0, 30, sh))

    # The long Spring Festival gap suppresses the preceding Friday night session.
    assert not calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 2, 13, 21, 0, sh))
    assert calendar.is_market_open("futures", "SHFE.RB2510", _aware(2026, 2, 24, 9, 0, sh))

    assert not calendar.is_market_open("futures", None, _aware(2026, 8, 3, 9, 0, sh))
    assert not calendar.is_market_open("futures", "SHFE.NEW9999", _aware(2026, 8, 3, 9, 0, sh))
    assert not calendar.is_market_open("futures", "SHFE.RB2701", _aware(2027, 1, 4, 9, 0, sh))


def test_ny_futures_week_boundary_maintenance_and_dst_are_explicit() -> None:
    calendar = _load_calendar()
    ny = "America/New_York"
    code = "CO.GC00W"

    assert calendar.is_market_open("ny_futures", code, _aware(2026, 1, 5, 16, 59, ny))
    assert not calendar.is_market_open("ny_futures", code, _aware(2026, 1, 5, 17, 0, ny))
    assert calendar.is_market_open("ny_futures", code, _aware(2026, 1, 5, 18, 0, ny))
    assert calendar.is_market_open("ny_futures", code, _aware(2026, 1, 9, 16, 59, ny))
    assert not calendar.is_market_open("ny_futures", code, _aware(2026, 1, 9, 17, 0, ny))
    assert not calendar.is_market_open("ny_futures", code, _aware(2026, 1, 11, 17, 59, ny))
    assert calendar.is_market_open("ny_futures", code, _aware(2026, 1, 11, 18, 0, ny))

    # The same UTC wall time lands in the maintenance break in winter but not summer.
    assert not calendar.is_market_open(
        "ny_futures", code, datetime(2026, 1, 5, 22, 30, tzinfo=timezone.utc)
    )
    assert calendar.is_market_open(
        "ny_futures", code, datetime(2026, 7, 6, 22, 30, tzinfo=timezone.utc)
    )


def test_ny_futures_holidays_unknown_products_and_years_fail_closed() -> None:
    calendar = _load_calendar()
    ny = "America/New_York"

    assert not calendar.is_market_open("ny_futures", "CO.GC00W", _aware(2026, 12, 25, 10, 0, ny))
    assert not calendar.is_market_open("ny_futures", "CO.GC00W", _aware(2026, 12, 24, 18, 0, ny))
    assert not calendar.is_market_open("ny_futures", None, _aware(2026, 8, 3, 12, 0, ny))
    assert not calendar.is_market_open("ny_futures", "CO.UNKNOWN", _aware(2026, 8, 3, 12, 0, ny))
    assert not calendar.is_market_open("ny_futures", "CO.GC00W", _aware(2027, 1, 4, 12, 0, ny))

    metadata = calendar.market_calendar_metadata("ny_futures", "CO.GC00W")
    assert metadata["version"] == "CME-GLOBEX-2026-v1"
    assert metadata["instrument_root"] == "GC"


def test_crypto_24x7_and_fx_24x5_remain_distinct_contracts() -> None:
    calendar = _load_calendar()
    utc_weekend = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    ny = "America/New_York"

    assert calendar.is_market_open("currency", "BTC/USDT", utc_weekend)
    assert calendar.is_market_open("currency_spot", "ETH/USDT", utc_weekend)
    assert not calendar.is_market_open("fx", "EURUSD", _aware(2026, 8, 7, 17, 0, ny))
    assert calendar.is_market_open("fx", "EURUSD", _aware(2026, 8, 9, 17, 0, ny))

    with pytest.raises(ValueError, match="timezone-aware"):
        calendar.is_market_open("currency", "BTC/USDT", datetime(2026, 8, 8, 12, 0))
    with pytest.raises(ValueError, match="unsupported"):
        calendar.is_market_open("crypto", "BTC/USDT", utc_weekend)


def test_all_reachable_providers_expose_instrument_aware_bool_contract() -> None:
    expected = {
        "exchange_alpaca.py": ("ExchangeAlpaca", "us"),
        "exchange_baostock.py": ("ExchangeBaostock", "a"),
        "exchange_binance.py": ("ExchangeBinance", "currency"),
        "exchange_binance_spot.py": ("ExchangeBinanceSpot", "currency_spot"),
        "exchange_ib.py": ("ExchangeIB", "us"),
        "exchange_polygon.py": ("ExchangePolygon", "us"),
        "exchange_qmt.py": ("ExchangeQMT", "a"),
        "exchange_tdx.py": ("ExchangeTDX", "a"),
        "exchange_tdx_futures.py": ("ExchangeTDXFutures", "futures"),
        "exchange_tdx_fx.py": ("ExchangeTDXFX", "fx"),
        "exchange_tdx_hk.py": ("ExchangeTDXHK", "hk"),
        "exchange_tdx_ny_futures.py": ("ExchangeTDXNYFutures", "ny_futures"),
        "exchange_tdx_us.py": ("ExchangeTDXUS", "us"),
        "exchange_tq.py": ("ExchangeTq", "futures"),
    }
    forbidden_calls = {"strftime", "get_market_status", "market_trade_days"}

    for filename, (class_name, market) in expected.items():
        path = EXCHANGE_ROOT / filename
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        provider = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        method = next(
            node for node in provider.body
            if isinstance(node, ast.FunctionDef) and node.name == "now_trading"
        )
        assert [arg.arg for arg in method.args.args] == ["self", "code", "at"], path
        assert ast.unparse(method.returns) == "bool", path
        calls = [
            node for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "is_market_open"
        ]
        assert len(calls) == 1, path
        assert ast.literal_eval(calls[0].args[0]) == market, path
        assert {kw.arg for kw in calls[0].keywords} == {"code", "at"}, path
        assert not any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in forbidden_calls
            for node in ast.walk(method)
        ), path

    # Multi-market Futu resolves the calendar from a concrete code; DB is explicit false.
    futu_path = EXCHANGE_ROOT / "exchange_futu.py"
    futu_source = futu_path.read_text(encoding="utf-8")
    futu_tree = ast.parse(futu_source, filename=str(futu_path))
    futu_class = next(node for node in futu_tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeFutu")
    futu_method = next(node for node in futu_class.body if isinstance(node, ast.FunctionDef) and node.name == "now_trading")
    assert [arg.arg for arg in futu_method.args.args] == ["self", "code", "at"]
    assert ast.unparse(futu_method.returns) == "bool"
    assert 'prefix in {"SH", "SZ", "BJ"}' in futu_source
    assert 'prefix == "HK"' in futu_source
    assert "return False" in ast.get_source_segment(futu_source, futu_method)

    base_tree = ast.parse((EXCHANGE_ROOT / "exchange.py").read_text(encoding="utf-8"))
    base_class = next(node for node in base_tree.body if isinstance(node, ast.ClassDef) and node.name == "Exchange")
    base_method = next(node for node in base_class.body if isinstance(node, ast.FunctionDef) and node.name == "now_trading")
    assert [arg.arg for arg in base_method.args.args] == ["self", "code", "at"]
    assert ast.unparse(base_method.returns) == "bool"

    db_tree = ast.parse((EXCHANGE_ROOT / "exchange_db.py").read_text(encoding="utf-8"))
    db_class = next(node for node in db_tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeDB")
    db_method = next(node for node in db_class.body if isinstance(node, ast.FunctionDef) and node.name == "now_trading")
    assert [arg.arg for arg in db_method.args.args] == ["self", "code", "at"]
    assert any(isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and node.value.value is False for node in ast.walk(db_method))


def test_web_and_monitoring_callers_pass_concrete_codes_and_keep_bad_targets() -> None:
    web_source = WEB_APP.read_text(encoding="utf-8")
    alert_source = ALERT_TASKS.read_text(encoding="utf-8")

    assert "ex.now_trading(code) is False" in web_source
    assert "ex.now_trading(code) for code in tick_request.codes" in web_source
    assert "exchange.now_trading(code)" in alert_source
    assert ".now_trading()" not in web_source
    assert ".now_trading()" not in alert_source

    tree = ast.parse(alert_source, filename=str(ALERT_TASKS))
    alert_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AlertTasks"
    )
    helper = next(
        node for node in alert_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "_stocks_in_open_sessions"
    )
    isolated = ast.Module(body=[helper], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace: dict[str, object] = {}
    exec(compile(isolated, str(ALERT_TASKS), "exec"), namespace)

    class FakeExchange:
        def now_trading(self, code, at=None):
            return code == "OPEN"

    stocks = [
        {"code": "OPEN", "name": "open"},
        {"code": "CLOSED", "name": "closed"},
        {"name": "missing-code"},
        "malformed",
    ]
    result = namespace["_stocks_in_open_sessions"](FakeExchange(), stocks)
    assert result == [stocks[0], stocks[2], stocks[3]]
