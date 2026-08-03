"""Reliability and data-contract helpers for the BaoStock adapter.

The upstream SDK exposes result objects with string error codes and does not
accept a request timeout.  These helpers therefore bound *retries and total
retry time*; they cannot interrupt one SDK call that is already blocked in the
vendor implementation.
"""
from __future__ import annotations

import time
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Callable, TypeVar

T = TypeVar("T")

AUTH_ERROR_CODES = frozenset({"10001001", "10002007"})


class BaostockQueryError(RuntimeError):
    """Raised when BaoStock returns a non-retryable protocol error."""


class BaostockUnavailableError(BaostockQueryError):
    """Raised when a bounded BaoStock retry budget is exhausted."""


def _result_detail(result: object) -> tuple[str, str]:
    code = str(getattr(result, "error_code", ""))
    message = str(getattr(result, "error_msg", ""))
    return code, message


def require_successful_login(result: object) -> None:
    """Validate the SDK login response instead of silently continuing."""

    code, message = _result_detail(result)
    if code != "0":
        raise BaostockUnavailableError(
            f"BaoStock login failed with error_code={code or 'missing'}"
            + (f": {message}" if message else "")
        )


def call_baostock_query(
    query: Callable[[], T],
    login: Callable[[], object],
    *,
    operation: str,
    max_attempts: int = 3,
    deadline_seconds: float = 8.0,
    base_delay_seconds: float = 0.2,
    max_delay_seconds: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Run an SDK query with finite re-login attempts and a total deadline.

    Authentication/session error codes are retried after a re-login.  SDK
    exceptions are treated as transient because this callback contains only the
    external SDK invocation.  Other protocol error codes fail immediately.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if deadline_seconds <= 0:
        raise ValueError("deadline_seconds must be positive")
    if base_delay_seconds < 0 or max_delay_seconds < 0:
        raise ValueError("retry delays must not be negative")

    started = clock()
    attempts = 0
    last_error = "unknown failure"

    while attempts < max_attempts:
        elapsed = clock() - started
        if elapsed >= deadline_seconds:
            break
        attempts += 1

        try:
            result = query()
        except Exception as exc:  # vendor SDK boundary
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            code, message = _result_detail(result)
            if code == "0":
                return result
            last_error = f"error_code={code or 'missing'}"
            if message:
                last_error += f": {message}"
            if code not in AUTH_ERROR_CODES:
                raise BaostockQueryError(f"{operation} failed: {last_error}")

        if attempts >= max_attempts:
            break

        try:
            login_result = login()
            login_code, login_message = _result_detail(login_result)
            if login_code != "0":
                last_error = f"re-login error_code={login_code or 'missing'}"
                if login_message:
                    last_error += f": {login_message}"
        except Exception as exc:  # vendor SDK boundary
            last_error = f"re-login {type(exc).__name__}: {exc}"

        remaining = deadline_seconds - (clock() - started)
        if remaining <= 0:
            break
        delay = min(
            base_delay_seconds * (2 ** (attempts - 1)),
            max_delay_seconds,
            remaining,
        )
        if delay > 0:
            sleeper(delay)

    raise BaostockUnavailableError(
        f"{operation} unavailable after {attempts} attempt(s): {last_error}"
    )


def parse_baostock_datetime(
    date_value: object,
    time_value: object | None = None,
) -> datetime:
    """Parse BaoStock's source timestamp without reconstructing bars by row.

    Daily/weekly/monthly rows only have ``YYYY-MM-DD`` and are represented at
    the 15:00 market close, preserving the adapter's existing convention.
    Minute rows have an exchange timestamp formatted as
    ``YYYYMMDDHHMMSSsss`` (milliseconds); 14-digit second precision is also
    accepted for compatibility with older responses.
    """

    date_text = str(date_value).strip()
    try:
        source_date = date.fromisoformat(date_text)
    except ValueError as exc:
        raise ValueError(f"invalid BaoStock date: {date_text!r}") from exc

    if time_value is None:
        return datetime.combine(source_date, datetime_time(hour=15))

    time_text = str(time_value).strip()
    if not time_text:
        raise ValueError("BaoStock minute row is missing its source time")
    if not time_text.isdigit() or len(time_text) not in {14, 17}:
        raise ValueError(f"invalid BaoStock minute time: {time_text!r}")

    fmt = "%Y%m%d%H%M%S%f" if len(time_text) == 17 else "%Y%m%d%H%M%S"
    try:
        parsed = datetime.strptime(time_text, fmt)
    except ValueError as exc:
        raise ValueError(f"invalid BaoStock minute time: {time_text!r}") from exc
    if parsed.date() != source_date:
        raise ValueError(
            "BaoStock date/time mismatch: "
            f"date={date_text!r}, time={time_text!r}"
        )
    return parsed


def recent_weekdays(as_of: date, *, lookback_days: int = 20) -> list[date]:
    """Return a finite newest-first fallback list for catalog discovery."""

    if lookback_days < 1:
        raise ValueError("lookback_days must be at least 1")
    candidates: list[date] = []
    for offset in range(lookback_days + 1):
        candidate = as_of - timedelta(days=offset)
        if candidate.weekday() < 5:
            candidates.append(candidate)
    return candidates
