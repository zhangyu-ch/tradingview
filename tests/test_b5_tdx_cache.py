"""Offline B5 contracts: execute real adapter methods without private config/DB."""
from __future__ import annotations

import ast
import datetime
from enum import Enum
from types import SimpleNamespace

import pandas as pd
import pytest

from test_b18_kline_reliability import (
    SRC, FakeClient, FakeClock, FakeConnectionError, InvalidRequestError,
    _load_helper, reliability,
)
from tradingview_zy.exchange.tdx_cache import refresh_tdx_window, tdx_cache_key


TARGETS = [
    ("exchange_tdx", "A", 8),
    ("exchange_tdx_hk", "HK", 8),
    ("exchange_tdx_us", "US", 5),
    ("exchange_tdx_futures", "FUTURES", 8),
    ("exchange_tdx_fx", "FX", 10),
    ("exchange_tdx_ny_futures", "NY_FUTURES", 8),
]
MARKETS = Enum("Market", {market: market.lower() for _, market, _ in TARGETS})


def frame(values, *, price=1):
    dates = [pd.Timestamp("2026-08-03 10:00") + pd.Timedelta(minutes=i) for i in values]
    return pd.DataFrame({
        "datetime": [d.strftime("%Y-%m-%d %H:%M:%S") for d in dates],
        "date": dates, "open": price, "close": price, "high": price,
        "low": price, "vol": 10, "amount": 20, "trade": 30,
    })


def refresh(cached, pages, limit=8):
    calls = []

    def fetch(index):
        calls.append(index)
        page = pages[index] if index < len(pages) else pd.DataFrame()
        if isinstance(page, Exception):
            raise page
        return page

    return refresh_tdx_window(cached, fetch, lambda page: page, limit), calls


def test_fixed_tail_multi_page_overlap_sort_deduplicate_and_fresh_rows_win():
    cached = frame([2, 0, 1, 2], price=0)
    original = cached.copy(deep=True)
    pages = [frame([8, 7, 8]), frame([6, 5]), frame([4, 3]), frame([2, 1], price=9)]
    result, calls = refresh(cached, pages)
    assert calls == [0, 1, 2, 3]
    assert result.date.tolist() == frame(range(9)).date.tolist()
    assert result.close.tolist()[:3] == [0, 9, 9]
    pd.testing.assert_frame_equal(cached, original)
    assert len(pages[0]) == 3


@pytest.mark.parametrize("cached", [None, pd.DataFrame(), frame([0])])
def test_first_empty_never_normalizes_or_returns_old_history(cached):
    def unexpected(page):
        pytest.fail("empty response must not be normalized")
    result = refresh_tdx_window(cached, lambda index: pd.DataFrame(), unexpected, 8)
    assert result.empty


@pytest.mark.parametrize("limit,pages", [(2, [frame([8, 9]), frame([6, 7])]),
                                         (8, [frame([8, 9]), pd.DataFrame()])])
def test_disconnected_old_cache_is_not_bridged(limit, pages, caplog):
    result, calls = refresh(frame([0, 1]), pages, limit)
    assert result.date.min() == pages[-1 if limit == 2 else 0].date.min()
    assert len(calls) == 2
    assert "not reached" in caplog.text


def test_cache_ahead_of_server_is_not_treated_as_overlap():
    result, calls = refresh(frame([100, 101]), [frame([1, 2])])
    assert result.date.tolist() == frame([1, 2]).date.tolist()
    assert len(calls) == 2


def test_later_fetch_wins_page_ties_and_failure_propagates():
    result, _ = refresh(None, [frame([1, 2]), frame([0, 1], price=9)])
    assert result.close.tolist() == [9, 9, 1]
    with pytest.raises(TimeoutError, match="page failed"):
        refresh(frame([0]), [frame([8]), TimeoutError("page failed")])


def test_key_versions_market_code_and_frequency_without_filename_collisions():
    keys = {tdx_cache_key(m.value, code, frequency)
            for m in MARKETS for code in ["S.X", "S_X"] for frequency in ["1m", "d"]}
    assert len(keys) == 24
    assert all(key.startswith("tdx_raw_v2_") and "." not in key for key in keys)


class MemoryCache:
    def __init__(self, cached=None):
        self.cached = cached
        self.reads, self.writes = [], []

    def get_tdx_klines(self, *key):
        self.reads.append(key)
        return None if self.cached is None else self.cached.copy(deep=True)

    def save_tdx_klines(self, *args):
        self.writes.append((*args[:3], args[3].copy(deep=True)))
        self.cached = args[3].copy(deep=True)
        return True


