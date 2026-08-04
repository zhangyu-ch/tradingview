from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import tzlocal  # noqa: F401
except ModuleNotFoundError:
    import types

    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: "UTC"
    sys.modules["tzlocal"] = tzlocal

from tradingview_zy.exchange.exchange import (  # noqa: E402
    Exchange,
    LiveTradingDisabledError,
)


class MarketDataOnlyExchange(Exchange):
    def default_code(self): return "TEST"
    def support_frequencys(self): return {"d": "Day"}
    def all_stocks(self): return []
    def now_trading(self, code=None, at=None): return False
    def klines(self, code, frequency, start_date=None, end_date=None, args=None): return None
    def ticks(self, codes): return {}
    def stock_info(self, code): return None
    def stock_owner_plate(self, code): return []
    def plate_stocks(self, code): return []
    def balance(self): return None
    def positions(self, code=""): return []


def test_exchange_order_fails_closed_with_actionable_error() -> None:
    exchange = MarketDataOnlyExchange()
    with pytest.raises(LiveTradingDisabledError, match="Order/Fill state machine"):
        exchange.order("TEST", "buy", 1)


def test_unverified_live_trader_modules_are_removed() -> None:
    trader_root = ROOT / "src/tradingview_zy/trader"
    removed = {
        "trader_a_stock.py",
        "trader_currency.py",
        "trader_futures.py",
        "trader_hk_stock.py",
        "trader_qmt_stock.py",
        "trader_ctp.py",
    }
    assert not any((trader_root / name).exists() for name in removed)
    assert (trader_root / "online_market_datas.py").exists()


def test_all_exchange_order_and_cancel_methods_use_the_fail_closed_boundary() -> None:
    offenders: list[str] = []
    for path in (ROOT / "src/tradingview_zy/exchange").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name not in {"order", "cancel_order", "cancel_all_order", "cancel_all_orders"}:
                continue
            if path.name == "exchange.py" and node.name == "order":
                calls = [
                    call for call in ast.walk(node)
                    if isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "_raise_live_trading_disabled"
                ]
                if not calls:
                    offenders.append(f"{path.name}:{node.lineno}:base")
                continue
            segment = ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
            if "super().order(" not in segment and "_raise_live_trading_disabled(" not in segment:
                offenders.append(f"{path.name}:{node.lineno}:{node.name}")
    assert offenders == []


def test_runtime_contains_no_broker_order_submission_or_ib_order_queue() -> None:
    forbidden = (
        "create_order(",
        "create_market_buy_order(",
        "create_market_sell_order(",
        "place_order(",
        "placeOrder(",
        "insert_order(",
        "unlock_trade(",
        "CmdEnum.ORDERS",
    )
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert offenders == []
