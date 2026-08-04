from __future__ import annotations

import threading
import time

import pytest

from test_support.web_routes import route_source

from tradingview_zy.tick_request import (
    BoundedProviderCaller,
    SlidingWindowLimiter,
    TickProviderBusyError,
    TickProviderCallError,
    TickProviderTimeoutError,
    TickRateLimitError,
    TickRequestError,
    parse_tick_request,
)


@pytest.mark.parametrize(
    "codes",
    ["not-json", "{}", "[]", '["ok", 3]', '[" "]', '["bad\\ncode"]'],
)
def test_parse_tick_request_rejects_invalid_codes(codes):
    with pytest.raises(TickRequestError):
        parse_tick_request(
            "a", codes, allowed_markets={"a"}, max_codes=3, max_code_bytes=12
        )


def test_parse_tick_request_rejects_unknown_market_before_provider_use():
    with pytest.raises(TickRequestError):
        parse_tick_request(
            "unknown", '["SH.000001"]', allowed_markets={"a"}, max_codes=3, max_code_bytes=32
        )


def test_parse_tick_request_enforces_raw_count_before_deduplication():
    with pytest.raises(TickRequestError):
        parse_tick_request(
            "a", '["x", "x", "x", "x"]', allowed_markets={"a"}, max_codes=3, max_code_bytes=8
        )


def test_parse_tick_request_enforces_utf8_byte_limit():
    with pytest.raises(TickRequestError):
        parse_tick_request(
            "a", '["中中"]', allowed_markets={"a"}, max_codes=3, max_code_bytes=5
        )


def test_parse_tick_request_trims_and_stably_deduplicates():
    parsed = parse_tick_request(
        " A ", '[" SH.000001 ", "SZ.000002", "SH.000001"]',
        allowed_markets={"a"}, max_codes=5, max_code_bytes=32,
    )
    assert parsed.market == "a"
    assert parsed.codes == ("SH.000001", "SZ.000002")


def test_sliding_window_limiter_rejects_excess_and_recovers():
    limiter = SlidingWindowLimiter(max_requests=2, window_seconds=10, max_keys=3)
    limiter.check("client", now=1)
    limiter.check("client", now=2)
    with pytest.raises(TickRateLimitError):
        limiter.check("client", now=3)
    limiter.check("client", now=12.1)


def test_sliding_window_limiter_bounds_key_directory():
    limiter = SlidingWindowLimiter(max_requests=1, window_seconds=10, max_keys=2)
    limiter.check("a", now=1)
    limiter.check("b", now=1)
    limiter.check("c", now=1)
    assert limiter.key_count == 2


def test_sliding_window_limiter_is_thread_safe():
    limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60, max_keys=10)
    barrier = threading.Barrier(20)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def attempt() -> None:
        barrier.wait()
        try:
            limiter.check("same-client", now=1)
            allowed = True
        except TickRateLimitError:
            allowed = False
        with lock:
            outcomes.append(allowed)

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(outcomes) == 5


def test_bounded_provider_caller_returns_result_and_wraps_error():
    caller = BoundedProviderCaller(max_concurrent=1, timeout_seconds=0.2)
    assert caller.call(lambda x: x + 1, 2) == 3
    with pytest.raises(TickProviderCallError):
        caller.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))


def test_bounded_provider_caller_times_out_and_fails_busy_until_worker_exits():
    gate = threading.Event()
    caller = BoundedProviderCaller(max_concurrent=1, timeout_seconds=0.02)

    with pytest.raises(TickProviderTimeoutError):
        caller.call(lambda: gate.wait(1))
    with pytest.raises(TickProviderBusyError):
        caller.call(lambda: None)
    gate.set()
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        try:
            assert caller.call(lambda: "recovered") == "recovered"
            break
        except TickProviderBusyError:
            time.sleep(0.01)
    else:
        raise AssertionError("provider slot did not recover")


def test_web_route_uses_tick_contract_before_provider_call():
    route = route_source("ticks")
    assert route.index("parse_tick_request") < route.index("services.get_exchange")
    assert "services.tick_provider_caller.call(ex.ticks" in route
    assert "TickRateLimitError" in route
    assert "TickProviderTimeoutError" in route
