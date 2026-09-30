"""Bounded OHLCV transport shared by Binance spot and futures adapters."""
from __future__ import annotations

import time

import ccxt

from tradingview_zy.exchange.tdx_reliability import (
    ProviderUnavailableError,
    call_with_bounded_retry,
)
from tradingview_zy.sync_batch import DeadlineCaller, SyncCallBusyError, SyncCallTimeoutError


_ohlcv_calls = DeadlineCaller(max_concurrent=2)


def fetch_ohlcv_with_retry(exchange, lock, *, deadline: float, **request):
    """Retry only NetworkError, sharing the caller's budget across all pages.

    The lock prevents concurrent OHLCV requests changing the shared SDK timeout.
    SDK retry is disabled when the adapters construct their CCXT client.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProviderUnavailableError("Binance OHLCV deadline exceeded")

    def request_with_timeout(budget):
        started = time.monotonic()
        if not lock.acquire(timeout=budget):
            raise TimeoutError("Binance OHLCV request queue timed out")
        old_timeout = exchange.timeout
        try:
            budget -= time.monotonic() - started
            if budget <= 0:
                raise TimeoutError("Binance OHLCV deadline exceeded")
            exchange.timeout = max(1, min(int(budget * 1000), 4000))
            return exchange.fetch_ohlcv(**request)
        finally:
            exchange.timeout = old_timeout
            lock.release()

    def operation(budget):
        try:
            return _ohlcv_calls.call(
                request_with_timeout, budget, timeout_seconds=budget,
            )
        except (SyncCallBusyError, SyncCallTimeoutError) as error:
            raise ProviderUnavailableError("Binance OHLCV unavailable or timed out") from error

    return call_with_bounded_retry(
        operation,
        retry_on=(ccxt.NetworkError,),
        max_attempts=3,
        deadline_seconds=remaining,
        description="Binance OHLCV",
    )
