"""Shared raw-window pagination; SDK, persistence and market rules stay outside."""

import hashlib
import json
import logging
from typing import Callable, Optional

import pandas as pd


_LOG = logging.getLogger(__name__)


def tdx_cache_key(market: str, code: str, frequency: str) -> str:
    """Version the raw semantics, independently of FileCacheDB's sidecar schema."""
    identity = json.dumps([market, code, frequency], ensure_ascii=False).encode("utf-8")
    # Hashing also avoids FileCacheDB's dot/underscore filename collisions.
    return "tdx_raw_v2_" + hashlib.sha256(identity).hexdigest()


def refresh_tdx_window(
    cached: Optional[pd.DataFrame],
    fetch_page: Callable[[int], pd.DataFrame],
    normalize_page: Callable[[pd.DataFrame], pd.DataFrame],
    max_pages: int,
) -> pd.DataFrame:
    """Fetch zero-based pages until the ORIGINAL cache tail is covered.

    Empty pages terminate normally; exceptions propagate without returning partial
    data. Later fetched rows win ties, including ties with cached rows. If the
    bounded new window cannot reach the old tail, never bridge the missing range.
    Inputs are not mutated. Consecutive SDK offsets define the fetched window;
    this helper does not infer exchange calendars or fill missing bars.
    """
    if max_pages < 1:
        raise ValueError("max_pages must be positive")
    cache_end = None if cached is None or cached.empty else cached["date"].max()
    pages = []
    connected = False
    window_start = window_end = None
    for page_index in range(max_pages):
        page = fetch_page(page_index)
        if page.empty:
            break
        page = normalize_page(page.copy())
        if page.empty:
            break
        pages.append(page)
        start, end = page["date"].min(), page["date"].max()
        window_start = start if window_start is None else min(window_start, start)
        window_end = end if window_end is None else max(window_end, end)
        if cache_end is not None and window_start <= cache_end <= window_end:
            connected = True
            break

    if not pages:
        return pd.DataFrame()
    if connected:
        pages.insert(0, cached)
    elif cache_end is not None:
        _LOG.warning(
            "TDX raw cache tail %s not reached; retaining fetched window %s to %s only",
            cache_end, window_start, window_end,
        )
    return (
        pd.concat(pages, ignore_index=True)
        .drop_duplicates("date", keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
