from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tradingview_zy.history_request_tracker import (
    HistoryRequestTracker,
    history_request_key,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
CONFIG_DEMO = ROOT / "src/tradingview_zy/config.py.demo"


class ManualClock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_legacy_cadence_is_preserved_without_unbounded_dict() -> None:
    tracker = HistoryRequestTracker(
        max_entries=8,
        entry_ttl_seconds=60,
        burst_window_seconds=5,
        max_requests_per_window=6,
        clock=lambda: 1.0,
    )
    key = ("user", "127.0.0.1", "a", "SH.000001", "1D")

    assert [tracker.record(key) for _ in range(6)] == ["ok"] * 6
    assert tracker.record(key) == "no_data"
    assert tracker.record(key) == "ok"


def test_quiet_window_and_ttl_expiration_reset_and_prune_state() -> None:
    clock = ManualClock()
    tracker = HistoryRequestTracker(
        max_entries=8,
        entry_ttl_seconds=10,
        burst_window_seconds=2,
        max_requests_per_window=2,
        clock=clock,
    )
    first = ("u", "ip", "a", "one", "1")
    second = ("u", "ip", "a", "two", "1")

    assert tracker.record(first) == "ok"
    assert tracker.record(first) == "ok"
    clock.advance(2.1)
    assert tracker.record(first) == "ok"

    clock.advance(10.1)
    assert tracker.record(second) == "ok"
    assert tracker.snapshot_keys() == (second,)


def test_capacity_is_strictly_bounded_and_eviction_is_lru() -> None:
    clock = ManualClock()
    tracker = HistoryRequestTracker(
        max_entries=2,
        entry_ttl_seconds=100,
        burst_window_seconds=5,
        clock=clock,
    )
    first = ("u", "ip", "a", "one", "1")
    second = ("u", "ip", "a", "two", "1")
    third = ("u", "ip", "a", "three", "1")

    tracker.record(first)
    clock.advance(1)
    tracker.record(second)
    clock.advance(1)
    tracker.record(first)  # first is now most-recently used
    clock.advance(1)
    tracker.record(third)

    assert len(tracker) == 2
    assert tracker.snapshot_keys() == (first, third)


def test_same_key_concurrency_has_exact_atomic_suppression_count() -> None:
    tracker = HistoryRequestTracker(
        max_entries=8,
        entry_ttl_seconds=60,
        burst_window_seconds=5,
        max_requests_per_window=6,
        clock=lambda: 1.0,
    )
    key = ("user", "ip", "a", "SH.000001", "1")

    with ThreadPoolExecutor(max_workers=24) as pool:
        statuses = list(pool.map(lambda _n: tracker.record(key), range(100)))

    assert statuses.count("no_data") == 16
    assert statuses.count("ok") == 84
    assert len(tracker) == 1


def test_key_separates_identity_address_market_symbol_and_resolution() -> None:
    base = history_request_key(
        user_id="user-a",
        remote_addr="127.0.0.1",
        market="a",
        code="SH.000001",
        resolution="1",
    )
    variants = {
        history_request_key(
            user_id="user-b",
            remote_addr="127.0.0.1",
            market="a",
            code="SH.000001",
            resolution="1",
        ),
        history_request_key(
            user_id="user-a",
            remote_addr="127.0.0.2",
            market="a",
            code="SH.000001",
            resolution="1",
        ),
        history_request_key(
            user_id="user-a",
            remote_addr="127.0.0.1",
            market="hk",
            code="SH.000001",
            resolution="1",
        ),
        history_request_key(
            user_id="user-a",
            remote_addr="127.0.0.1",
            market="a",
            code="SZ.000001",
            resolution="1",
        ),
        history_request_key(
            user_id="user-a",
            remote_addr="127.0.0.1",
            market="a",
            code="SH.000001",
            resolution="5",
        ),
    }
    assert base not in variants
    assert len(variants) == 5
    assert history_request_key(
        user_id="", remote_addr=None, market="a", code="x", resolution="1"
    )[:2] == ("anonymous", "unknown")


def test_invalid_tracker_configuration_fails_before_serving_requests() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        HistoryRequestTracker(max_entries=0)
    with pytest.raises(ValueError, match="max_entries"):
        HistoryRequestTracker(max_entries=2.5)
    with pytest.raises(ValueError, match="entry_ttl_seconds"):
        HistoryRequestTracker(entry_ttl_seconds=float("inf"))
    with pytest.raises(ValueError, match="greater than or equal"):
        HistoryRequestTracker(entry_ttl_seconds=4, burst_window_seconds=5)
    with pytest.raises(ValueError, match="max_requests_per_window"):
        HistoryRequestTracker(max_requests_per_window=1_001)


def test_web_route_uses_bounded_tracker_only_for_follow_up_requests() -> None:
    source = WEB_APP.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "__history_req_counter" not in source
    assert "HistoryRequestTracker(" in source
    assert 'app.extensions["history_request_tracker"]' in source
    assert 'session.get("_user_id")' in source
    assert "request.remote_addr" in source

    history_function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "tv_history"
    )
    guarded_calls = []
    for node in ast.walk(history_function):
        if not isinstance(node, ast.If):
            continue
        test_text = ast.unparse(node.test)
        if test_text != "not first_data_request":
            continue
        guarded_calls.extend(
            call
            for statement in node.body
            for call in ast.walk(statement)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "record"
        )
    assert guarded_calls, "tracker record() must remain behind firstDataRequest=false"


def test_config_demo_documents_all_history_tracker_bounds() -> None:
    source = CONFIG_DEMO.read_text(encoding="utf-8")
    for name in (
        "WEB_HISTORY_TRACKER_MAX_ENTRIES",
        "WEB_HISTORY_TRACKER_TTL_SECONDS",
        "WEB_HISTORY_BURST_WINDOW_SECONDS",
        "WEB_HISTORY_MAX_REQUESTS_PER_WINDOW",
    ):
        assert name in source
