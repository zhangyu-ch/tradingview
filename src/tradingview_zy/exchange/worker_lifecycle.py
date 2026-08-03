from __future__ import annotations

import threading
from collections.abc import Callable


class ManagedWorker:
    """Small, deterministic lifecycle wrapper for one daemon worker thread."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.stop_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None

    @property
    def thread(self) -> threading.Thread | None:
        with self._lock:
            return self._thread

    @property
    def running(self) -> bool:
        thread = self.thread
        return bool(thread and thread.is_alive())

    def start(self, target: Callable[[], object]) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self.stop_event.clear()
            self._thread = threading.Thread(
                target=target,
                name=self.name,
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self, timeout: float = 5.0) -> bool:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.stop_event.set()
        thread = self.thread
        if thread is None:
            return False
        if thread is threading.current_thread():
            return False
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise TimeoutError(f"worker {self.name!r} did not stop within {timeout}s")
        with self._lock:
            if self._thread is thread:
                self._thread = None
        return True

    def wait(self, timeout: float) -> bool:
        """Wait for stop; returns True when shutdown was requested."""
        return self.stop_event.wait(timeout=max(0.0, timeout))
