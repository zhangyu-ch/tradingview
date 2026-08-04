"""Thread-safe, failure-isolated ownership for Futu quote/trade contexts."""
from __future__ import annotations

import atexit
import datetime as dt
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Literal, TypeVar


ContextKind = Literal["quote", "trade"]
T = TypeVar("T")


class FutuContextError(RuntimeError):
    """Base class for deterministic Futu lifecycle failures."""


class FutuContextClosedError(FutuContextError):
    """Raised when an operation is attempted after deterministic shutdown."""


class FutuContextUnavailableError(FutuContextError):
    """Raised after the bounded context creation/operation attempts are exhausted."""


class FutuOperationError(FutuContextError):
    """Raised by an adapter when the SDK returns a non-success business status."""


@dataclass(slots=True)
class _ContextSlot:
    factory: Callable[[], Any]
    context: Any | None = None
    generation: int = 0
    state: str = "degraded"
    last_success_at: str | None = None
    last_error_type: str | None = None


class FutuContextManager:
    """Own quote and trade SDK contexts behind independent serialized boundaries.

    A logical operation can use an existing context and, after a failure, rebuild it
    once by default.  Only a fully constructed candidate is published.  Quote and
    trade failures are isolated from each other and every retained context has a
    deterministic close path.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        quote_factory: Callable[[], Any],
        trade_factory: Callable[[], Any],
        max_attempts: int = 2,
        register_atexit: bool = True,
    ) -> None:
        if not isinstance(max_attempts, int) or isinstance(max_attempts, bool):
            raise TypeError("max_attempts must be an integer")
        if max_attempts < 1 or max_attempts > 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not callable(quote_factory) or not callable(trade_factory):
            raise TypeError("quote_factory and trade_factory must be callable")

        self._enabled = bool(enabled)
        self._max_attempts = max_attempts
        self._quote = _ContextSlot(quote_factory)
        self._trade = _ContextSlot(trade_factory)
        self._lifecycle_lock = threading.RLock()
        self._quote_lock = threading.RLock()
        self._trade_lock = threading.RLock()
        self._closed = False
        self._pid = os.getpid()

        if register_atexit:
            atexit.register(self.close)
        register_at_fork = getattr(os, "register_at_fork", None)
        if callable(register_at_fork):
            register_at_fork(after_in_child=self._after_fork_child)

    @staticmethod
    def _utc_now() -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat()

    @staticmethod
    def _safe_close(context: Any | None) -> None:
        if context is None:
            return
        close = getattr(context, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                # Shutdown and invalidation are best-effort.  The context is never
                # retained after this point, even when a third-party close fails.
                pass

    def _after_fork_child(self) -> None:
        """Drop inherited sockets/threads and replace possibly inherited locks."""

        old_contexts = (self._quote.context, self._trade.context)
        self._lifecycle_lock = threading.RLock()
        self._quote_lock = threading.RLock()
        self._trade_lock = threading.RLock()
        self._pid = os.getpid()
        self._quote.context = None
        self._trade.context = None
        for slot in (self._quote, self._trade):
            slot.state = "degraded"
            slot.last_error_type = "ProcessBoundary"
        for context in old_contexts:
            self._safe_close(context)

    def _ensure_process_locked(self) -> None:
        current_pid = os.getpid()
        if current_pid == self._pid:
            return
        # A real fork leaves only the calling thread in the child.  Do not trust
        # inherited SDK objects; discard both ownership domains before reuse.
        old_contexts = (self._quote.context, self._trade.context)
        self._pid = current_pid
        self._quote.context = None
        self._trade.context = None
        for slot in (self._quote, self._trade):
            slot.state = "degraded"
            slot.last_error_type = "ProcessBoundary"
        for context in old_contexts:
            self._safe_close(context)

    def _ensure_active_locked(self) -> None:
        if self._closed:
            raise FutuContextClosedError("Futu context manager is closed")
        if not self._enabled:
            raise FutuContextUnavailableError("Futu provider is not configured")

    def _slot_for(self, kind: ContextKind) -> tuple[_ContextSlot, threading.RLock]:
        if kind == "quote":
            return self._quote, self._quote_lock
        if kind == "trade":
            return self._trade, self._trade_lock
        raise ValueError(f"unknown Futu context kind: {kind!r}")

    @contextmanager
    def _locked_slot(self, kind: ContextKind) -> Iterator[_ContextSlot]:
        # Global order is lifecycle -> kind.  close() uses the same order, so it
        # waits for in-flight operations without racing a newly starting one.
        self._lifecycle_lock.acquire()
        lock: threading.RLock | None = None
        try:
            self._ensure_active_locked()
            self._ensure_process_locked()
            slot, lock = self._slot_for(kind)
            lock.acquire()
        finally:
            self._lifecycle_lock.release()

        try:
            yield slot
        finally:
            assert lock is not None
            lock.release()

    def _invalidate(self, slot: _ContextSlot, error: Exception) -> None:
        context = slot.context
        slot.context = None
        slot.state = "degraded"
        slot.last_error_type = type(error).__name__
        self._safe_close(context)

    def _run(self, kind: ContextKind, operation: Callable[[Any], T]) -> T:
        if not callable(operation):
            raise TypeError("operation must be callable")

        with self._locked_slot(kind) as slot:
            last_error: Exception | None = None
            for _attempt in range(self._max_attempts):
                try:
                    context = slot.context
                    if context is None:
                        candidate = slot.factory()
                        if candidate is None:
                            raise FutuContextUnavailableError(
                                f"{kind} context factory returned no context"
                            )
                        # Publish only after the factory has returned successfully.
                        slot.context = candidate
                        slot.generation += 1
                        slot.state = "ready"
                        slot.last_error_type = None
                        context = candidate

                    result = operation(context)
                except Exception as error:
                    last_error = error
                    self._invalidate(slot, error)
                    continue

                slot.state = "ready"
                slot.last_success_at = self._utc_now()
                slot.last_error_type = None
                return result

            assert last_error is not None
            raise FutuContextUnavailableError(
                f"{kind} context operation failed after {self._max_attempts} attempts"
            ) from last_error

    def run_quote(self, operation: Callable[[Any], T]) -> T:
        return self._run("quote", operation)

    def run_trade(self, operation: Callable[[Any], T]) -> T:
        return self._run("trade", operation)

    @staticmethod
    def _slot_health(slot: _ContextSlot) -> dict[str, Any]:
        return {
            "state": slot.state,
            "generation": slot.generation,
            "last_success_at": slot.last_success_at,
            "last_error_type": slot.last_error_type,
        }

    def health(self) -> dict[str, Any]:
        """Return lifecycle state without host, account, token, or other secrets."""

        with self._lifecycle_lock:
            self._ensure_process_locked()
            with self._quote_lock, self._trade_lock:
                if self._closed:
                    state = "closed"
                elif not self._enabled:
                    state = "degraded"
                elif self._quote.state == "ready" or self._trade.state == "ready":
                    state = "ready"
                else:
                    state = "degraded"
                return {
                    "state": state,
                    "pid": self._pid,
                    "quote": self._slot_health(self._quote),
                    "trade": self._slot_health(self._trade),
                }

    def close(self) -> None:
        """Close both retained contexts exactly once and reject future work."""

        with self._lifecycle_lock:
            if self._closed:
                return
            self._closed = True
            with self._quote_lock, self._trade_lock:
                for slot in (self._quote, self._trade):
                    context = slot.context
                    slot.context = None
                    slot.state = "closed"
                    self._safe_close(context)

    def __enter__(self) -> "FutuContextManager":
        with self._lifecycle_lock:
            self._ensure_active_locked()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback
        self.close()
