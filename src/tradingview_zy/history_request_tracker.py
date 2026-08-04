"""Bounded, thread-safe request state for the TradingView history endpoint.

The TradingView client can issue several closely spaced follow-up history
requests while panning or zooming.  The Web route historically used a plain
``dict`` to count those requests and returned ``no_data`` periodically, but
that state grew without bound and its read/modify/write sequence was racy.

This module keeps the existing cadence while making the state explicit,
bounded, expiring and safe to share between request threads in one process.
"""

from __future__ import annotations

import math
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Hashable, TypeAlias


HistoryRequestKey: TypeAlias = tuple[str, str, str, str, str]


@dataclass(slots=True)
class _HistoryRequestEntry:
    """Mutable state guarded by :class:`HistoryRequestTracker`'s lock."""

    counter: int
    last_seen: float


def _positive_finite_number(value: object, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a positive finite number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(f"{field} must be a positive finite number")
    return parsed


def _positive_int(value: object, *, field: str, maximum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer between 1 and {maximum}")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{field} must be an integer between 1 and {maximum}")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field} must be an integer between 1 and {maximum}"
        ) from exc
    if parsed < 1 or parsed > maximum:
        raise ValueError(f"{field} must be an integer between 1 and {maximum}")
    return parsed


def history_request_key(
    *,
    user_id: object,
    remote_addr: object,
    market: object,
    code: object,
    resolution: object,
) -> HistoryRequestKey:
    """Build the stable identity used by the bounded history tracker.

    Authentication identity and remote address are both part of the key so one
    browser or proxy client cannot consume another client's short request
    cadence.  Market, code and resolution keep independent chart series apart.
    Request-facing market/symbol validation remains the route's responsibility.
    """

    return (
        str(user_id or "anonymous"),
        str(remote_addr or "unknown"),
        str(market),
        str(code),
        str(resolution),
    )


class HistoryRequestTracker:
    """Thread-safe TTL/LRU tracker preserving the legacy ``no_data`` cadence.

    For a continuously active key, the first ``max_requests_per_window`` calls
    return ``"ok"`` and the next call returns ``"no_data"``.  That suppression
    call resets the per-key counter, matching the old Web route.  A quiet period
    longer than ``burst_window_seconds`` also resets the counter.

    State is process-local by design, but it is strictly bounded and cannot
    grow beyond ``max_entries``.  Multi-process deployments therefore do not
    rely on this helper as an authorization or security boundary.
    """

    def __init__(
        self,
        *,
        max_entries: int = 4_096,
        entry_ttl_seconds: float = 900.0,
        burst_window_seconds: float = 5.0,
        max_requests_per_window: int = 6,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_entries = _positive_int(
            max_entries, field="max_entries", maximum=100_000
        )
        self.max_requests_per_window = _positive_int(
            max_requests_per_window,
            field="max_requests_per_window",
            maximum=1_000,
        )
        self.entry_ttl_seconds = _positive_finite_number(
            entry_ttl_seconds, field="entry_ttl_seconds"
        )
        self.burst_window_seconds = _positive_finite_number(
            burst_window_seconds, field="burst_window_seconds"
        )
        if self.entry_ttl_seconds < self.burst_window_seconds:
            raise ValueError(
                "entry_ttl_seconds must be greater than or equal to "
                "burst_window_seconds"
            )
        if not callable(clock):
            raise TypeError("clock must be callable")

        self._clock = clock
        self._entries: OrderedDict[Hashable, _HistoryRequestEntry] = OrderedDict()
        self._lock = threading.RLock()

    @staticmethod
    def _validate_now(value: object) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("now must be a finite monotonic timestamp") from exc
        if not math.isfinite(parsed):
            raise ValueError("now must be a finite monotonic timestamp")
        return parsed

    @staticmethod
    def _validate_key(key: Hashable) -> None:
        try:
            hash(key)
        except TypeError as exc:
            raise TypeError("history request key must be hashable") from exc

    def _prune_expired_locked(self, now: float) -> None:
        expired = [
            key
            for key, entry in self._entries.items()
            if now - entry.last_seen > self.entry_ttl_seconds
        ]
        for key in expired:
            self._entries.pop(key, None)

    def record(self, key: Hashable, *, now: float | None = None) -> str:
        """Atomically record a follow-up request and return ``ok``/``no_data``."""

        self._validate_key(key)
        observed_at = self._validate_now(self._clock() if now is None else now)

        with self._lock:
            self._prune_expired_locked(observed_at)
            entry = self._entries.get(key)
            if entry is None:
                if len(self._entries) >= self.max_entries:
                    self._entries.popitem(last=False)
                self._entries[key] = _HistoryRequestEntry(
                    counter=0, last_seen=observed_at
                )
                return "ok"

            elapsed = observed_at - entry.last_seen
            if elapsed < 0 or elapsed > self.burst_window_seconds:
                entry.counter = 0
                entry.last_seen = observed_at
                self._entries.move_to_end(key)
                return "ok"

            if entry.counter >= self.max_requests_per_window - 1:
                entry.counter = 0
                entry.last_seen = observed_at
                self._entries.move_to_end(key)
                return "no_data"

            entry.counter += 1
            entry.last_seen = observed_at
            self._entries.move_to_end(key)
            return "ok"

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def snapshot_keys(self) -> tuple[Hashable, ...]:
        """Return LRU-to-MRU keys for diagnostics and deterministic tests."""

        with self._lock:
            return tuple(self._entries.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