def adapter(target, pages, cache=None, *, seconds_per_page=0):
    name, market, _ = target
    tree = ast.parse((SRC / f"{name}.py").read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "klines")
    clock, clients, budgets = FakeClock(), [], []
    cache = cache if cache is not None else MemoryCache()

    class Client(FakeClient):
        def get_instrument_bars(self, category, sdk_market, code, offset, count):
            assert count == 700 and offset % 700 == 0
            self.calls += 1
            self.offsets.append(offset)
            self.client.send(b"page")  # real B18 deadline guard, no network
            clock.now += seconds_per_page
            index = offset // 700
            page = pages[index] if index < len(pages) else pd.DataFrame()
            if isinstance(page, Exception):
                raise page
            return page.copy(deep=True)

        get_security_bars = get_instrument_bars
        get_index_bars = get_instrument_bars

    def factory(**options):
        assert not options.get("auto_retry", False)
        client = Client()
        client.offsets = []
        clients.append(client)
        return client

    def retry(operation, **options):
        budgets.append(options)
        return reliability.call_with_bounded_retry(
            operation, **options, clock=clock, sleeper=clock.sleep,
            base_delay_seconds=0, max_delay_seconds=0,
        )

    namespace = {
        "pd": pd, "datetime": datetime, "time": SimpleNamespace(monotonic=clock),
        "Market": MARKETS, "InvalidRequestError": InvalidRequestError,
        "TdxConnectionError": FakeConnectionError, "NodeSelectionError": FakeConnectionError,
        "TdxHq_API": factory, "refresh_tdx_window": refresh_tdx_window,
        "tdx_cache_key": tdx_cache_key, "call_with_bounded_retry": retry,
        "remaining_request_seconds": lambda deadline: deadline - clock(),
        "tdx_kline_connection": lambda client, info, remaining: reliability.tdx_kline_connection(
            client, info, remaining, clock=clock),
        "normalize_tdx_us_bars": _load_helper("b5_us", SRC / "tdx_us_payloads.py").normalize_tdx_us_bars,
        "convert_stock_kline_frequency": lambda data, frequency: data,
    }
    # The real night-session methods are safe to execute independently as well.
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == "fix_yp_date":
            namespace["fun"] = SimpleNamespace(
                str_to_datetime=lambda value, fmt: datetime.datetime.strptime(value, fmt),
                datetime_to_str=lambda value: value.strftime("%Y-%m-%d %H:%M:%S"),
            )
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC / f"{name}.py"), "exec"), namespace)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SRC / f"{name}.py"), "exec"), namespace)
    provider = SimpleNamespace(
        _new_tdx_client=factory, connect_info={"ip": "test.invalid", "port": 7709},
        reset_tdx_ip=lambda **kwargs: None,
        to_tdx_code=lambda code: (1, "TEST", "stock_cn") if market == "A" else (1, "TEST"),
        fdb=cache, tz=__import__("pytz").timezone("Asia/Shanghai"),
        fix_yp_date=namespace.get("fix_yp_date"),
        klines_qfq=lambda code, data, **kwargs: data,
        klines_fq=lambda data, *args: data, xdxr=lambda *args: pd.DataFrame(),
    )
    provider.__convert_date = lambda date: date
    invoke = lambda frequency="1m", **kwargs: namespace["klines"](provider, "TEST.CODE", frequency, **kwargs)
    return SimpleNamespace(invoke=invoke, clients=clients, cache=cache, budgets=budgets, clock=clock)


