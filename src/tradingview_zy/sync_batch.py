"""Recoverable, auditable batch synchronization for historical K-lines.

The module is intentionally free of provider imports and application
configuration.  Provider modules are imported lazily inside the CLI execution
path and every constructor/query/write is placed behind a wall-clock call
budget.  A third-party call that ignores its own timeout cannot be killed safely
in Python; timed-out calls therefore remain in daemon threads and keep a bounded
slot until they finish.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import queue
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

CHECKPOINT_SCHEMA_VERSION = 1
_ITEM_SEPARATOR = "::"


class SyncBatchError(RuntimeError):
    """Base class for stable synchronization failures."""


class SyncCheckpointError(SyncBatchError):
    """Checkpoint is corrupt or belongs to a different batch definition."""


class SyncCallTimeoutError(SyncBatchError):
    """One external constructor/query/write exceeded its wall-clock budget."""


class SyncCallBusyError(SyncBatchError):
    """All bounded external-call slots are still occupied."""


class SyncBatchDeadlineError(SyncBatchError):
    """The total batch deadline has been exhausted."""


class SyncNoProgressError(SyncBatchError):
    """A paginated source returned the same terminal bar repeatedly."""


@dataclass(frozen=True)
class SyncOutcome:
    rows_written: int = 0
    pages: int = 0
    skipped: bool = False
    progress_token: str | None = None


@dataclass(frozen=True)
class BatchRunResult:
    batch_id: str
    status: str
    exit_code: int
    completed: int
    failed: int
    pending: int
    skipped: int
    checkpoint: str


class BatchDeadline:
    def __init__(self, seconds: float, *, clock: Callable[[], float] = time.monotonic):
        if seconds <= 0:
            raise ValueError("batch deadline must be positive")
        self.seconds = float(seconds)
        self._clock = clock
        self._started = clock()

    def remaining(self) -> float:
        return max(0.0, self.seconds - (self._clock() - self._started))

    def require_remaining(self) -> float:
        remaining = self.remaining()
        if remaining <= 0:
            raise SyncBatchDeadlineError("batch deadline exceeded")
        return remaining


class DeadlineCaller:
    """Bound synchronous SDK calls without spawning unbounded worker threads."""

    def __init__(self, *, max_concurrent: int = 2) -> None:
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        self.max_concurrent = int(max_concurrent)
        self._slots = threading.BoundedSemaphore(self.max_concurrent)

    def call(
        self,
        function: Callable[..., Any],
        *args: Any,
        timeout_seconds: float,
        **kwargs: Any,
    ) -> Any:
        if timeout_seconds <= 0:
            raise SyncBatchDeadlineError("no external-call budget remains")
        if not self._slots.acquire(blocking=False):
            raise SyncCallBusyError("external-call capacity is exhausted")

        result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def run() -> None:
            try:
                result_queue.put((True, function(*args, **kwargs)))
            except BaseException as exc:  # retain exact provider/DB exception
                result_queue.put((False, exc))
            finally:
                self._slots.release()

        worker = threading.Thread(target=run, name="sync-external-call", daemon=True)
        worker.start()
        worker.join(float(timeout_seconds))
        if worker.is_alive():
            raise SyncCallTimeoutError(
                f"external call exceeded {float(timeout_seconds):.3f}s"
            )

        try:
            ok, value = result_queue.get_nowait()
        except queue.Empty as exc:
            raise SyncBatchError("external call completed without a result") from exc
        if ok:
            return value
        raise value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _item_key(code: str, frequency: str) -> str:
    return f"{code}{_ITEM_SEPARATOR}{frequency}"


def _safe_error(exc: BaseException, *, limit: int = 600) -> str:
    text = f"{type(exc).__name__}: {exc}".replace("\x00", "")
    return text[:limit]


def _summary(items: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    counts = {"completed": 0, "failed": 0, "pending": 0, "running": 0, "skipped": 0}
    for item in items.values():
        status = str(item.get("status", "pending"))
        if status in counts:
            counts[status] += 1
        else:
            counts["pending"] += 1
        if bool(item.get("skipped")):
            counts["skipped"] += 1
    return counts


class BatchCheckpoint:
    """Atomic JSON checkpoint with per-symbol/per-frequency audit records."""

    def __init__(self, path: Path, *, now: Callable[[], str] = _utc_now) -> None:
        self.path = Path(path)
        self._now = now
        self._lock = threading.RLock()
        self.state: dict[str, Any] = {}

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SyncCheckpointError(f"cannot read checkpoint {self.path}: {exc}") from exc
        if not isinstance(data, dict):
            raise SyncCheckpointError("checkpoint root must be an object")
        if data.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise SyncCheckpointError("unsupported checkpoint schema version")
        if not isinstance(data.get("items"), dict):
            raise SyncCheckpointError("checkpoint items must be an object")
        return data

    def _atomic_write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.state, ensure_ascii=False, indent=2) + "\n"
        temp = self.path.with_name(
            f".{self.path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
        )
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, self.path)
            try:
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass

    def _save(self) -> None:
        self.state["updated_at"] = self._now()
        self.state["summary"] = _summary(self.state["items"])
        self._atomic_write()

    def prepare(
        self,
        *,
        market: str,
        items: Sequence[tuple[str, str]],
        config_digest: str,
        resume: bool,
    ) -> None:
        with self._lock:
            if resume and self.path.exists():
                state = self._read()
                if state.get("market") != market:
                    raise SyncCheckpointError("checkpoint market does not match config")
                if state.get("config_digest") != config_digest:
                    raise SyncCheckpointError(
                        "checkpoint config digest differs; use --no-resume or another path"
                    )
                self.state = state
                for item in self.state["items"].values():
                    if item.get("status") == "running":
                        item["status"] = "pending"
                        item["last_error"] = "previous process stopped while item was running"
                self.state["resume_count"] = int(self.state.get("resume_count", 0)) + 1
            else:
                created = self._now()
                self.state = {
                    "schema_version": CHECKPOINT_SCHEMA_VERSION,
                    "batch_id": f"{market}-{uuid.uuid4().hex}",
                    "market": market,
                    "config_digest": config_digest,
                    "status": "running",
                    "created_at": created,
                    "updated_at": created,
                    "resume_count": 0,
                    "items": {},
                    "batch_error": "",
                }

            expected_keys = {_item_key(code, frequency) for code, frequency in items}
            existing_keys = set(self.state["items"])
            if existing_keys and existing_keys != expected_keys:
                raise SyncCheckpointError(
                    "checkpoint item set differs despite matching config digest"
                )
            for code, frequency in items:
                key = _item_key(code, frequency)
                self.state["items"].setdefault(
                    key,
                    {
                        "code": code,
                        "frequency": frequency,
                        "status": "pending",
                        "attempts": 0,
                        "rows_written": 0,
                        "pages": 0,
                        "skipped": False,
                        "progress_token": None,
                        "last_error": "",
                        "started_at": None,
                        "finished_at": None,
                    },
                )
            self.state["status"] = "running"
            self.state["batch_error"] = ""
            self._save()

    @property
    def batch_id(self) -> str:
        return str(self.state["batch_id"])

    def item_status(self, code: str, frequency: str) -> str:
        return str(self.state["items"][_item_key(code, frequency)]["status"])

    def mark_running(self, code: str, frequency: str) -> None:
        with self._lock:
            item = self.state["items"][_item_key(code, frequency)]
            item.update(
                {
                    "status": "running",
                    "attempts": int(item.get("attempts", 0)) + 1,
                    "started_at": self._now(),
                    "finished_at": None,
                    "last_error": "",
                }
            )
            self._save()

    def mark_completed(self, code: str, frequency: str, outcome: SyncOutcome) -> None:
        with self._lock:
            item = self.state["items"][_item_key(code, frequency)]
            item.update(
                {
                    "status": "completed",
                    "rows_written": int(item.get("rows_written", 0))
                    + int(outcome.rows_written),
                    "pages": int(item.get("pages", 0)) + int(outcome.pages),
                    "skipped": bool(outcome.skipped),
                    "progress_token": outcome.progress_token,
                    "last_error": "",
                    "finished_at": self._now(),
                }
            )
            self._save()

    def mark_failed(self, code: str, frequency: str, exc: BaseException) -> None:
        with self._lock:
            item = self.state["items"][_item_key(code, frequency)]
            item.update(
                {
                    "status": "failed",
                    "last_error": _safe_error(exc),
                    "finished_at": self._now(),
                }
            )
            self._save()

    def finalize(self, status: str, *, batch_error: str = "") -> None:
        with self._lock:
            self.state["status"] = status
            self.state["batch_error"] = batch_error[:600]
            self.state["finished_at"] = self._now()
            self._save()


def _call_with_budget(
    caller: DeadlineCaller,
    deadline: BatchDeadline,
    per_call_timeout: float,
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    remaining = deadline.require_remaining()
    timeout = min(float(per_call_timeout), remaining)
    return caller.call(function, *args, timeout_seconds=timeout, **kwargs)


def _frame_length(frame: Any) -> int:
    if frame is None:
        return 0
    try:
        return int(len(frame))
    except TypeError as exc:
        raise SyncBatchError("provider K-line result has no length") from exc


def _frame_progress_token(frame: Any) -> str | None:
    if frame is None or _frame_length(frame) == 0:
        return None
    try:
        dates = frame["date"]
        value = dates.max()
    except Exception as exc:
        raise SyncBatchError("provider K-line result is missing a usable date column") from exc
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)


def sync_incremental_series(
    *,
    destination: Any,
    source: Any,
    code: str,
    frequency: str,
    start_date: str | None,
    query_args: Mapping[str, Any] | None,
    stop_rows: int,
    max_pages: int,
    deadline: BatchDeadline,
    caller: DeadlineCaller,
    per_call_timeout: float,
) -> SyncOutcome:
    """Idempotently upsert one symbol/frequency until the source stops advancing."""

    if stop_rows < 0 or max_pages < 1:
        raise ValueError("stop_rows and max_pages are invalid")
    total_rows = 0
    seen_tokens: set[str] = set()
    last_token: str | None = None

    for page in range(1, max_pages + 1):
        last_datetime = _call_with_budget(
            caller,
            deadline,
            per_call_timeout,
            destination.query_last_datetime,
            code,
            frequency,
        )
        effective_start = last_datetime if last_datetime is not None else start_date
        kwargs: dict[str, Any] = {"args": dict(query_args or {})}
        if effective_start is not None:
            kwargs["start_date"] = effective_start
        frame = _call_with_budget(
            caller,
            deadline,
            per_call_timeout,
            source.klines,
            code,
            frequency,
            **kwargs,
        )
        row_count = _frame_length(frame)
        if row_count == 0:
            return SyncOutcome(
                rows_written=total_rows,
                pages=page - 1,
                progress_token=last_token,
            )

        token = _frame_progress_token(frame)
        if token is None or token in seen_tokens:
            raise SyncNoProgressError(
                f"{code} {frequency} did not advance beyond {token!r}"
            )
        seen_tokens.add(token)
        last_token = token

        inserted = _call_with_budget(
            caller,
            deadline,
            per_call_timeout,
            destination.insert_klines,
            code,
            frequency,
            frame,
        )
        if inserted is not True:
            raise SyncBatchError("destination did not confirm K-line upsert")
        total_rows += row_count
        if row_count <= stop_rows:
            return SyncOutcome(
                rows_written=total_rows,
                pages=page,
                progress_token=last_token,
            )

    raise SyncNoProgressError(
        f"{code} {frequency} exceeded max_pages={max_pages} without a terminal page"
    )


def sync_missing_series(
    *,
    destination: Any,
    source: Any,
    code: str,
    frequency: str,
    query_args: Mapping[str, Any] | None,
    deadline: BatchDeadline,
    caller: DeadlineCaller,
    per_call_timeout: float,
) -> SyncOutcome:
    """Fetch a one-shot series only when the destination has no persisted bars."""

    last_datetime = _call_with_budget(
        caller,
        deadline,
        per_call_timeout,
        destination.query_last_datetime,
        code,
        frequency,
    )
    if last_datetime is not None:
        return SyncOutcome(skipped=True, progress_token=str(last_datetime))

    frame = _call_with_budget(
        caller,
        deadline,
        per_call_timeout,
        source.klines,
        code,
        frequency,
        args=dict(query_args or {}),
    )
    row_count = _frame_length(frame)
    if row_count == 0:
        return SyncOutcome(pages=0)
    token = _frame_progress_token(frame)
    inserted = _call_with_budget(
        caller,
        deadline,
        per_call_timeout,
        destination.insert_klines,
        code,
        frequency,
        frame,
    )
    if inserted is not True:
        raise SyncBatchError("destination did not confirm K-line upsert")
    return SyncOutcome(rows_written=row_count, pages=1, progress_token=token)


def run_sync_batch(
    *,
    market: str,
    items: Sequence[tuple[str, str]],
    config_digest: str,
    checkpoint_path: Path,
    synchronizer: Callable[[str, str, BatchDeadline, DeadlineCaller], SyncOutcome],
    deadline: BatchDeadline,
    caller: DeadlineCaller,
    resume: bool = True,
    now: Callable[[], str] = _utc_now,
) -> BatchRunResult:
    """Run items sequentially, checkpointing before and after every item."""

    checkpoint = BatchCheckpoint(checkpoint_path, now=now)
    checkpoint.prepare(
        market=market,
        items=items,
        config_digest=config_digest,
        resume=resume,
    )

    try:
        for code, frequency in items:
            if checkpoint.item_status(code, frequency) == "completed":
                continue
            if deadline.remaining() <= 0:
                checkpoint.finalize(
                    "deadline_exceeded", batch_error="batch deadline exceeded"
                )
                break
            checkpoint.mark_running(code, frequency)
            try:
                outcome = synchronizer(code, frequency, deadline, caller)
            except KeyboardInterrupt:
                checkpoint.mark_failed(
                    code, frequency, SyncBatchError("batch interrupted by operator")
                )
                checkpoint.finalize("interrupted", batch_error="operator interrupt")
                break
            except Exception as exc:
                checkpoint.mark_failed(code, frequency, exc)
            else:
                checkpoint.mark_completed(code, frequency, outcome)
        else:
            counts = _summary(checkpoint.state["items"])
            final_status = "completed" if counts["failed"] == 0 else "completed_with_errors"
            checkpoint.finalize(final_status)
    except BaseException as exc:
        checkpoint.finalize("failed", batch_error=_safe_error(exc))
        raise

    counts = _summary(checkpoint.state["items"])
    status = str(checkpoint.state["status"])
    exit_code = {
        "completed": 0,
        "completed_with_errors": 2,
        "deadline_exceeded": 3,
        "interrupted": 130,
    }.get(status, 1)
    return BatchRunResult(
        batch_id=checkpoint.batch_id,
        status=status,
        exit_code=exit_code,
        completed=counts["completed"],
        failed=counts["failed"],
        pending=counts["pending"] + counts["running"],
        skipped=counts["skipped"],
        checkpoint=str(checkpoint.path),
    )


def _canonical_digest(config: Mapping[str, Any]) -> str:
    payload = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_sync_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SyncBatchError(f"cannot load sync config {path}: {exc}") from exc
    if not isinstance(config, dict):
        raise SyncBatchError("sync config root must be an object")
    for key in ["market", "mode", "source", "destination", "universe", "frequencies"]:
        if key not in config:
            raise SyncBatchError(f"sync config is missing {key!r}")
    if config["mode"] not in {"incremental", "missing_only"}:
        raise SyncBatchError("sync mode must be incremental or missing_only")
    if not isinstance(config["frequencies"], dict) or not config["frequencies"]:
        raise SyncBatchError("frequencies must be a non-empty object")
    return config


def _instantiate(spec: Mapping[str, Any]) -> Any:
    if not isinstance(spec, Mapping):
        raise SyncBatchError("provider specification must be an object")
    module_name = str(spec.get("module", "")).strip()
    class_name = str(spec.get("class", "")).strip()
    if not module_name or not class_name:
        raise SyncBatchError("provider module and class are required")
    module = importlib.import_module(module_name)
    provider_class = getattr(module, class_name)
    args = list(spec.get("args", []))
    kwargs = dict(spec.get("kwargs", {}))
    return provider_class(*args, **kwargs)


def _normalize_codes(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        code = str(value).strip()
        if not code:
            raise SyncBatchError("universe contains an empty code")
        if code not in seen:
            seen.add(code)
            result.append(code)
    if not result:
        raise SyncBatchError("universe is empty")
    return result


def _load_universe(
    universe: Mapping[str, Any],
    *,
    source: Any,
    caller: DeadlineCaller,
    deadline: BatchDeadline,
    per_call_timeout: float,
) -> list[str]:
    universe_type = str(universe.get("type", "")).strip()
    if universe_type == "list":
        codes = universe.get("codes")
        if not isinstance(codes, list):
            raise SyncBatchError("list universe requires a codes array")
        return _normalize_codes(codes)
    if universe_type == "provider_all_stocks":
        stocks = _call_with_budget(
            caller, deadline, per_call_timeout, source.all_stocks
        )
        try:
            return _normalize_codes(item["code"] for item in stocks)
        except (TypeError, KeyError) as exc:
            raise SyncBatchError("provider stock universe has an invalid shape") from exc
    raise SyncBatchError(f"unsupported universe type: {universe_type!r}")


def _write_initialization_failure(
    path: Path,
    *,
    market: str,
    config_digest: str,
    exc: BaseException,
) -> BatchRunResult:
    state = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "batch_id": f"{market}-{uuid.uuid4().hex}",
        "market": market,
        "config_digest": config_digest,
        "status": "initialization_failed",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "finished_at": _utc_now(),
        "resume_count": 0,
        "items": {},
        "summary": _summary({}),
        "batch_error": _safe_error(exc),
    }
    checkpoint = BatchCheckpoint(path)
    checkpoint.state = state
    checkpoint._atomic_write()
    return BatchRunResult(
        batch_id=str(state["batch_id"]),
        status="initialization_failed",
        exit_code=1,
        completed=0,
        failed=0,
        pending=0,
        skipped=0,
        checkpoint=str(path),
    )


def run_configured_sync(
    *,
    config_path: Path,
    checkpoint_path: Path,
    batch_deadline_seconds: float,
    per_call_timeout: float,
    resume: bool = True,
) -> BatchRunResult:
    config = load_sync_config(config_path)
    digest = _canonical_digest(config)
    market = str(config["market"]).strip()
    deadline = BatchDeadline(batch_deadline_seconds)
    caller = DeadlineCaller(max_concurrent=2)

    try:
        source = _call_with_budget(
            caller, deadline, per_call_timeout, _instantiate, config["source"]
        )
        destination = _call_with_budget(
            caller, deadline, per_call_timeout, _instantiate, config["destination"]
        )
        codes = _load_universe(
            config["universe"],
            source=source,
            caller=caller,
            deadline=deadline,
            per_call_timeout=per_call_timeout,
        )
    except Exception as exc:
        return _write_initialization_failure(
            checkpoint_path, market=market, config_digest=digest, exc=exc
        )

    frequencies = [str(value) for value in config["frequencies"].keys()]
    items = [(code, frequency) for code in codes for frequency in frequencies]
    mode = str(config["mode"])
    default_max_pages = int(config.get("max_pages", 100))

    def synchronize(
        code: str,
        frequency: str,
        item_deadline: BatchDeadline,
        item_caller: DeadlineCaller,
    ) -> SyncOutcome:
        spec = config["frequencies"][frequency]
        if not isinstance(spec, Mapping):
            raise SyncBatchError(f"frequency {frequency!r} config must be an object")
        if mode == "incremental":
            return sync_incremental_series(
                destination=destination,
                source=source,
                code=code,
                frequency=frequency,
                start_date=spec.get("start_date"),
                query_args=spec.get("args", {}),
                stop_rows=int(spec.get("stop_rows", 1)),
                max_pages=int(spec.get("max_pages", default_max_pages)),
                deadline=item_deadline,
                caller=item_caller,
                per_call_timeout=per_call_timeout,
            )
        return sync_missing_series(
            destination=destination,
            source=source,
            code=code,
            frequency=frequency,
            query_args=spec.get("args", {}),
            deadline=item_deadline,
            caller=item_caller,
            per_call_timeout=per_call_timeout,
        )

    return run_sync_batch(
        market=market,
        items=items,
        config_digest=digest,
        checkpoint_path=checkpoint_path,
        synchronizer=synchronize,
        deadline=deadline,
        caller=caller,
        resume=resume,
    )


def configured_sync_cli(default_config: Path, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an auditable, checkpointed historical K-line sync batch"
    )
    parser.add_argument("--config", type=Path, default=Path(default_config))
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--batch-deadline", type=float, default=3600.0)
    parser.add_argument("--call-timeout", type=float, default=60.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)
    checkpoint = args.checkpoint or (
        Path("data") / "sync_checkpoints" / f"{args.config.stem}.json"
    )
    result = run_configured_sync(
        config_path=args.config,
        checkpoint_path=checkpoint,
        batch_deadline_seconds=args.batch_deadline,
        per_call_timeout=args.call_timeout,
        resume=not args.no_resume,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return result.exit_code
