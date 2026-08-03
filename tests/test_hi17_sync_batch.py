from __future__ import annotations

import ast
import importlib.util
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src/tradingview_zy/sync_batch.py"
_spec = importlib.util.spec_from_file_location("sync_batch_under_test", MODULE)
assert _spec and _spec.loader
sync = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sync
_spec.loader.exec_module(sync)

WRAPPERS = [
    ROOT / "script/crontab/reboot_sync_a_klines.py",
    ROOT / "script/crontab/reboot_sync_us_klines.py",
    ROOT / "script/crontab/reboot_sync_currency_klines.py",
]
CONFIGS = {
    "a": ROOT / "script/crontab/sync_configs/a_klines.json",
    "us": ROOT / "script/crontab/sync_configs/us_klines.json",
    "currency": ROOT / "script/crontab/sync_configs/currency_klines.json",
}


class SequenceClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class Destination:
    def __init__(self) -> None:
        self.last: dict[tuple[str, str], str] = {}
        self.inserted: list[tuple[str, str, int]] = []

    def query_last_datetime(self, code: str, frequency: str):
        return self.last.get((code, frequency))

    def insert_klines(self, code: str, frequency: str, frame: pd.DataFrame) -> bool:
        self.inserted.append((code, frequency, len(frame)))
        self.last[(code, frequency)] = str(frame["date"].max())
        return True


class Source:
    def __init__(self, frames: list[pd.DataFrame | None]) -> None:
        self.frames = list(frames)
        self.calls = 0

    def klines(self, code: str, frequency: str, **kwargs):
        self.calls += 1
        return self.frames.pop(0)


def _frame(*dates: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(list(dates), utc=True),
            "open": [1.0] * len(dates),
            "high": [1.0] * len(dates),
            "low": [1.0] * len(dates),
            "close": [1.0] * len(dates),
            "volume": [1.0] * len(dates),
        }
    )


def test_three_scripts_are_import_safe_thin_main_wrappers() -> None:
    for path in WRAPPERS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        assert len(source.splitlines()) < 30
        assert "while True" not in source
        assert any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            for node in tree.body
        )
        forbidden_top_level = []
        for node in tree.body:
            if isinstance(node, (ast.For, ast.While, ast.With, ast.Try)):
                forbidden_top_level.append(node)
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                forbidden_top_level.append(node)
        assert not forbidden_top_level, path
        assert "ExchangeBaostock" not in source
        assert "ExchangeIB" not in source
        assert "ExchangeBinance" not in source


def test_importing_wrappers_does_not_import_or_construct_providers() -> None:
    provider_modules = {
        "tradingview_zy.exchange.exchange_baostock",
        "tradingview_zy.exchange.exchange_ib",
        "tradingview_zy.exchange.exchange_binance",
        "tradingview_zy.exchange.exchange_db",
    }
    before = provider_modules.intersection(sys.modules)
    for index, path in enumerate(WRAPPERS):
        spec = importlib.util.spec_from_file_location(f"sync_wrapper_{index}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        assert callable(module.main)
    assert provider_modules.intersection(sys.modules) == before


def test_universes_and_frequency_contracts_are_externalized() -> None:
    a = json.loads(CONFIGS["a"].read_text(encoding="utf-8"))
    us = json.loads(CONFIGS["us"].read_text(encoding="utf-8"))
    currency = json.loads(CONFIGS["currency"].read_text(encoding="utf-8"))

    assert len(a["universe"]["codes"]) == 1210
    assert len(us["universe"]["codes"]) == 495
    assert currency["universe"] == {"type": "provider_all_stocks"}
    assert set(a["frequencies"]) == {"m", "w", "d", "30m", "5m"}
    assert us["frequencies"]["d"]["args"]["timeout"] == 45
    assert all(
        spec.get("max_pages", a["max_pages"]) <= 100
        for spec in a["frequencies"].values()
    )


def test_provider_initialization_failure_is_audited_without_starting_items(
    tmp_path: Path,
) -> None:
    config = {
        "schema_version": 1,
        "market": "a",
        "mode": "incremental",
        "source": {"module": "missing_sync_provider", "class": "Provider"},
        "destination": {"module": "missing_destination", "class": "Destination"},
        "universe": {"type": "list", "codes": ["SH.600000"]},
        "frequencies": {"d": {"start_date": "2000-01-01"}},
    }
    config_path = tmp_path / "config.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = sync.run_configured_sync(
        config_path=config_path,
        checkpoint_path=checkpoint_path,
        batch_deadline_seconds=1,
        per_call_timeout=0.2,
    )
    state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert result.status == "initialization_failed"
    assert result.exit_code == 1
    assert state["status"] == "initialization_failed"
    assert state["items"] == {}
    assert "ModuleNotFoundError" in state["batch_error"]


