from __future__ import annotations

import ast
import datetime as dt
import importlib.util
import os
import pathlib
import stat
import sys
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
WEB = ROOT / "web" / "tradingview_zy_chart"
CL_APP = WEB / "cl_app"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(CL_APP) not in sys.path:
    sys.path.insert(0, str(CL_APP))

from tradingview_zy.scheduler_status import SchedulerStatusStore
from scheduler_runtime import (
    RECONCILE_JOB_ID,
    SchedulerAlreadyRunningError,
    SchedulerLeaderLock,
    build_scheduler,
    run_scheduler,
)


class MemoryCache:
    def __init__(self, value=None, error: Exception | None = None):
        self.value = value
        self.error = error
        self.writes: list[tuple[str, object]] = []

    def cache_pkl_from_file(self, filename: str):
        if self.error is not None:
            raise self.error
        return self.value

    def cache_pkl_to_file(self, filename: str, value: object) -> bool:
        self.writes.append((filename, value))
        self.value = value
        return True


class FakeJob:
    def __init__(self, job_id: str, name: str, next_run_time=None, **options):
        self.id = job_id
        self.name = name
        self.next_run_time = next_run_time
        self.options = options


class FakeScheduler:
    instances: list["FakeScheduler"] = []

    def __init__(self, *, timezone):
        self.timezone = timezone
        self.jobs: dict[str, FakeJob] = {}
        self.listeners: list[tuple[object, int]] = []
        self.start_count = 0
        self.on_start = None
        type(self).instances.append(self)

    def add_listener(self, callback, mask: int) -> None:
        self.listeners.append((callback, mask))

    def add_job(self, func, trigger=None, *, id: str, name: str, **options):
        job = FakeJob(
            id,
            name,
            next_run_time=options.get("next_run_time"),
            func=func,
            trigger=trigger,
            **options,
        )
        self.jobs[id] = job
        return job

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    def remove_job(self, job_id: str) -> None:
        self.jobs.pop(job_id, None)

    def start(self) -> None:
        self.start_count += 1
        if self.on_start is not None:
            self.on_start()


class FakeAlertTasks:
    instances: list["FakeAlertTasks"] = []

    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.run_count = 0
        type(self).instances.append(self)

    def run(self):
        self.run_count += 1
        return True


def _build_fake_scheduler(**overrides):
    FakeScheduler.instances.clear()
    FakeAlertTasks.instances.clear()
    kwargs = {
        "scheduler_factory": FakeScheduler,
        "alert_tasks_factory": FakeAlertTasks,
        "event_mask": 0xFFFF,
        "event_states": {1: "已完成", 2: "执行异常"},
        "status_store": SchedulerStatusStore(cache=MemoryCache()),
        "reconcile_seconds": 30,
    }
    kwargs.update(overrides)
    scheduler = build_scheduler(**kwargs)
    return scheduler, kwargs


def test_flask_factory_has_no_scheduler_lifecycle_side_effects() -> None:
    path = WEB / "cl_app" / "__init__.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    create_app = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )

    assert "apscheduler" not in source.lower()
    assert "TornadoScheduler" not in source
    assert "scheduler.start()" not in source
    assert "task_cls(None)" in source
    assert "SchedulerStatusStore()" in source
    assert "scheduler_status_store.read()" in source
    assert 'app.extensions["scheduler_mode"] = "external-process"' in source
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "start"
        for node in ast.walk(create_app)
    )


def test_task_modules_do_not_import_apscheduler_and_web_alert_reconcile_is_a_noop() -> None:
    alert_source = (WEB / "cl_app" / "alert_tasks.py").read_text(encoding="utf-8")
    xuangu_source = (WEB / "cl_app" / "xuangu_tasks.py").read_text(encoding="utf-8")
    other_source = (WEB / "cl_app" / "other_tasks.py").read_text(encoding="utf-8")

    assert "apscheduler" not in alert_source.lower()
    assert "apscheduler" not in xuangu_source.lower()
    assert "apscheduler" not in other_source.lower()
    assert "def __init__(self, scheduler=None)" in alert_source
    assert "if self.scheduler is None:" in alert_source
    assert "return True" in alert_source[alert_source.index("def run(self):") :]


def test_scheduler_status_store_whitelists_sorts_and_round_trips() -> None:
    cache = MemoryCache()
    store = SchedulerStatusStore(cache=cache, filename="scheduler-status")
    raw = [
        {
            "id": "job-b",
            "name": "B",
            "state": "运行中",
            "update_dt": "2026-08-03 12:00:00",
            "next_run_dt": None,
            "secret": "must-not-persist",
        },
        {
            "id": "job-a",
            "name": 123,
            "state": "已完成",
            "update_dt": "2026-08-03 11:00:00",
            "next_run_dt": "--",
        },
    ]

    assert store.write(raw) is True
    assert cache.writes == [
        (
            "scheduler-status",
            [
                {
                    "id": "job-a",
                    "name": "123",
                    "update_dt": "2026-08-03 11:00:00",
                    "next_run_dt": "--",
                    "state": "已完成",
                },
                {
                    "id": "job-b",
                    "name": "B",
                    "update_dt": "2026-08-03 12:00:00",
                    "next_run_dt": "--",
                    "state": "运行中",
                },
            ],
        )
    ]
    assert store.read() == cache.value