@pytest.mark.parametrize("target", TARGETS)
def test_six_adapters_catch_up_after_more_than_two_pages_and_same_key(target):
    run = adapter(target, [frame([8, 7]), frame([6, 5]), frame([4, 3]), frame([2, 1], price=9)], MemoryCache(frame([0, 1, 2], price=0)))
    output = run.invoke()
    assert len(output) == 9
    assert run.clients[0].offsets == [0, 700, 1400, 2100]
    key = (target[1].lower(), tdx_cache_key(target[1].lower(), "TEST.CODE", "1m"), "1m")
    assert run.cache.reads == [key]
    assert run.cache.writes[0][:3] == key
    raw = run.cache.writes[0][3]
    assert raw.date.is_unique and raw.date.is_monotonic_increasing
    assert raw.close.tolist()[:3] == [0, 9, 9]
    assert run.budgets[0]["max_attempts"] == 3
    assert run.budgets[0]["deadline_seconds"] == 12
    assert run.clients[0].closed and not run.clients[0].auto_retry


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("cached,frequency,options", [
    (None, "1m", {}), ("empty", "1m", {}), ("old", "1m", {}),
    (None, "d", {"pages": 1}),
])
def test_six_adapters_empty_first_page_preserves_cache(target, cached, frequency, options):
    cache = MemoryCache(None if cached is None else pd.DataFrame() if cached == "empty" else frame([0]))
    original = None if cache.cached is None else cache.cached.copy(deep=True)
    run = adapter(target, [], cache)
    args = options.copy()
    assert run.invoke(frequency=frequency, args=args).empty
    assert len(run.clients) == 1
    assert run.clients[0].calls == 1 and run.clients[0].closed
    assert run.clients[0].offsets == [0]
    assert args == options
    assert not cache.writes
    if original is None:
        assert cache.cached is None
    else:
        pd.testing.assert_frame_equal(cache.cached, original)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("empty_tail", [False, True])
def test_six_adapters_disconnected_window_and_default_page_limits(target, empty_tail):
    count = 2 if empty_tail else target[2]
    pages = [frame([100 - i]) for i in range(count)]
    run = adapter(target, pages, MemoryCache(frame([0, 1])))
    output = run.invoke()
    assert len(output) == count
    assert len(run.clients[0].offsets) == count + int(empty_tail)
    assert len(run.cache.writes[0][3]) == count


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("error", [TimeoutError("page failed"), KeyError("malformed")])
def test_six_adapters_partial_failure_never_writes_and_preserves_retry_budget(target, error):
    cache = MemoryCache(frame([0]))
    run = adapter(target, [frame([9]), error], cache)
    expected = reliability.ProviderUnavailableError if isinstance(error, TimeoutError) else KeyError
    with pytest.raises(expected):
        run.invoke()
    assert len(run.clients) == (3 if isinstance(error, TimeoutError) else 1)
    assert all(client.closed and client.offsets == [0, 700] for client in run.clients)
    assert not cache.writes
    pd.testing.assert_frame_equal(cache.cached, frame([0]))


@pytest.mark.parametrize("target", TARGETS)
def test_six_adapters_all_pages_keep_one_twelve_second_deadline(target):
    run = adapter(target, [frame([100 - i]) for i in range(10)], seconds_per_page=4)
    with pytest.raises(reliability.ProviderUnavailableError):
        run.invoke()
    assert run.clock.now == 12
    assert len(run.clients) == 1
    assert not run.cache.writes


def test_a_week_still_requests_twelve_pages_and_raw_1300_is_not_return_1130():
    run = adapter(TARGETS[0], [frame([i]) for i in range(12)])
    run.invoke(frequency="w")
    assert len(run.clients[0].offsets) == 12
    page = frame([179, 180, 181])
    run = adapter(TARGETS[0], [page])
    output = run.invoke()
    assert datetime.time(11, 30) in output.date.dt.time.tolist()
    assert datetime.time(13, 0) in run.cache.cached.date.dt.time.tolist()
    run.invoke()
    assert run.clients[-1].offsets == [0]
    assert run.cache.cached.date.tolist() == page.date.tolist()


@pytest.mark.parametrize("target,hour,expected_day", [(TARGETS[3], 21, 2), (TARGETS[5], 2, 4)])
def test_night_session_normalization_remains_in_adapter(target, hour, expected_day):
    page = frame([0])
    page["datetime"] = f"2026-08-03 {hour:02d}:00:00"
    run = adapter(target, [page])
    output = run.invoke()
    assert output.date.iloc[0].day == expected_day
    assert run.cache.cached.date.iloc[0].day == expected_day


@pytest.fixture
def file_cache(tmp_path):
    # Execute the actual FileCacheDB implementation with only application imports
    # replaced: never import private config, business DB or create real user data.
    path = SRC.parent / "file_db.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and (node.module or "").startswith("tradingview_zy")
    )]
    namespace = {"get_data_path": lambda: tmp_path, "Market": MARKETS,
                 "fun": SimpleNamespace(), "__name__": "b5_file_cache"}
    exec(compile(tree, str(path), "exec"), namespace)
    cache = namespace["FileCacheDB"]()
    # Existing probabilistic maintenance is not part of this migration test.
    cache.clear_tdx_old_klines = lambda market: True
    return cache


