from __future__ import annotations

import ast
import datetime as dt
import importlib
import importlib.util
import json
import math
import sys
import types
from dataclasses import replace
from datetime import timezone
from pathlib import Path

import pandas as pd
import pytest

from tradingview_zy.base import Market
from tradingview_zy.domain import (
    Capability,
    Frequency,
    InvalidRequestError,
    OperationAction,
    OrderOffset,
    OrderSide,
    OrderStatus,
    PositionSide,
    ProviderResponseError,
    TradeMode,
    parse_frequency,
    parse_operation_action,
    parse_order_offset,
    parse_order_side,
    parse_order_status,
    parse_position_side,
    parse_trade_mode,
)
from tradingview_zy.exchange.contracted import ContractedExchange
from tradingview_zy.market_registry import (
    MARKET_REGISTRY,
    ProviderSpec,
    parse_market,
    validate_market_registry,
)
from tradingview_zy.strategies.base import (
    StrategyAction,
    StrategyPurpose,
    StrategySignal,
    strategy_target_from_stock,
    validate_strategy_signals,
)
from tradingview_zy.web_api_validation import WebParameterError, parse_resolution

ROOT = Path(__file__).resolve().parents[1]
BACKTEST_BASE = ROOT / "src" / "tradingview_zy" / "backtesting" / "base.py"


def test_market_and_frequency_are_stable_string_codes() -> None:
    assert Market.A == "a"
    assert str(Market.US) == "us"
    assert parse_market("  HK  ") is Market.HK
    assert parse_frequency(" 4H ") is Frequency.HOUR_4
    assert json.dumps({"market": Market.A, "frequency": Frequency.DAY}) == (
        '{"market": "a", "frequency": "d"}'
    )

    for value in [None, True, 1, "", "unknown", "a\n"]:
        with pytest.raises((InvalidRequestError, TypeError, ValueError)):
            parse_market(value)  # type: ignore[arg-type]
    for value in [None, True, 1, "", "day", "d\n", "x" * 100]:
        with pytest.raises((TypeError, ValueError)):
            parse_frequency(value)



def test_every_provider_frequency_literal_is_a_domain_code() -> None:
    locations: list[str] = []
    for path in (ROOT / "src" / "tradingview_zy" / "exchange").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name != "support_frequencys":
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Dict):
                    continue
                for key in child.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        try:
                            parse_frequency(key.value)
                        except (TypeError, ValueError):
                            locations.append(f"{path.name}:{key.lineno}:{key.value}")
    assert locations == []

def test_order_domain_parsers_accept_known_aliases_and_reject_typos() -> None:
    assert parse_order_side(" BUY ") is OrderSide.BUY
    assert parse_position_side("做多") is PositionSide.LONG
    assert parse_position_side("SHORT") is PositionSide.SHORT
    assert parse_order_offset("closeToday") is OrderOffset.CLOSE_TODAY
    assert parse_order_status("cancelled") is OrderStatus.CANCELED
    assert parse_operation_action("open") is OperationAction.OPEN
    assert parse_operation_action("buy") is OperationAction.OPEN
    assert parse_operation_action("close") is OperationAction.CLOSE
    assert parse_trade_mode(" TRADE ") is TradeMode.TRADE

    parsers = [
        parse_order_side,
        parse_position_side,
        parse_order_offset,
        parse_order_status,
        parse_operation_action,
        parse_trade_mode,
    ]
    for parser in parsers:
        for value in [None, True, "", "typo", "buy\x00sell"]:
            with pytest.raises((TypeError, ValueError)):
                parser(value)


def test_market_registry_rejects_invalid_frequency_codes() -> None:
    registry = dict(MARKET_REGISTRY)
    registry[Market.A] = replace(
        MARKET_REGISTRY[Market.A], frequencies={"day": "D"}
    )
    with pytest.raises(RuntimeError, match="周期元数据无效"):
        validate_market_registry(registry)


class _RawProvider:
    def __init__(self, frequencies: dict[str, str] | None = None) -> None:
        self.frequencies = frequencies or {"d": "D"}
        self.kline_calls: list[tuple[str, str]] = []

    def default_code(self) -> str:
        return "SH.000001"

    def support_frequencys(self) -> dict[str, str]:
        return self.frequencies

    def klines(self, code: str, frequency: str, **_kwargs):
        self.kline_calls.append((code, frequency))
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-08-04"),
                    "open": 1.0,
                    "high": 1.2,
                    "low": 0.9,
                    "close": 1.1,
                    "volume": 10.0,
                }
            ]
        )


def _facade(provider: _RawProvider) -> ContractedExchange:
    spec = ProviderSpec(
        module="tests.fake",
        attribute="Fake",
        capabilities=frozenset({Capability.METADATA, Capability.MARKET_DATA}),
    )
    return ContractedExchange(Market.A, "fake", provider, spec)


def test_provider_facade_rejects_frequency_typos_before_sdk_call() -> None:
    raw = _RawProvider()
    facade = _facade(raw)

    result = facade.klines("SH.000001", " D ")
    assert len(result) == 1
    assert raw.kline_calls == [("SH.000001", "d")]

    with pytest.raises(InvalidRequestError, match="K 线周期无效"):
        facade.klines("SH.000001", "day")
    with pytest.raises(InvalidRequestError, match="不支持周期 1m"):
        facade.klines("SH.000001", Frequency.MINUTE_1)
    assert raw.kline_calls == [("SH.000001", "d")]


