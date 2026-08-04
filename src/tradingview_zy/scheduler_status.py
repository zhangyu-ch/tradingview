"""Persisted, fail-closed status snapshots for the external scheduler process.

The Web application must not own an APScheduler instance.  It only reads the
last snapshot written by the dedicated scheduler runner.  The underlying cache
is the schema-validated, atomic JSON cache from :mod:`tradingview_zy.file_db`;
imports are deliberately lazy so this small boundary can be tested without
constructing the project's database or file-cache globals.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

_STATUS_FIELDS = ("id", "name", "update_dt", "next_run_dt", "state")
_DEFAULT_STATUS = {
    "name": "--",
    "update_dt": "--",
    "next_run_dt": "--",
    "state": "未知",
}
_MAX_STATUS_TEXT = 512


def _status_text(value: Any, *, default: str = "--") -> str:
    if value is None:
        return default
    text = str(value)
    if not text:
        return default
    # Status data is rendered into an authenticated operational page.  Keep the
    # persisted snapshot bounded even when a third-party scheduler supplies an
    # unexpectedly large job name or state string.
    return text[:_MAX_STATUS_TEXT]


def normalize_status_records(records: object) -> list[dict[str, str]]:
    """Validate, whitelist, deduplicate and stably order job-status records."""

    if not isinstance(records, (list, tuple)):
        raise ValueError("scheduler status must be a list")

    normalized: dict[str, dict[str, str]] = {}
    for raw in records:
        if not isinstance(raw, Mapping):
            raise ValueError("scheduler status entries must be mappings")
        job_id = _status_text(raw.get("id"), default="")
        if not job_id:
            raise ValueError("scheduler status id must be non-empty")
        item = {
            "id": job_id,
            "name": _status_text(raw.get("name"), default=_DEFAULT_STATUS["name"]),
            "update_dt": _status_text(
                raw.get("update_dt"), default=_DEFAULT_STATUS["update_dt"]
            ),
            "next_run_dt": _status_text(
                raw.get("next_run_dt"), default=_DEFAULT_STATUS["next_run_dt"]
            ),
            "state": _status_text(raw.get("state"), default=_DEFAULT_STATUS["state"]),
        }
        # A single snapshot has one authoritative record per APScheduler job id.
        # Last writer wins, then output is sorted for deterministic rendering.
        normalized[job_id] = item

    return [normalized[job_id] for job_id in sorted(normalized)]


class SchedulerStatusStore:
    """Read and write scheduler snapshots through the safe atomic state cache."""

    def __init__(self, cache=None, filename: str = "scheduler_jobs") -> None:
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("scheduler status filename must be non-empty")
        self._cache = cache
        self.filename = filename.strip()
        self.log = logging.getLogger(__name__)

    def _resolve_cache(self):
        if self._cache is None:
            from tradingview_zy.file_db import fdb

            self._cache = fdb
        return self._cache

    def read(self) -> list[dict[str, str]]:
        """Return a validated snapshot, or an empty list when unavailable/corrupt."""

        try:
            raw = self._resolve_cache().cache_pkl_from_file(self.filename)
            if raw is None:
                return []
            return normalize_status_records(raw)
        except Exception as exc:  # The Web status page must remain fail-closed.
            self.log.warning("scheduler status snapshot unavailable: %s", exc)
            return []

    def write(self, records: Iterable[Mapping[str, Any]]) -> bool:
        snapshot = normalize_status_records(list(records))
        result = self._resolve_cache().cache_pkl_to_file(self.filename, snapshot)
        return result is True


__all__ = ["SchedulerStatusStore", "normalize_status_records"]