def test_scheduler_status_store_fails_closed_on_missing_or_corrupt_state() -> None:
    assert SchedulerStatusStore(cache=MemoryCache(value=None)).read() == []
    assert SchedulerStatusStore(cache=MemoryCache(value={"not": "a list"})).read() == []
    assert SchedulerStatusStore(cache=MemoryCache(error=RuntimeError("corrupt"))).read() == []


def test_leader_lock_is_exclusive_releasable_and_private(tmp_path: pathlib.Path) -> None:
    lock_path = tmp_path / "scheduler" / "leader.lock"
    first = SchedulerLeaderLock(lock_path)
    first.acquire()
    try:
        assert lock_path.read_text(encoding="ascii").strip() == str(os.getpid())
        with pytest.raises(SchedulerAlreadyRunningError):
            SchedulerLeaderLock(lock_path).acquire()
        if os.name == "posix":
            assert stat.S_IMODE(lock_path.parent.stat().st_mode) == 0o700
            assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600
    finally:
        first.release()

    second = SchedulerLeaderLock(lock_path)
    second.acquire()
    second.release()


def test_build_scheduler_reconciles_once_and_registers_one_bounded_job_without_starting() -> None:
    scheduler, _ = _build_fake_scheduler(reconcile_seconds=1)

    assert scheduler.start_count == 0
    assert isinstance(scheduler.timezone, ZoneInfo)
    assert scheduler.timezone.key == "Asia/Shanghai"
    assert len(scheduler.listeners) == 1
    assert len(FakeAlertTasks.instances) == 1
    assert FakeAlertTasks.instances[0].run_count == 1
    assert list(scheduler.jobs) == [RECONCILE_JOB_ID]
    reconcile = scheduler.jobs[RECONCILE_JOB_ID]
    assert reconcile.options["seconds"] == 5
    assert reconcile.options["replace_existing"] is True
    assert reconcile.options["max_instances"] == 1
    assert reconcile.options["coalesce"] is True


def test_scheduler_listener_persists_a_stable_status_snapshot() -> None:
    cache = MemoryCache()
    store = SchedulerStatusStore(cache=cache)
    scheduler, _ = _build_fake_scheduler(status_store=store)
    next_run = dt.datetime(2026, 8, 3, 12, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
    scheduler.jobs["job-b"] = FakeJob("job-b", "Job B", next_run_time=next_run)
    scheduler.jobs["job-a"] = FakeJob("job-a", "Job A", next_run_time=None)
    listener, mask = scheduler.listeners[0]

    assert mask == 0xFFFF
    listener(SimpleNamespace(code=1, job_id="job-b"))
    listener(SimpleNamespace(code=2, job_id="job-a"))

    snapshot = store.read()
    assert [item["id"] for item in snapshot] == ["job-a", "job-b"]
    assert snapshot[0]["state"] == "执行异常"
    assert snapshot[0]["next_run_dt"] == "--"
    assert snapshot[1]["name"] == "Job B"
    assert snapshot[1]["next_run_dt"] == "2026-08-03 12:30:00"
    assert snapshot[1]["state"] == "已完成"


def test_run_scheduler_holds_the_leader_lock_and_starts_exactly_once(tmp_path: pathlib.Path) -> None:
    lock_path = tmp_path / "scheduler" / "leader.lock"
    scheduler, kwargs = _build_fake_scheduler()

    # run_scheduler builds its own instance, so reset the factory list and verify the
    # process lock is still held from inside start().
    FakeScheduler.instances.clear()

    def on_start() -> None:
        with pytest.raises(SchedulerAlreadyRunningError):
            SchedulerLeaderLock(lock_path).acquire()

    class LockAwareScheduler(FakeScheduler):
        def __init__(self, *, timezone):
            super().__init__(timezone=timezone)
            self.on_start = on_start

    kwargs["scheduler_factory"] = LockAwareScheduler
    result = run_scheduler(lock_path=lock_path, **kwargs)

    assert result.start_count == 1
    # The blocking scheduler has returned in this fake; the lock must now be released.
    probe = SchedulerLeaderLock(lock_path)
    probe.acquire()
    probe.release()


def test_scheduler_cli_returns_two_when_another_runner_owns_the_lock(monkeypatch) -> None:
    path = WEB / "scheduler.py"
    spec = importlib.util.spec_from_file_location("test_scheduler_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    def duplicate_runner():
        raise SchedulerAlreadyRunningError("already running")

    monkeypatch.setattr(module, "run_scheduler", duplicate_runner)
    assert module.main() == 2
