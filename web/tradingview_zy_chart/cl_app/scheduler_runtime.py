"""Single-owner APScheduler runtime kept outside the Flask application factory."""

from __future__ import annotations

import contextlib
import datetime as dt
import os
import pathlib
from collections.abc import Callable, Mapping
from typing import Any
from zoneinfo import ZoneInfo

from tradingview_zy.scheduler_status import SchedulerStatusStore

SCHEDULER_TIMEZONE = ZoneInfo("Asia/Shanghai")
RECONCILE_JOB_ID = "system:alert-reconcile"
DEFAULT_RECONCILE_SECONDS = 30
MIN_RECONCILE_SECONDS = 5
MAX_RECONCILE_SECONDS = 3600


class SchedulerAlreadyRunningError(RuntimeError):
    """Raised when another scheduler process owns the data-directory lease."""


class SchedulerLeaderLock:
    """Cross-process, non-blocking local-file lock for the scheduler owner."""

    def __init__(self, path: os.PathLike[str] | str) -> None:
        self.path = pathlib.Path(path)
        self._fd: int | None = None

    def _lock_fd(self, fd: int) -> None:
        if os.name == "nt":  # pragma: no cover - exercised on Windows deployments
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            # msvcrt locks bytes, so guarantee that byte zero exists first.
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"0")
                os.fsync(fd)
                os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise SchedulerAlreadyRunningError(
                    f"scheduler leader lock is already held: {self.path}"
                ) from exc
            return

        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise SchedulerAlreadyRunningError(
                f"scheduler leader lock is already held: {self.path}"
            ) from exc

    @staticmethod
    def _unlock_fd(fd: int) -> None:
        if os.name == "nt":  # pragma: no cover - exercised on Windows deployments
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            with contextlib.suppress(OSError):
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)

    def acquire(self) -> "SchedulerLeaderLock":
        if self._fd is not None:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with contextlib.suppress(OSError):
            os.chmod(self.path.parent, 0o700)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            with contextlib.suppress(OSError):
                os.chmod(self.path, 0o600)
            self._lock_fd(fd)
            payload = f"{os.getpid()}\n".encode("ascii")
            os.ftruncate(fd, 0)
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, payload)
            os.fsync(fd)
        except Exception:
            os.close(fd)
            raise
        self._fd = fd
        return self

    def release(self) -> None:
        fd = self._fd
        if fd is None:
            return
        self._fd = None
        self._unlock_fd(fd)
        os.close(fd)

    def __enter__(self) -> "SchedulerLeaderLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.release()
        return False


