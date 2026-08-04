from __future__ import annotations

import ast
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import tradingview_zy.futu_context as futu_context
from tradingview_zy.futu_context import (
    FutuContextClosedError,
    FutuContextManager,
    FutuContextUnavailableError,
)


class FakeContext:
    def __init__(self, name: str) -> None:
        self.name = name
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def _manager(
    quote_factory,
    trade_factory=None,
    *,
    enabled: bool = True,
    max_attempts: int = 2,
) -> FutuContextManager:
    if trade_factory is None:
        trade_factory = lambda: FakeContext("trade")
    return FutuContextManager(
        enabled=enabled,
        quote_factory=quote_factory,
        trade_factory=trade_factory,
        max_attempts=max_attempts,
        register_atexit=False,
    )


def test_constructor_is_lazy_and_empty_host_fails_closed() -> None:
    calls = {"quote": 0, "trade": 0}

    def quote_factory():
        calls["quote"] += 1
        return FakeContext("quote")

    def trade_factory():
        calls["trade"] += 1
        return FakeContext("trade")

    manager = _manager(quote_factory, trade_factory, enabled=False)

    assert calls == {"quote": 0, "trade": 0}
    with pytest.raises(FutuContextUnavailableError, match="not configured"):
        manager.run_quote(lambda context: context.name)
    assert calls == {"quote": 0, "trade": 0}
    assert manager.health()["state"] == "degraded"


def test_quote_operations_are_serialized_and_share_one_context() -> None:
    factory_calls = 0
    factory_lock = threading.Lock()
    activity_lock = threading.Lock()
    active = 0
    max_active = 0

    def quote_factory():
        nonlocal factory_calls
        with factory_lock:
            factory_calls += 1
        return FakeContext("quote")

    manager = _manager(quote_factory)

    def operation(context: FakeContext) -> str:
        nonlocal active, max_active
        with activity_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.005)
        with activity_lock:
            active -= 1
        return context.name

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(manager.run_quote, operation) for _ in range(20)]
        assert [future.result(timeout=2) for future in futures] == ["quote"] * 20

    assert factory_calls == 1
    assert max_active == 1
    assert manager.health()["quote"]["generation"] == 1


def test_quote_and_trade_have_independent_operation_locks() -> None:
    quote_entered = threading.Event()
    trade_entered = threading.Event()
    release = threading.Event()
    manager = _manager(lambda: FakeContext("quote"), lambda: FakeContext("trade"))

    def quote_operation(context: FakeContext) -> str:
        quote_entered.set()
        assert trade_entered.wait(1)
        assert release.wait(1)
        return context.name

    def trade_operation(context: FakeContext) -> str:
        trade_entered.set()
        assert quote_entered.wait(1)
        assert release.wait(1)
        return context.name

    with ThreadPoolExecutor(max_workers=2) as executor:
        quote_future = executor.submit(manager.run_quote, quote_operation)
        trade_future = executor.submit(manager.run_trade, trade_operation)
        assert quote_entered.wait(1)
        assert trade_entered.wait(1)
        release.set()
        assert quote_future.result(timeout=1) == "quote"
        assert trade_future.result(timeout=1) == "trade"


def test_factory_failure_is_bounded_and_never_published() -> None:
    attempts = 0

    def failing_factory():
        nonlocal attempts
        attempts += 1
        raise RuntimeError("factory-secret-must-not-be-exposed")

    manager = _manager(failing_factory, max_attempts=2)

    with pytest.raises(FutuContextUnavailableError, match="after 2 attempts") as error:
        manager.run_quote(lambda context: context)

    assert attempts == 2
    health = manager.health()
    assert health["quote"]["generation"] == 0
    assert health["quote"]["state"] == "degraded"
    assert health["quote"]["last_error_type"] == "RuntimeError"
    assert "factory-secret" not in str(error.value)


