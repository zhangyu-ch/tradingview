from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta
from typing import Any

DEFAULT_NODE_CACHE_TTL_SECONDS = 6 * 60 * 60


class NodeSelectionError(RuntimeError):
    """No healthy TDX node was observed inside the selection deadline."""


Probe = Callable[[str, int, str], timedelta]


def cache_expiry_epoch(
    ttl_seconds: int = DEFAULT_NODE_CACHE_TTL_SECONDS,
    *,
    wall_clock: Callable[[], float] = time.time,
) -> int:
    """Return an absolute cache expiry so selected nodes are periodically revalidated."""
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")
    return int(wall_clock()) + ttl_seconds


def select_fastest_node(
    candidates: Sequence[Mapping[str, Any]],
    *,
    node_type: str,
    probe: Probe,
    deadline_seconds: float = 3.0,
    max_workers: int = 16,
    minimum_successes: int = 1,
    healthy_latency_limit: timedelta = timedelta(seconds=9),
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Probe TDX candidates concurrently under one wall-clock budget.

    Workers are daemon threads so a provider probe that violates its own socket timeout
    cannot hold the caller or process shutdown hostage. The stop event prevents workers
    from starting additional probes after the caller's deadline. Results completed before
    the deadline are ranked by measured latency; malformed or failed probes are ignored.
    """
    if deadline_seconds <= 0:
        raise ValueError("deadline_seconds must be positive")
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")
    if minimum_successes < 1:
        raise ValueError("minimum_successes must be at least 1")
    if not candidates:
        raise NodeSelectionError(f"no {node_type} TDX candidates configured")

    tasks: queue.Queue[tuple[int, Mapping[str, Any]]] = queue.Queue()
    results: queue.Queue[tuple[int, Mapping[str, Any], timedelta | None]] = queue.Queue()
    stop = threading.Event()

    for index, candidate in enumerate(candidates):
        tasks.put((index, candidate))

    def worker() -> None:
        while not stop.is_set():
            try:
                index, candidate = tasks.get_nowait()
            except queue.Empty:
                return
            if stop.is_set():
                tasks.task_done()
                return

            latency: timedelta | None = None
            try:
                measured = probe(str(candidate["ip"]), int(candidate["port"]), node_type)
                if isinstance(measured, timedelta):
                    latency = measured
            except Exception:
                # A single broken node must not abort the whole selection batch.
                latency = None
            finally:
                results.put((index, candidate, latency))
                tasks.task_done()

    worker_count = min(max_workers, len(candidates))
    threads = [
        threading.Thread(
            target=worker,
            name=f"tdx-node-probe-{node_type}-{number + 1}",
            daemon=True,
        )
        for number in range(worker_count)
    ]

    started = clock()
    deadline = started + deadline_seconds
    for thread in threads:
        thread.start()

    completed = 0
    healthy: list[tuple[timedelta, int, Mapping[str, Any]]] = []
    while completed < len(candidates):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        try:
            index, candidate, latency = results.get(timeout=remaining)
        except queue.Empty:
            break
        completed += 1
        if latency is not None and timedelta(0) <= latency < healthy_latency_limit:
            healthy.append((latency, index, candidate))

    stop.set()

    if len(healthy) < minimum_successes:
        elapsed = max(0.0, clock() - started)
        raise NodeSelectionError(
            f"found {len(healthy)} healthy {node_type} TDX nodes; "
            f"required {minimum_successes} within {deadline_seconds:.2f}s "
            f"(completed {completed}/{len(candidates)}, elapsed {elapsed:.2f}s)"
        )

    _, _, best = min(healthy, key=lambda item: (item[0], item[1]))
    return dict(best)
