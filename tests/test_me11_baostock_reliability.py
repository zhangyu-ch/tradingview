from __future__ import annotations

import ast
import importlib
import importlib.util
import sys
import types
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/tradingview_zy/exchange/exchange_baostock.py"
HELPER = ROOT / "src/tradingview_zy/exchange/baostock_reliability.py"
_spec = importlib.util.spec_from_file_location("baostock_reliability", HELPER)
assert _spec and _spec.loader
_reliability = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reliability)
BaostockQueryError = _reliability.BaostockQueryError
BaostockUnavailableError = _reliability.BaostockUnavailableError
call_baostock_query = _reliability.call_baostock_query
parse_baostock_datetime = _reliability.parse_baostock_datetime
recent_weekdays = _reliability.recent_weekdays


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class Result:
    def __init__(
        self,
        fields: list[str],
        rows: list[list[str]],
        *,
        error_code: str = "0",
        error_msg: str = "",
    ) -> None:
        self.fields = fields
        self.rows = rows
        self.error_code = error_code
        self.error_msg = error_msg
        self._index = -1

    def next(self) -> bool:
        self._index += 1
        return self._index < len(self.rows)

    def get_row_data(self) -> list[str]:
        return self.rows[self._index]


class LoginResult:
    def __init__(self, error_code: str = "0", error_msg: str = "") -> None:
        self.error_code = error_code
        self.error_msg = error_msg


def _load_provider(monkeypatch: pytest.MonkeyPatch, fake_bs: types.ModuleType):
    config = types.ModuleType("tradingview_zy.config")
    config.get_data_path = lambda: ROOT / "data"
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: "UTC"
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config)
    monkeypatch.setitem(sys.modules, "tzlocal", tzlocal)
    monkeypatch.setitem(sys.modules, "baostock", fake_bs)
    sys.modules.pop("tradingview_zy.fun", None)
    sys.modules.pop("tradingview_zy.exchange.exchange_baostock", None)
    return importlib.import_module("tradingview_zy.exchange.exchange_baostock")


def test_source_uses_minute_time_and_has_no_recursive_klines_retry() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    provider = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ExchangeBaostock"
    )
    klines = next(
        node
        for node in provider.body
        if isinstance(node, ast.FunctionDef) and node.name == "klines"
    )

    assert '"date,time,code' in source
    assert 'day = "2022-04-18"' not in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
        and node.func.attr == "klines"
        for node in ast.walk(klines)
    )


def test_source_timestamp_parser_preserves_real_gaps_and_milliseconds() -> None:
    first = parse_baostock_datetime("2026-08-03", "20260803093500123")
    second = parse_baostock_datetime("2026-08-03", "20260803100500000")

    assert first == datetime(2026, 8, 3, 9, 35, 0, 123000)
    assert second == datetime(2026, 8, 3, 10, 5)
    assert (second - first).total_seconds() == pytest.approx(1799.877)
    assert parse_baostock_datetime("2026-08-03") == datetime(2026, 8, 3, 15)

    with pytest.raises(ValueError, match="mismatch"):
        parse_baostock_datetime("2026-08-03", "20260804093500000")
    with pytest.raises(ValueError, match="missing"):
        parse_baostock_datetime("2026-08-03", "")


def test_relogin_retry_is_bounded_by_attempts_and_deadline() -> None:
    fake_time = FakeTime()
    query_calls = 0
    login_calls = 0

    def query() -> Result:
        nonlocal query_calls
        query_calls += 1
        fake_time.now += 0.35
        return Result([], [], error_code="10001001", error_msg="session expired")

    def login() -> LoginResult:
        nonlocal login_calls
        login_calls += 1
        return LoginResult()

    with pytest.raises(BaostockUnavailableError, match="after 3 attempt"):
        call_baostock_query(
            query,
            login,
            operation="history",
            max_attempts=3,
            deadline_seconds=2.0,
            base_delay_seconds=0.1,
            max_delay_seconds=0.1,
            clock=fake_time.clock,
            sleeper=fake_time.sleep,
        )

    assert query_calls == 3
    assert login_calls == 2
    assert fake_time.now <= 2.0