@pytest.mark.parametrize("target", TARGETS)
def test_real_filecache_drops_only_row_then_refills_new_key_without_touching_legacy(target, file_cache):
    market = target[1].lower()
    key = tdx_cache_key(market, "TEST.CODE", "1m")
    file_cache.save_tdx_klines(market, "TEST.CODE", "1m", frame([999]))
    legacy = file_cache._kline_path(market, "TEST.CODE", "1m")
    before = legacy.read_bytes()
    file_cache.save_tdx_klines(market, key, "1m", frame([0]))
    assert file_cache.get_tdx_klines(market, key, "1m").empty
    run = adapter(target, [frame([4, 3]), frame([2, 1])], file_cache)
    assert len(run.invoke()) == 4
    saved = file_cache.get_tdx_klines(market, key, "1m", include_incomplete=True)
    assert saved.date.tolist() == frame([1, 2, 3, 4]).date.tolist()
    assert len(file_cache.get_tdx_klines(market, key, "1m")) == 3
    assert legacy.read_bytes() == before


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("cached", [None, pd.DataFrame()])
def test_six_adapters_cold_cache_reads_all_nonempty_pages(target, cached):
    run = adapter(target, [frame([8, 7]), frame([6, 5]), frame([4, 3])], MemoryCache(cached))
    assert len(run.invoke()) == 6
    assert run.clients[0].offsets == [0, 700, 1400, 2100]
    assert run.cache.cached.date.tolist() == frame(range(3, 9)).date.tolist()


@pytest.mark.parametrize("target", TARGETS)
def test_six_adapters_large_700_bar_pages_catch_up(target):
    # Keep dates during daytime so night-session adapters preserve ordering.
    def daily(values):
        page = frame(values)
        page["date"] = pd.to_datetime("2016-01-01 10:00") + pd.to_timedelta(values, unit="D")
        page["datetime"] = page["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        return page
    pages = [daily(list(range(start, start + 700))) for start in [2100, 1400, 700, 0]]
    run = adapter(target, pages, MemoryCache(daily(list(range(-10, 100)))))
    assert len(run.invoke()) == 2810
    assert run.clients[0].offsets == [0, 700, 1400, 2100]


def test_actual_cache_market_isolation_and_no_legacy_fallback(file_cache):
    for index, target in enumerate(TARGETS):
        market = target[1].lower()
        file_cache.save_tdx_klines(market, "TEST.CODE", "1m", frame([999]))
        run = adapter(target, [frame([index], price=index + 1)], file_cache)
        assert run.invoke().close.tolist() == [index + 1]
    for index, target in enumerate(TARGETS):
        market = target[1].lower()
        key = tdx_cache_key(market, "TEST.CODE", "1m")
        data = file_cache.get_tdx_klines(market, key, "1m", include_incomplete=True)
        assert data.close.tolist() == [index + 1]
        assert file_cache._kline_path(market, "TEST.CODE", "1m").exists()


@pytest.mark.parametrize("target", TARGETS)
def test_invalid_csv_never_starts_page_fetch_or_overwrites_cache(target, file_cache):
    market = target[1].lower()
    key = tdx_cache_key(market, "TEST.CODE", "1m")
    path = file_cache._kline_path(market, key, "1m")
    path.write_text("date,close\ninvalid,1\n", encoding="utf-8")
    run = adapter(target, [frame([4])], file_cache)
    with pytest.raises(RuntimeError, match="invalid date"):
        run.invoke()
    assert len(run.clients) == 1 and run.clients[0].offsets == []
    assert not path.exists()  # FileCacheDB quarantines, never replaces with partial data.
    quarantined = list(path.parent.glob(path.name + ".corrupt.*"))
    assert len(quarantined) == 1
    assert quarantined[0].read_text(encoding="utf-8") == "date,close\ninvalid,1\n"


@pytest.mark.parametrize("target", TARGETS)
def test_metadata_mismatch_conservatively_drops_incomplete_row(target, file_cache):
    market = target[1].lower()
    key = tdx_cache_key(market, "TEST.CODE", "1m")
    file_cache.save_tdx_klines(market, key, "1m", frame([0]), last_row_complete=True)
    path = file_cache._kline_path(market, key, "1m")
    file_cache._meta_path(path).write_text("{}", encoding="utf-8")
    run = adapter(target, [frame([4, 3]), frame([2, 1])], file_cache)
    assert len(run.invoke()) == 4
    assert run.clients[0].offsets == [0, 700, 1400]
