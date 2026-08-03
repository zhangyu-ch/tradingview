from __future__ import annotations

import ast
import importlib.util
import threading
import time
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "src/tradingview_zy/tools/tdx_node_selector.py"
spec = importlib.util.spec_from_file_location("tdx_node_selector", HELPER)
assert spec and spec.loader
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)
NodeSelectionError = selector.NodeSelectionError
cache_expiry_epoch = selector.cache_expiry_epoch
select_fastest_node = selector.select_fastest_node

TDX_ADAPTERS = [
    ROOT / "src/tradingview_zy/exchange/exchange_tdx.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_hk.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_futures.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_us.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_fx.py",
    ROOT / "src/tradingview_zy/exchange/exchange_tdx_ny_futures.py",
]


def _candidates(count: int) -> list[dict[str, object]]:
    return [{"ip": f"node-{index}", "port": 7709} for index in range(count)]


def test_candidates_are_probed_concurrently_and_fastest_wins() -> None:
    active = 0
    max_active = 0
    lock = threading.Lock()

    def probe(ip: str, port: int, node_type: str) -> timedelta:
        nonlocal active, max_active
        assert port == 7709 and node_type == "stock"
        with lock:
            active += 1
            max_active = max(max_active, active)
        delay = 0.03 if ip == "node-7" else 0.08
        time.sleep(delay)
        with lock:
            active -= 1
        return timedelta(seconds=delay)

    started = time.monotonic()
    best = select_fastest_node(
        _candidates(12),
        node_type="stock",
        probe=probe,
        deadline_seconds=0.5,
        max_workers=6,
    )
    elapsed = time.monotonic() - started

    assert best["ip"] == "node-7"
    assert max_active >= 4
    assert elapsed < 0.35  # Serial execution would take about 0.9 seconds.


def test_global_deadline_returns_completed_success_without_waiting_for_hung_nodes() -> None:
    def probe(ip: str, _port: int, _node_type: str) -> timedelta:
        if ip == "node-0":
            time.sleep(0.01)
            return timedelta(milliseconds=10)
        time.sleep(0.5)  # Simulate an SDK call that violates its own timeout.
        return timedelta(milliseconds=500)

    started = time.monotonic()
    best = select_fastest_node(
        _candidates(8),
        node_type="future",
        probe=probe,
        deadline_seconds=0.06,
        max_workers=8,
    )
    elapsed = time.monotonic() - started

    assert best["ip"] == "node-0"
    assert elapsed < 0.2


def test_no_healthy_node_fails_with_a_bounded_explainable_error() -> None:
    def probe(_ip: str, _port: int, _node_type: str) -> timedelta:
        time.sleep(0.3)
        return timedelta(seconds=9, microseconds=1)

    started = time.monotonic()
    with pytest.raises(NodeSelectionError, match=r"completed 0/4"):
        select_fastest_node(
            _candidates(4),
            node_type="stock",
            probe=probe,
            deadline_seconds=0.04,
            max_workers=4,
        )
    assert time.monotonic() - started < 0.2


def test_minimum_successes_is_enforced() -> None:
    def probe(ip: str, _port: int, _node_type: str) -> timedelta:
        return timedelta(milliseconds=5) if ip == "node-0" else timedelta(seconds=9)

    with pytest.raises(NodeSelectionError, match=r"found 1 healthy"):
        select_fastest_node(
            _candidates(3),
            node_type="future",
            probe=probe,
            deadline_seconds=0.2,
            minimum_successes=2,
        )


def test_selected_node_cache_expiry_is_finite_and_absolute() -> None:
    assert cache_expiry_epoch(600, wall_clock=lambda: 1_000.9) == 1_600
    with pytest.raises(ValueError, match="positive"):
        cache_expiry_epoch(0)


def test_every_tdx_adapter_persists_selected_nodes_with_a_ttl() -> None:
    for path in TDX_ADAPTERS:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        cache_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "cache_set"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in {"tdx_connect_ip", "tdxex_connect_ip"}
        ]
        assert len(cache_calls) == 1, path
        expire = next((kw.value for kw in cache_calls[0].keywords if kw.arg == "expire"), None)
        assert isinstance(expire, ast.Call), path
        assert isinstance(expire.func, ast.Attribute), path
        assert ast.unparse(expire.func) == "best_ip.cache_expiry_epoch", path