def test_quote_failure_rebuilds_only_quote_context() -> None:
    quotes = [FakeContext("quote-1"), FakeContext("quote-2")]
    trade = FakeContext("trade-1")
    quote_creations = 0
    trade_creations = 0

    def quote_factory():
        nonlocal quote_creations
        context = quotes[quote_creations]
        quote_creations += 1
        return context

    def trade_factory():
        nonlocal trade_creations
        trade_creations += 1
        return trade

    manager = _manager(quote_factory, trade_factory)
    assert manager.run_trade(lambda context: context.name) == "trade-1"

    def flaky_quote(context: FakeContext) -> str:
        if context.name == "quote-1":
            raise RuntimeError("broken quote")
        return context.name

    assert manager.run_quote(flaky_quote) == "quote-2"
    health = manager.health()

    assert quote_creations == 2
    assert trade_creations == 1
    assert quotes[0].closed == 1
    assert quotes[1].closed == 0
    assert trade.closed == 0
    assert health["quote"]["generation"] == 2
    assert health["trade"]["generation"] == 1


def test_close_is_idempotent_and_rejects_future_operations() -> None:
    quote = FakeContext("quote")
    trade = FakeContext("trade")
    manager = _manager(lambda: quote, lambda: trade)

    manager.run_quote(lambda context: context.name)
    manager.run_trade(lambda context: context.name)
    manager.close()
    manager.close()

    assert quote.closed == 1
    assert trade.closed == 1
    assert manager.health()["state"] == "closed"
    with pytest.raises(FutuContextClosedError, match="closed"):
        manager.run_quote(lambda context: context.name)


def test_pid_change_discards_inherited_contexts_and_creates_new_generations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quote_contexts: list[FakeContext] = []
    trade_contexts: list[FakeContext] = []
    fake_pid = 100
    monkeypatch.setattr(futu_context.os, "getpid", lambda: fake_pid)

    def quote_factory():
        context = FakeContext(f"quote-{len(quote_contexts) + 1}")
        quote_contexts.append(context)
        return context

    def trade_factory():
        context = FakeContext(f"trade-{len(trade_contexts) + 1}")
        trade_contexts.append(context)
        return context

    manager = _manager(quote_factory, trade_factory)
    assert manager.run_quote(lambda context: context.name) == "quote-1"
    assert manager.run_trade(lambda context: context.name) == "trade-1"

    fake_pid = 101
    assert manager.run_quote(lambda context: context.name) == "quote-2"
    assert quote_contexts[0].closed == 1
    assert trade_contexts[0].closed == 1
    assert manager.health()["trade"]["state"] == "degraded"

    assert manager.run_trade(lambda context: context.name) == "trade-2"
    health = manager.health()
    assert health["pid"] == 101
    assert health["quote"]["generation"] == 2
    assert health["trade"]["generation"] == 2


def test_health_contains_no_host_account_or_error_message_secrets() -> None:
    sentinel = "open-d-host-and-account-secret"
    manager = _manager(lambda: FakeContext(sentinel), max_attempts=1)

    with pytest.raises(FutuContextUnavailableError):
        manager.run_quote(lambda context: (_ for _ in ()).throw(ValueError(sentinel)))

    serialized = json.dumps(manager.health(), sort_keys=True)
    assert sentinel not in serialized
    assert "host" not in serialized.lower()
    assert "account" not in serialized.lower()
    assert manager.health()["quote"]["last_error_type"] == "ValueError"


def test_exchange_adapter_uses_managed_boundaries_without_legacy_globals() -> None:
    path = SRC / "tradingview_zy/exchange/exchange_futu.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert all(alias.name != "*" for alias in node.names)

    assert "FutuContextManager(" in source
    assert ".run_quote(" in source
    assert ".run_trade(" in source
    assert "def close(" in source
    assert "def health(" in source
    assert "g_ctx" not in source
    assert "g_ttx" not in source
    assert "unsubscribe_all" not in source
    assert "import random" not in source
    assert "tenacity" not in source
    assert "@retry" not in source
    assert "CTX(" not in source
    assert "TTX(" not in source
