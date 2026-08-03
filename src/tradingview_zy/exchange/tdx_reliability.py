from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


class ProviderUnavailableError(RuntimeError):
    """A market-data provider could not become ready within its deadline."""


def call_with_bounded_retry(
    operation: Callable[[float], T],
    *,
    recover: Callable[[], object] | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    deadline_seconds: float = 12.0,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    description: str = "TDX provider initialization",
) -> T:
    """Run a retryable TDX operation with both attempt and wall-clock bounds.

    ``operation`` receives the remaining deadline so the SDK connection timeout
    can never exceed the overall budget.  Recovery (for example selecting a new
    node) is also inside the same budget.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if deadline_seconds <= 0:
        raise ValueError("deadline_seconds must be positive")

    started = clock()
    deadline = started + deadline_seconds
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        try:
            result = operation(remaining)
            if clock() > deadline:
                last_error = TimeoutError("operation completed after its deadline")
                break
            return result
        except retry_on as exc:
            last_error = exc
            if attempt >= max_attempts:
                break

            if recover is not None:
                remaining = deadline - clock()
                if remaining <= 0:
                    break
                try:
                    recover()
                except retry_on as recover_exc:
                    last_error = recover_exc

            remaining = deadline - clock()
            if remaining <= 0:
                break
            delay = min(
                base_delay_seconds * (2 ** (attempt - 1)),
                max_delay_seconds,
                remaining,
            )
            if delay > 0:
                sleeper(delay)

    elapsed = max(0.0, clock() - started)
    message = (
        f"{description} unavailable after {max_attempts} attempts "
        f"within {deadline_seconds:.2f}s (elapsed {elapsed:.2f}s)"
    )
    raise ProviderUnavailableError(message) from last_error
