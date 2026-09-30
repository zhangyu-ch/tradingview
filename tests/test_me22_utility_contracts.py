from __future__ import annotations

import datetime as dt
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tradingview_zy import fun

ROOT = Path(__file__).resolve().parents[1]


def test_timestamp_helpers_are_explicit_and_host_independent() -> None:
    assert fun.str_to_timeint(
        "1970-01-01 08:00:00", tz="Asia/Shanghai"
    ) == 0
    assert fun.timeint_to_str(
        0, "%Y-%m-%d %H:%M:%S", tz="Asia/Shanghai"
    ) == "1970-01-01 08:00:00"
    assert fun.timeint_to_str(
        0, "%Y-%m-%d %H:%M:%S", tz="UTC"
    ) == "1970-01-01 00:00:00"
    assert fun.timeint_to_datetime(0, tz="UTC").tzinfo is not None


def test_naive_epoch_conversion_requires_explicit_timezone() -> None:
    naive = dt.datetime(1970, 1, 1, 8, 0, 0)
    with pytest.raises(ValueError, match="explicit assume_tz"):
        fun.datetime_to_int(naive)
    assert fun.datetime_to_int(naive, assume_tz="Asia/Shanghai") == 0
    assert fun.datetime_to_int(dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)) == 0


def test_dst_ambiguous_and_nonexistent_wall_times_fail_closed() -> None:
    with pytest.raises(ValueError, match="nonexistent"):
        fun.str_to_datetime(
            "2026-03-08 02:30:00", tz="America/New_York"
        )
    with pytest.raises(ValueError, match="ambiguous"):
        fun.str_to_datetime(
            "2026-11-01 01:30:00", tz="America/New_York"
        )

    first = fun.str_to_datetime(
        "2026-11-01 01:30:00", tz="America/New_York", fold=0
    )
    second = fun.str_to_datetime(
        "2026-11-01 01:30:00", tz="America/New_York", fold=1
    )
    assert int(second.timestamp() - first.timestamp()) == 3600


def test_string_arithmetic_does_not_use_mktime_or_localtime() -> None:
    assert fun.str_add_seconds_to_str(
        "2026-01-01 00:00:00", 90, tz="Asia/Shanghai"
    ) == "2026-01-01 00:01:30"
    source = (ROOT / "src/tradingview_zy/fun.py").read_text(encoding="utf-8")
    assert "time.localtime" not in source
    assert "time.mktime" not in source
    assert "get_localzone" not in source


def test_singleton_is_published_once_under_concurrent_first_use() -> None:
    counter = 0
    counter_lock = threading.Lock()

    @fun.singleton
    class Resource:
        def __init__(self) -> None:
            nonlocal counter
            time.sleep(0.01)
            with counter_lock:
                counter += 1

    with ThreadPoolExecutor(max_workers=24) as pool:
        values = list(pool.map(lambda _n: Resource(), range(72)))

    assert counter == 1
    assert len({id(value) for value in values}) == 1


def test_singleton_does_not_cache_failed_construction_and_can_reset() -> None:
    attempts = 0

    @fun.singleton
    class Flaky:
        def __init__(self) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("first construction failed")

    with pytest.raises(RuntimeError):
        Flaky()
    first = Flaky()
    second = Flaky()
    assert first is second
    assert attempts == 2

    Flaky.reset_instance()
    third = Flaky()
    assert third is not first
    assert attempts == 3