def test_provider_metadata_cannot_publish_non_domain_frequency() -> None:
    facade = _facade(_RawProvider({"day": "D"}))
    with pytest.raises(ProviderResponseError, match="周期元数据响应无效"):
        facade.support_frequencys()


def test_strategy_boundary_canonicalizes_market_and_frequency() -> None:
    target = strategy_target_from_stock(
        " A ", {"code": "SH.600000", "name": "浦发银行"}, " D "
    )
    assert target.market is Market.A
    assert target.frequency is Frequency.DAY

    now = dt.datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc)
    signals = validate_strategy_signals(
        StrategySignal(
            code=target.code,
            name=target.name,
            action=StrategyAction.WATCH,
            score=0.0,
            message="typed",
            frequency="D",
            event_time=now,
        ),
        target,
        purpose=StrategyPurpose.MONITORING,
        context_now=now,
    )
    assert signals[0].frequency is Frequency.DAY
    assert signals[0].to_payload()["frequency"] == "d"

    bad = StrategySignal(
        code=target.code,
        name=target.name,
        action=StrategyAction.WATCH,
        score=1.0,
        message="bad",
        frequency="day",
        event_time=now,
    )
    with pytest.raises(ValueError, match="frequency is unsupported"):
        validate_strategy_signals(
            bad,
            target,
            purpose=StrategyPurpose.MONITORING,
            context_now=now,
        )


def test_web_resolution_returns_domain_frequency_and_rejects_bad_internal_map() -> None:
    resolution, frequency = parse_resolution("1D", resolution_map={"1D": "d"})
    assert resolution == "1D"
    assert frequency is Frequency.DAY
    with pytest.raises(WebParameterError, match="unsupported internal frequency"):
        parse_resolution("1D", resolution_map={"1D": "day"})


def _load_backtest_base():
    module_name = "_lo03_backtesting_base"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, BACKTEST_BASE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_backtest_operation_and_constructor_boundaries_are_typed() -> None:
    module = _load_backtest_base()

    opened = module.Operation("SH.000001", "open", "breakout")
    closed = module.Operation("SH.000001", "SELL", "exit")
    assert opened.opt is OperationAction.OPEN
    assert opened.opt == "buy"
    assert closed.opt is OperationAction.CLOSE
    assert closed.opt == "sell"
    with pytest.raises(ValueError, match="unsupported operation action"):
        module.Operation("SH.000001", "hold", "bad")

    class Datas(module.MarketDatas):
        def klines(self, code, frequency):
            return pd.DataFrame()

        def last_k_info(self, code):
            return {}

    class Trader(module.Trader):
        def get_price(self, code):
            return {}

        def hold_positions(self):
            return []

    datas = Datas(" US ", ["D", Frequency.MINUTE_5])
    trader = Trader("typed", mode="TRADE", market="HK")
    assert datas.market is Market.US
    assert datas.frequencys == [Frequency.DAY, Frequency.MINUTE_5]
    assert trader.market is Market.HK
    assert trader.mode is TradeMode.TRADE

    assert module.fee_a(OperationAction.CLOSE, 10, 100) > module.fee_a(
        OperationAction.OPEN, 10, 100
    )


def _load_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for name in ["tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config"]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: timezone.utc
    monkeypatch.setitem(sys.modules, "tzlocal", tzlocal)

    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "lo03"
    config.DB_HOST = "127.0.0.1"
    config.DB_PORT = 3306
    config.DB_USER = "user"
    config.DB_PWD = "env://TEST_DB_PASSWORD"
    config.get_data_path = lambda: tmp_path
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config)
    package = importlib.import_module("tradingview_zy")
    monkeypatch.setattr(package, "config", config, raising=False)
    return importlib.import_module("tradingview_zy.db")


def test_db_kline_boundary_stores_only_canonical_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_db(tmp_path, monkeypatch)
    bars = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-08-04 15:00:00"),
                "open": 10.0,
                "high": 11.0,
                "low": 9.5,
                "close": 10.5,
                "volume": 100.0,
            }
        ]
    )
    assert module.db.klines_insert(" A ", "SH.600000", " D ", bars)
    rows = module.db.klines_query(Market.A, "SH.600000", Frequency.DAY)
    assert len(rows) == 1
    assert rows[0].f == "d"
    assert module.db.klines_last_datetime("a", "SH.600000", "d") == "2026-08-04"

    before = len(rows)
    with pytest.raises(InvalidRequestError):
        module.db.klines_query("not-a-market", "SH.600000", "d")
    with pytest.raises(ValueError, match="unsupported frequency"):
        module.db.klines_insert("a", "SH.600000", "day", bars)
    assert len(module.db.klines_query("a", "SH.600000", "d")) == before
    module.db.engine.dispose()


def test_numeric_domain_parsers_reject_non_finite_surrogates() -> None:
    # Domain codes must never be inferred from numeric values, including NaN/Inf.
    for value in [math.nan, math.inf, -math.inf]:
        with pytest.raises(TypeError):
            parse_frequency(value)
