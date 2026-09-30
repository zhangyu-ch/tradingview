"""A bounded shared boundary for AkShare adjustment-factor HTTP requests."""
from __future__ import annotations

from tradingview_zy.exchange.tdx_reliability import remaining_request_seconds

from requests.exceptions import ConnectionError as HttpConnectionError, Timeout

from tradingview_zy.domain import ProviderUnavailableError
from tradingview_zy.sync_batch import (
    DeadlineCaller,
    SyncBatchDeadlineError,
    SyncCallBusyError,
    SyncCallTimeoutError,
)

# Timed-out work keeps its slot until it really exits; never one pool per call.
_factor_calls = DeadlineCaller(max_concurrent=2)


def fetch_adjustment_factors(function, *, deadline: float, provider: str, **kwargs):
    try:
        return _factor_calls.call(
            function,
            timeout_seconds=remaining_request_seconds(deadline),
            **kwargs,
        )
    except (SyncCallTimeoutError, SyncCallBusyError, SyncBatchDeadlineError,
            HttpConnectionError, Timeout, TimeoutError) as error:
        raise ProviderUnavailableError(
            "复权因子数据源不可用或超时", provider=provider,
        ) from error
