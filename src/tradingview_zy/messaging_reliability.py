from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from tradingview_zy.secret_store import redact_secrets


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry settings for one idempotent HTTP operation."""

    request_timeout_seconds: float = 5.0
    max_attempts: int = 3
    initial_backoff_seconds: float = 0.2
    max_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not 0.05 <= float(self.request_timeout_seconds) <= 60.0:
            raise ValueError("request_timeout_seconds must be between 0.05 and 60")
        if not 1 <= int(self.max_attempts) <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not 0.0 <= float(self.initial_backoff_seconds) <= 10.0:
            raise ValueError("initial_backoff_seconds must be between 0 and 10")
        if not 0.0 <= float(self.max_backoff_seconds) <= 30.0:
            raise ValueError("max_backoff_seconds must be between 0 and 30")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise ValueError("max_backoff_seconds must not be below initial_backoff_seconds")


@dataclass(frozen=True)
class RetryOutcome:
    result: Any | None
    error: Exception | None
    attempts: int
    exhausted: bool


def execute_with_retry(
    operation: Callable[[], Any],
    *,
    policy: RetryPolicy,
    should_retry_result: Callable[[Any], bool] | None = None,
    should_retry_exception: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> RetryOutcome:
    """Execute an already-time-bounded operation with finite retries.

    The caller must configure the underlying HTTP client's per-attempt timeout.
    This helper only controls the maximum attempt count and backoff.  It catches
    ``Exception`` rather than ``BaseException`` so cancellation and process
    termination signals are never swallowed.
    """

    retry_result = should_retry_result or (lambda _result: False)
    retry_exception = should_retry_exception or (lambda _error: True)
    last_result: Any | None = None
    last_error: Exception | None = None

    for attempt in range(1, policy.max_attempts + 1):
        try:
            last_result = operation()
            last_error = None
        except Exception as exc:  # noqa: BLE001 - policy decides retryability
            last_result = None
            last_error = exc
            should_retry = retry_exception(exc)
        else:
            should_retry = retry_result(last_result)
            if not should_retry:
                return RetryOutcome(last_result, None, attempt, False)

        if not should_retry or attempt >= policy.max_attempts:
            return RetryOutcome(last_result, last_error, attempt, should_retry)

        delay = min(
            policy.initial_backoff_seconds * (2 ** (attempt - 1)),
            policy.max_backoff_seconds,
        )
        if delay > 0:
            sleep(delay)

    raise AssertionError("bounded retry loop terminated unexpectedly")


def redact_sensitive(value: object, secrets: list[str] | tuple[str, ...]) -> str:
    """Return a compact diagnostic string through the central secret redactor."""

    return redact_secrets(value, tuple(str(secret) for secret in secrets if secret))[:300]