def test_checkpoint_resume_retries_only_failed_items(tmp_path: Path) -> None:
    checkpoint = tmp_path / "sync.json"
    items = [("A", "d"), ("B", "d"), ("C", "d")]
    first_calls: list[str] = []

    def first(code, frequency, deadline, caller):
        first_calls.append(code)
        if code == "B":
            raise RuntimeError("temporary source failure")
        return sync.SyncOutcome(rows_written=1, pages=1, progress_token=code)

    result = sync.run_sync_batch(
        market="a",
        items=items,
        config_digest="digest",
        checkpoint_path=checkpoint,
        synchronizer=first,
        deadline=sync.BatchDeadline(60),
        caller=sync.DeadlineCaller(),
    )
    assert result.status == "completed_with_errors"
    assert result.exit_code == 2
    assert first_calls == ["A", "B", "C"]

    second_calls: list[str] = []

    def second(code, frequency, deadline, caller):
        second_calls.append(code)
        return sync.SyncOutcome(rows_written=2, pages=1, progress_token=code + "2")

    resumed = sync.run_sync_batch(
        market="a",
        items=items,
        config_digest="digest",
        checkpoint_path=checkpoint,
        synchronizer=second,
        deadline=sync.BatchDeadline(60),
        caller=sync.DeadlineCaller(),
        resume=True,
    )
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert resumed.status == "completed"
    assert resumed.exit_code == 0
    assert second_calls == ["B"]
    assert state["items"]["A::d"]["attempts"] == 1
    assert state["items"]["B::d"]["attempts"] == 2
    assert state["items"]["C::d"]["attempts"] == 1
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob(".*.tmp"))


def test_checkpoint_rejects_different_config_digest(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    synchronizer = lambda *args: sync.SyncOutcome()
    sync.run_sync_batch(
        market="a",
        items=[("A", "d")],
        config_digest="first",
        checkpoint_path=path,
        synchronizer=synchronizer,
        deadline=sync.BatchDeadline(60),
        caller=sync.DeadlineCaller(),
    )
    with pytest.raises(sync.SyncCheckpointError, match="digest"):
        sync.run_sync_batch(
            market="a",
            items=[("A", "d")],
            config_digest="second",
            checkpoint_path=path,
            synchronizer=synchronizer,
            deadline=sync.BatchDeadline(60),
            caller=sync.DeadlineCaller(),
            resume=True,
        )


def test_external_call_timeout_is_finite_and_capacity_is_bounded() -> None:
    caller = sync.DeadlineCaller(max_concurrent=1)
    release = threading.Event()

    def block() -> None:
        release.wait(2)

    started = time.monotonic()
    with pytest.raises(sync.SyncCallTimeoutError):
        caller.call(block, timeout_seconds=0.03)
    assert time.monotonic() - started < 0.5
    with pytest.raises(sync.SyncCallBusyError):
        caller.call(lambda: None, timeout_seconds=0.03)
    release.set()
    for _ in range(100):
        try:
            assert caller.call(lambda: "ready", timeout_seconds=0.1) == "ready"
            break
        except sync.SyncCallBusyError:
            time.sleep(0.005)
    else:
        raise AssertionError("timed-out worker never released its bounded slot")


def test_incremental_sync_upserts_pages_and_detects_terminal_page() -> None:
    destination = Destination()
    source = Source(
        [
            _frame("2026-01-01", "2026-01-02", "2026-01-03"),
            _frame("2026-01-04"),
        ]
    )
    outcome = sync.sync_incremental_series(
        destination=destination,
        source=source,
        code="A",
        frequency="d",
        start_date="2000-01-01",
        query_args={},
        stop_rows=1,
        max_pages=3,
        deadline=sync.BatchDeadline(60),
        caller=sync.DeadlineCaller(),
        per_call_timeout=1,
    )
    assert outcome.rows_written == 4
    assert outcome.pages == 2
    assert destination.inserted == [("A", "d", 3), ("A", "d", 1)]


def test_incremental_sync_fails_instead_of_looping_on_same_page() -> None:
    class NonAdvancingDestination(Destination):
        def insert_klines(self, code, frequency, frame):
            self.inserted.append((code, frequency, len(frame)))
            return True

    repeated = _frame("2026-01-01", "2026-01-02")
    source = Source([repeated, repeated.copy()])
    with pytest.raises(sync.SyncNoProgressError, match="did not advance"):
        sync.sync_incremental_series(
            destination=NonAdvancingDestination(),
            source=source,
            code="A",
            frequency="d",
            start_date="2000-01-01",
            query_args={},
            stop_rows=1,
            max_pages=5,
            deadline=sync.BatchDeadline(60),
            caller=sync.DeadlineCaller(),
            per_call_timeout=1,
        )
    assert source.calls == 2


def test_batch_deadline_leaves_unstarted_items_pending(tmp_path: Path) -> None:
    clock = SequenceClock()
    calls: list[str] = []

    def synchronizer(code, frequency, deadline, caller):
        calls.append(code)
        clock.value += 2
        return sync.SyncOutcome()

    result = sync.run_sync_batch(
        market="a",
        items=[("A", "d"), ("B", "d")],
        config_digest="deadline",
        checkpoint_path=tmp_path / "deadline.json",
        synchronizer=synchronizer,
        deadline=sync.BatchDeadline(1, clock=clock),
        caller=sync.DeadlineCaller(),
    )
    state = json.loads((tmp_path / "deadline.json").read_text(encoding="utf-8"))
    assert result.status == "deadline_exceeded"
    assert result.exit_code == 3
    assert calls == ["A"]
    assert state["items"]["A::d"]["status"] == "completed"
    assert state["items"]["B::d"]["status"] == "pending"
