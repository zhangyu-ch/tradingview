from __future__ import annotations

import json
import queue
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TickRequestError(ValueError):
    """Base class for stable tick-request failures."""

    code = "invalid_tick_request"
    http_status = 422


class TickRateLimitError(TickRequestError):
    code = "tick_rate_limited"
    http_status = 429


class TickProviderBusyError(TickRequestError):
    code = "tick_provider_busy"
    http_status = 503


class TickProviderTimeoutError(TickRequestError):
    code = "tick_provider_timeout"
    http_status = 504


class TickProviderCallError(RuntimeError):
    code = "tick_provider_failed"
    http_status = 502


@dataclass(frozen=True)
class TickRequest:
    market: str
    codes: tuple[str, ...]


def _contains_control_character(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


def parse_tick_request(
    market_value: Any,
    codes_value: Any,
    *,
    allowed_markets: Iterable[str],
    max_codes: int,
    max_code_bytes: int,
) -> TickRequest:
    """Validate a public tick request before any provider is constructed."""

    market = str(market_value or "").strip().lower()
    allowed = {str(item).strip().lower() for item in allowed_markets}
    if market == "" or market not in allowed:
        raise TickRequestError("unknown market")
    if max_codes <= 0 or max_code_bytes <= 0:
        raise RuntimeError("tick request limits must be positive")

    if isinstance(codes_value, str):
        try:
            raw_codes = json.loads(codes_value)
        except json.JSONDecodeError as exc:
            raise TickRequestError("codes must be a JSON array") from exc
    else:
        raw_codes = codes_value

    if not isinstance(raw_codes, list):
        raise TickRequestError("codes must be a JSON array")
    if not raw_codes:
        raise TickRequestError("codes must not be empty")
    # Enforce the raw cardinality before deduplication so duplicate-heavy input
    # cannot bypass the parsing/fan-out budget.
    if len(raw_codes) > max_codes:
        raise TickRequestError("too many codes")

    unique: list[str] = []
    seen: set[str] = set()
    for raw_code in raw_codes:
        if not isinstance(raw_code, str):
            raise TickRequestError("every code must be a string")
        code = raw_code.strip()
        if code == "":
            raise TickRequestError("code must not be empty")
        if _contains_control_character(code):
            raise TickRequestError("code contains control characters")
        if len(code.encode("utf-8")) > max_code_bytes:
            raise TickRequestError("code is too long")
        if code not in seen:
            seen.add(code)
            unique.append(code)

    return TickRequest(market=market, codes=tuple(unique))


class SlidingWindowLimiter:
    """Thread-safe, bounded in-process sliding-window limiter."""

    def __init__(self, *, max_requests: int, window_seconds: float, max_keys: int) -> None:
        if max_requests <= 0 or window_seconds <= 0 or max_keys <= 0:
            raise ValueError("limiter settings must be positive")
        self.max_requests = int(max_requests)
        self.window_seconds = float(window_seconds)
        self.max_keys = int(max_keys)
        self._lock = threading.Lock()
        self._events: OrderedDict[str, deque[float]] = OrderedDict()

    @property
    def key_count(self) -> int:
        with self._lock:
            return len(self._events)

    def check(self, key: str, *, now: float | None = None) -> None:
        key = str(key or "unknown")
        current = time.monotonic() if now is None else float(now)
        cutoff = current - self.window_seconds
        with self._lock:
            events = self._events.pop(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.max_requests:
                self._events[key] = events
                raise TickRateLimitError("tick request rate limit exceeded")
            events.append(current)
            self._events[key] = events
            while len(self._events) > self.max_keys:
                self._events.popitem(last=False)


class BoundedProviderCaller(Generic[T]):
    """Put a wall-clock deadline and a hard concurrency cap around sync SDK calls.

    Python cannot safely terminate an arbitrary blocked extension/SDK call. A timed-out
    daemon worker therefore keeps its slot until it exits; once all slots are occupied,
    new requests fail quickly instead of creating unbounded threads.
    """

    def __init__(self, *, max_concurrent: int, timeout_seconds: float) -> None:
        if max_concurrent <= 0 or timeout_seconds <= 0:
            raise ValueError("provider caller settings must be positive")
        self.max_concurrent = int(max_concurrent)
        self.timeout_seconds = float(timeout_seconds)
        self._slots = threading.BoundedSemaphore(self.max_concurrent)

    def call(self, function: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if not self._slots.acquire(blocking=False):
            raise TickProviderBusyError("tick provider is busy")

        result_queue: queue.SimpleQueue[tuple[bool, Any]] = queue.SimpleQueue()

        def run() -> None:
            try:
                result_queue.put((True, function(*args, **kwargs)))
            except BaseException as exc:  # preserve provider errors without losing slot cleanup
                result_queue.put((False, exc))
            finally:
                self._slots.release()

        worker = threading.Thread(target=run, name="tick-provider-call", daemon=True)
        worker.start()
        worker.join(self.timeout_seconds)
        if worker.is_alive():
            raise TickProviderTimeoutError("tick provider call timed out")

        try:
            ok, value = result_queue.get_nowait()
        except queue.Empty as exc:  # defensive: a completed worker must publish one result
            raise TickProviderCallError("tick provider returned no result") from exc
        if ok:
            return value
        raise TickProviderCallError("tick provider call failed") from value
