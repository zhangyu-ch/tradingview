from __future__ import annotations

import ast
from pathlib import Path

import importlib.util

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "src/tradingview_zy/exchange/tdx_reliability.py"
spec = importlib.util.spec_from_file_location("tdx_reliability", HELPER)
assert spec and spec.loader
_reliability = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_reliability)
ProviderUnavailableError = _reliability.ProviderUnavailableError
call_with_bounded_retry = _reliability.call_with_bounded_retry
TARGETS = [
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_hk.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_futures.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_ny_futures.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_fx.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_us.py",
]


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_retry_is_bounded_by_attempts_and_deadline() -> None:
    fake = FakeTime()
    calls: list[float] = []

    def fail(remaining: float):
        calls.append(remaining)
        fake.now += 0.4
        raise ConnectionError("down")

    with pytest.raises(ProviderUnavailableError) as exc_info:
        call_with_bounded_retry(
            fail,
            retry_on=(ConnectionError,),
            max_attempts=3,
            deadline_seconds=2.0,
            base_delay_seconds=0.2,
            max_delay_seconds=0.2,
            clock=fake.clock,
            sleeper=fake.sleep,
        )

    assert len(calls) == 3
    assert fake.now <= 2.0
    assert calls == sorted(calls, reverse=True)
    assert "unavailable after 3 attempts" in str(exc_info.value)


def test_retry_can_recover_without_unbounded_loop() -> None:
    fake = FakeTime()
    calls = 0
    recoveries = 0

    def operation(remaining: float) -> str:
        nonlocal calls
        calls += 1
        assert remaining > 0
        if calls == 1:
            raise ConnectionError("first node failed")
        return "ready"

    def recover() -> None:
        nonlocal recoveries
        recoveries += 1

    result = call_with_bounded_retry(
        operation,
        recover=recover,
        retry_on=(ConnectionError,),
        clock=fake.clock,
        sleeper=fake.sleep,
    )
    assert result == "ready"
    assert calls == 2
    assert recoveries == 1


def test_exhq_constructors_delegate_to_the_shared_bounded_lifecycle() -> None:
    for path in TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef))
        assert "TdxExHqLifecycleMixin" in {
            ast.unparse(base) for base in class_node.bases
        }, path
        init = next(
            node
            for node in class_node.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        assert not any(
            isinstance(node, ast.While)
            and isinstance(node.test, ast.Constant)
            and node.test.value is True
            for node in ast.walk(init)
        ), path
        assert any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_initialize_tdx_exhq"
            for node in ast.walk(init)
        ), path


def test_shared_lifecycle_uses_the_existing_bounded_retry_helper() -> None:
    tree = ast.parse(HELPER.read_text(encoding="utf-8"), filename=str(HELPER))
    lifecycle = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "TdxExHqLifecycleMixin"
    )
    load_markets = next(
        node
        for node in lifecycle.body
        if isinstance(node, ast.FunctionDef) and node.name == "_load_tdx_markets"
    )
    calls = {
        ast.unparse(node.func)
        for node in ast.walk(load_markets)
        if isinstance(node, ast.Call)
    }
    assert "call_with_bounded_retry" in calls
