from __future__ import annotations

import ast
import importlib.util
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "src/tradingview_zy/exchange/worker_lifecycle.py"
spec = importlib.util.spec_from_file_location("worker_lifecycle", HELPER)
assert spec and spec.loader
worker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_module)
ManagedWorker = worker_module.ManagedWorker


def test_managed_worker_is_daemon_idempotent_and_joins() -> None:
    worker = ManagedWorker("test-worker")
    entered = threading.Event()

    def target() -> None:
        entered.set()
        while not worker.stop_event.wait(0.01):
            pass

    assert worker.running is False
    assert worker.start(target) is True
    assert entered.wait(1.0)
    assert worker.running is True
    assert worker.thread is not None and worker.thread.daemon is True
    assert worker.start(target) is False
    assert worker.stop(timeout=1.0) is True
    assert worker.running is False


def test_exchange_tq_constructor_has_no_thread_start_and_uses_sync_primitives() -> None:
    path = ROOT / "src/tradingview_zy/exchange/exchange_tq.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeTq")
    assert not cls.decorator_list  # parameterized singleton removed
    init = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "start"
        for node in ast.walk(init)
    )
    assert "queue.Queue[str]" in text
    assert "threading.RLock()" in text
    assert "ManagedWorker(" in text
    assert "daemon=True" not in text  # centralized in ManagedWorker
    assert "def close(self, timeout" in text
    assert "self._worker.stop(timeout=timeout)" in text
    assert "self.command_tasks.put(command)" in text
    assert "self.command_tasks.append" not in text


def test_close_without_start_releases_cleanly() -> None:
    worker = ManagedWorker("never-started")
    assert worker.stop(timeout=0.1) is False
    assert worker.running is False