def test_non_auth_protocol_error_fails_without_retry() -> None:
    calls = 0

    def query() -> Result:
        nonlocal calls
        calls += 1
        return Result([], [], error_code="20000001", error_msg="bad request")

    with pytest.raises(BaostockQueryError, match="bad request"):
        call_baostock_query(query, lambda: LoginResult(), operation="history")
    assert calls == 1


def test_recent_weekday_fallback_is_finite_and_newest_first() -> None:
    days = recent_weekdays(date(2026, 8, 3), lookback_days=7)
    assert days == [
        date(2026, 8, 3),
        date(2026, 7, 31),
        date(2026, 7, 30),
        date(2026, 7, 29),
        date(2026, 7, 28),
        date(2026, 7, 27),
    ]


def test_provider_uses_exchange_minute_time_instead_of_row_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bs = types.ModuleType("baostock")
    fake_bs.login = lambda: LoginResult()
    captured_fields: list[str] = []

    def query_history(code: str, fields: str, **kwargs) -> Result:
        captured_fields.append(fields)
        return Result(
            ["date", "time", "code", "open", "low", "high", "close", "volume"],
            [
                ["2026-08-03", "20260803093500000", code, "10", "9", "11", "10.5", "100"],
                ["2026-08-03", "20260803100500000", code, "10.5", "10", "12", "11", "200"],
            ],
        )

    fake_bs.query_history_k_data_plus = query_history
    fake_bs.query_trade_dates = lambda **kwargs: Result(
        ["calendar_date", "is_trading_day"], []
    )
    fake_bs.query_all_stock = lambda **kwargs: Result(
        ["code", "tradeStatus", "code_name"], []
    )
    fake_bs.query_stock_basic = lambda **kwargs: Result([], [])

    module = _load_provider(monkeypatch, fake_bs)
    provider = module.ExchangeBaostock()
    frame = provider.klines(
        "sh.600000", "5m", start_date="2026-08-03", end_date="2026-08-03"
    )

    assert "date,time,code" in captured_fields[0]
    assert list(frame["date"].dt.strftime("%H:%M:%S")) == ["09:35:00", "10:05:00"]
    assert str(frame["date"].dt.tz) == "Asia/Shanghai"
    assert frame["volume"].tolist() == [100, 200]


def test_catalog_uses_latest_available_trading_day_and_daily_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_bs = types.ModuleType("baostock")
    fake_bs.login = lambda: LoginResult()
    fake_bs.query_history_k_data_plus = lambda *args, **kwargs: Result([], [])
    fake_bs.query_stock_basic = lambda **kwargs: Result([], [])
    fake_bs.query_trade_dates = lambda **kwargs: Result(
        ["calendar_date", "is_trading_day"],
        [
            ["2026-07-31", "1"],
            ["2026-08-01", "0"],
            ["2026-08-02", "0"],
            ["2026-08-03", "1"],
        ],
    )
    catalog_calls: list[str] = []

    def query_all_stock(*, day: str) -> Result:
        catalog_calls.append(day)
        if day == "2026-08-03":
            return Result(["code", "tradeStatus", "code_name"], [])
        return Result(
            ["code", "tradeStatus", "code_name"],
            [
                ["sh.600000", "1", "浦发银行"],
                ["sh.000001", "1", "上证指数"],
                ["sz.000001", "1", "平安银行"],
            ],
        )

    fake_bs.query_all_stock = query_all_stock
    module = _load_provider(monkeypatch, fake_bs)
    monkeypatch.setattr(module, "market_date", lambda _tz: date(2026, 8, 3))
    provider = module.ExchangeBaostock()

    expected = [
        {"code": "sh.600000", "name": "浦发银行"},
        {"code": "sz.000001", "name": "平安银行"},
    ]
    assert provider.all_stocks() == expected
    assert catalog_calls == ["2026-08-03", "2026-07-31"]
    assert provider.all_stocks() == expected
    assert catalog_calls == ["2026-08-03", "2026-07-31"]