def bounded_reconcile_seconds(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("scheduler reconcile seconds must be an integer")
    try:
        seconds = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("scheduler reconcile seconds must be an integer") from exc
    return max(MIN_RECONCILE_SECONDS, min(MAX_RECONCILE_SECONDS, seconds))


def _format_datetime(value: object) -> str:
    if value is None:
        return "--"
    if not isinstance(value, dt.datetime):
        return str(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=SCHEDULER_TIMEZONE)
    return value.astimezone(SCHEDULER_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")


def _load_apscheduler_components():
    # Kept lazy: importing the Flask application and its task modules must not
    # construct or even require APScheduler.
    from apscheduler.events import (
        EVENT_ALL,
        EVENT_EXECUTOR_ADDED,
        EVENT_EXECUTOR_REMOVED,
        EVENT_JOB_ADDED,
        EVENT_JOB_ERROR,
        EVENT_JOB_EXECUTED,
        EVENT_JOB_MAX_INSTANCES,
        EVENT_JOB_MISSED,
        EVENT_JOB_MODIFIED,
        EVENT_JOB_REMOVED,
        EVENT_JOB_SUBMITTED,
        EVENT_JOBSTORE_ADDED,
        EVENT_JOBSTORE_REMOVED,
    )
    from apscheduler.schedulers.blocking import BlockingScheduler

    states = {
        EVENT_EXECUTOR_ADDED: "已添加",
        EVENT_EXECUTOR_REMOVED: "删除调度",
        EVENT_JOBSTORE_ADDED: "已添加",
        EVENT_JOBSTORE_REMOVED: "删除存储",
        EVENT_JOB_ADDED: "已添加",
        EVENT_JOB_REMOVED: "删除作业",
        EVENT_JOB_MODIFIED: "修改作业",
        EVENT_JOB_SUBMITTED: "运行中",
        EVENT_JOB_MAX_INSTANCES: "等待运行",
        EVENT_JOB_EXECUTED: "已完成",
        EVENT_JOB_ERROR: "执行异常",
        EVENT_JOB_MISSED: "未执行",
    }
    return BlockingScheduler, EVENT_ALL, states


def _default_alert_tasks_factory(scheduler):
    from alert_tasks import AlertTasks

    return AlertTasks(scheduler)


def _configured_reconcile_seconds() -> int:
    from tradingview_zy import config

    return bounded_reconcile_seconds(
        getattr(config, "SCHEDULER_RECONCILE_SECONDS", DEFAULT_RECONCILE_SECONDS)
    )


def _default_leader_lock_path() -> pathlib.Path:
    from tradingview_zy.config import get_data_path

    return pathlib.Path(get_data_path()) / "scheduler" / "leader.lock"


def build_scheduler(
    *,
    scheduler_factory: Callable[..., Any] | None = None,
    alert_tasks_factory: Callable[[Any], Any] | None = None,
    status_store: SchedulerStatusStore | None = None,
    event_mask: int | None = None,
    event_states: Mapping[int, str] | None = None,
    reconcile_seconds: object | None = None,
):
    """Build and configure the scheduler without starting a background thread."""

    if scheduler_factory is None:
        real_factory, real_mask, real_states = _load_apscheduler_components()
        scheduler_factory = real_factory
        if event_mask is None:
            event_mask = real_mask
        if event_states is None:
            event_states = real_states
    else:
        event_mask = 0 if event_mask is None else event_mask
        event_states = {} if event_states is None else event_states

    status_store = status_store or SchedulerStatusStore()
    seconds = (
        _configured_reconcile_seconds()
        if reconcile_seconds is None
        else bounded_reconcile_seconds(reconcile_seconds)
    )
    scheduler = scheduler_factory(timezone=SCHEDULER_TIMEZONE)
    current_status = {
        item["id"]: dict(item)
        for item in status_store.read()
        if isinstance(item, dict) and item.get("id")
    }

    def run_tasks_listener(event) -> None:
        state = event_states.get(getattr(event, "code", None))
        job_id = getattr(event, "job_id", None)
        if state is None or not isinstance(job_id, str) or not job_id:
            return
        existing = current_status.get(
            job_id,
            {
                "id": job_id,
                "name": "--",
                "update_dt": "--",
                "next_run_dt": "--",
                "state": "未知",
            },
        )
        record = dict(existing)
        record["update_dt"] = _format_datetime(dt.datetime.now(SCHEDULER_TIMEZONE))
        job = scheduler.get_job(job_id)
        if job is not None:
            record["name"] = getattr(job, "name", "--") or "--"
            record["next_run_dt"] = _format_datetime(
                getattr(job, "next_run_time", None)
            )
        elif state == "删除作业":
            record["next_run_dt"] = "--"
        record["state"] = state
        current_status[job_id] = record
        status_store.write(current_status.values())

    scheduler.add_listener(run_tasks_listener, int(event_mask))

    task_factory = alert_tasks_factory or _default_alert_tasks_factory
    alert_tasks = task_factory(scheduler)
    if alert_tasks.run() is not True:
        raise RuntimeError("initial alert-task reconciliation failed")
    scheduler.add_job(
        alert_tasks.run,
        trigger="interval",
        seconds=seconds,
        id=RECONCILE_JOB_ID,
        name="监控任务配置同步",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def run_scheduler(
    *,
    lock_path: os.PathLike[str] | str | None = None,
    **build_options,
):
    """Acquire leadership, build once and start the blocking scheduler."""

    owner_path = pathlib.Path(lock_path) if lock_path is not None else _default_leader_lock_path()
    with SchedulerLeaderLock(owner_path):
        scheduler = build_scheduler(**build_options)
        scheduler.start()
        return scheduler


__all__ = [
    "DEFAULT_RECONCILE_SECONDS",
    "MAX_RECONCILE_SECONDS",
    "MIN_RECONCILE_SECONDS",
    "RECONCILE_JOB_ID",
    "SchedulerAlreadyRunningError",
    "SchedulerLeaderLock",
    "bounded_reconcile_seconds",
    "build_scheduler",
    "run_scheduler",
]
