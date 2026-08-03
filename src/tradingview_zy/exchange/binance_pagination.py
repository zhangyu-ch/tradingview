from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
from typing import Any


class PaginationStalledError(RuntimeError):
    """The upstream API did not advance the requested time cursor."""


def latest_cached_datetime(frame: Any) -> str | None:
    """Return a safe cache resume point for 0/1/N-row DataFrames."""
    if frame is None or len(frame) == 0:
        return None
    if "date" not in frame.columns:
        raise ValueError("cached K-lines are missing the date column")
    value = frame["date"].max()
    if value is None:
        return None
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if not isinstance(value, dt.datetime):
        raise ValueError(f"unsupported cached date value: {value!r}")
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _validated_page(page: Sequence[Sequence[Any]] | None) -> list[list[Any]]:
    if page is None:
        return []
    validated: list[list[Any]] = []
    for row in page:
        if len(row) < 6:
            raise ValueError(f"invalid OHLCV row: {row!r}")
        try:
            timestamp = int(row[0])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid OHLCV timestamp: {row[0]!r}") from exc
        normalized = list(row[:6])
        normalized[0] = timestamp
        validated.append(normalized)
    validated.sort(key=lambda item: item[0])
    return validated


def paginate_ohlcv(
    fetch_page: Callable[[dict[str, int]], Sequence[Sequence[Any]] | None],
    *,
    start_ms: int | None,
    page_limit: int = 1000,
    target_count: int = 10000,
    max_pages: int = 100,
) -> list[list[Any]]:
    """Fetch Binance-style inclusive OHLCV pages with strict cursor progress.

    With ``start_ms`` the cursor moves forward to ``last_timestamp + 1``.
    Without it, pages are collected backwards using ``first_timestamp - 1``.
    Timestamps are deduplicated and sorted before returning.
    """
    if page_limit < 1 or target_count < 1 or max_pages < 1:
        raise ValueError("page_limit, target_count and max_pages must be positive")

    rows_by_timestamp: dict[int, list[Any]] = {}
    forward = start_ms is not None
    cursor = int(start_ms) if start_ms is not None else None

    for _page_number in range(max_pages):
        params: dict[str, int] = {}
        if cursor is not None:
            params["startTime" if forward else "endTime"] = cursor

        page = _validated_page(fetch_page(params))
        if not page:
            break
        for row in page:
            rows_by_timestamp[row[0]] = row

        if len(page) < page_limit:
            break

        if forward:
            next_cursor = page[-1][0] + 1
            if cursor is not None and next_cursor <= cursor:
                raise PaginationStalledError(
                    f"forward cursor did not advance: {cursor} -> {next_cursor}"
                )
        else:
            next_cursor = page[0][0] - 1
            if cursor is not None and next_cursor >= cursor:
                raise PaginationStalledError(
                    f"backward cursor did not retreat: {cursor} -> {next_cursor}"
                )
        cursor = next_cursor

        if not forward and len(rows_by_timestamp) >= target_count:
            break
    else:
        raise PaginationStalledError(f"pagination exceeded max_pages={max_pages}")

    result = [rows_by_timestamp[key] for key in sorted(rows_by_timestamp)]
    if not forward and len(result) > target_count:
        result = result[-target_count:]
    return result
