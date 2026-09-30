"""B12 scheme C: isolated databases only; no config/provider/user-cache imports."""
from __future__ import annotations

import ast
import datetime as dt
import importlib
import importlib.util
import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
from typing import Dict, List, Union

import pandas as pd
import pytest
import pytz
from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from tradingview_zy import crypto_time as ct
from tradingview_zy.exchange.binance_pagination import latest_cached_datetime, paginate_ohlcv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/tradingview_zy"


@pytest.fixture
def db_module(monkeypatch, tmp_path):
    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "b12"
    config.get_data_path = lambda: tmp_path
    config.CRYPTO_STORAGE_TIMEZONES = {}
    fun = types.ModuleType("tradingview_zy.fun")
    fun.singleton = lambda cls: cls
    package = importlib.import_module("tradingview_zy")
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config)
    monkeypatch.setitem(sys.modules, "tradingview_zy.fun", fun)
    monkeypatch.setattr(package, "config", config, raising=False)
    monkeypatch.setattr(package, "fun", fun, raising=False)
    spec = importlib.util.spec_from_file_location("test_b12_db", SRC / "db.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    yield module
    module.db.engine.dispose()


def frame(dates):
    return pd.DataFrame({"date": [pd.Timestamp(d) for d in dates], "code": "BTC/USDT",
                         "open": range(1, len(dates)+1), "high": 9, "low": 0,
                         "close": range(2, len(dates)+2), "volume": 10})


def compile_node(relative, name, namespace, methods=None):
    tree = ast.parse((SRC / relative).read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name == name)
    if methods is not None:
        node.bases = []
        node.decorator_list = []
        node.body = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name in methods]
    namespace = {"pd": pd, "datetime": dt, "pytz": pytz, "Dict": Dict, "List": List,
                 "Union": Union, "as_utc": ct.as_utc, "is_crypto": ct.is_crypto, **namespace}
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), node], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), relative, "exec"), namespace)
    return namespace[name]


@pytest.fixture
def converter():
    return compile_node("exchange/exchange.py", "convert_currency_kline_frequency", {})


@pytest.mark.parametrize("market", ["currency", "currency_spot"])
@pytest.mark.parametrize("zone", ["UTC", "Asia/Shanghai", "America/New_York"])
def test_roundtrip_bounds_latest_delete_and_unchanged_wall_keys(db_module, market, zone):
    db = db_module.db
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {market: zone}
    data = frame(["2025-01-01T00:00Z", "2025-01-01T01:00Z", "2025-01-01T02:00Z"])
    db.klines_insert(market, "BTC/USDT", "60m", data)
    db.klines_insert(market, "BTC/USDT", "60m", data)
    rows = db.klines_query(market, "BTC/USDT", "60m", "2025-01-01T08:00+08:00", "2025-01-01 01:00:00", order="asc")
    assert [r.dt for r in rows] == list(data.date[:2])
    assert all(r.f == "60m" for r in rows)
    assert db.klines_last_datetime(market, "BTC/USDT", "60m") == "2025-01-01T02:00:00+00:00"
    table = db.klines_tables(market, "BTC/USDT")
    with db.engine.connect() as con:
        raw = con.execute(select(table.dt).order_by(table.dt)).scalars().all()
    assert raw == [ct.to_storage(d, zone) for d in data.date]
    db.klines_delete(market, "BTC/USDT", "60m", dt.datetime(2025, 1, 1, 1))
    assert len(db.klines_query(market, "BTC/USDT", "60m")) == 2
    # Reads detached UTC rows; no update to persisted wall-clock primary keys.
    with db.engine.connect() as con:
        assert con.execute(select(table.dt).order_by(table.dt)).scalars().all() == [raw[0], raw[2]]


def test_old_data_needs_explicit_confirmation_and_binding_is_immutable(db_module):
    db = db_module.db
    table = db.klines_tables("currency", "BTC/USDT")
    with db.engine.begin() as con:
        con.execute(table.__table__.insert().values(code="BTC/USDT", dt=dt.datetime(2025, 1, 1, 8), f="60m", o=1,c=2,h=3,l=0,v=10))
    for operation in [lambda: db.klines_query("currency", "BTC/USDT", "60m"),
                      lambda: db.klines_last_datetime("currency", "BTC/USDT", "60m"),
                      lambda: db.klines_delete("currency", "BTC/USDT"),
                      lambda: db.klines_insert("currency", "ETH/USDT", "60m", frame(["2025-01-01T00:00Z"]))]:
        with pytest.raises(ct.CryptoTimezoneError, match="CRYPTO_STORAGE_TIMEZONES"):
            operation()
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {"currency": "Asia/Shanghai"}
    assert db.klines_query("currency", "BTC/USDT", "60m")[0].dt == ct.as_utc("2025-01-01T00:00Z")
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {}
    assert db.crypto_storage_timezone("currency") == "Asia/Shanghai"
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {"currency": "UTC"}
    with pytest.raises(ct.CryptoTimezoneError, match="已锁定"):
        db.crypto_storage_timezone("currency")
    assert ct.storage_timezone(db.engine, "currency_spot") == "UTC"


@pytest.mark.parametrize("wall", ["2025-03-09 02:30", "2025-11-02 01:30"])
def test_dst_invalid_storage_rejected(wall):
    with pytest.raises(ct.CryptoTimezoneError, match="DST"):
        ct.from_storage(wall, "America/New_York")


@pytest.mark.parametrize("instant", ["2025-11-02T05:30Z", "2025-11-02T06:30Z"])
def test_dst_fold_write_rejected_without_overwriting(db_module, instant):
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {"currency": "America/New_York"}
    with pytest.raises(ct.CryptoTimezoneError, match="DST"):
        db_module.db.klines_insert("currency", "BTC/USDT", "60m", frame([instant]))
    assert db_module.db.klines_query("currency", "BTC/USDT", "60m") == []


def test_binding_concurrency_and_read_fast_path(tmp_path):
    path = tmp_path / "concurrent.sqlite"
    engines = [create_engine(f"sqlite:///{path}", connect_args={"timeout": .1}) for _ in range(2)]
    ct.migrate_crypto_storage_timezone(engines[0])
    def bind(item):
        engine, zone = item
        try:
            return ct.storage_timezone(engine, "currency", zone)
        except ct.CryptoTimezoneError:
            return "conflict"
    try:
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(bind, zip(engines, ["UTC", "Asia/Shanghai"])))
        assert results.count("conflict") == 1
        bound = next(r for r in results if r != "conflict")
        with engines[0].connect() as writer:
            writer.exec_driver_sql("BEGIN IMMEDIATE")
            assert ct.storage_timezone(engines[1], "currency") == bound
            writer.rollback()
    finally:
        for engine in engines:
            engine.dispose()


@pytest.mark.parametrize("frequency", ["3h", "10m", "2m"])
def test_derived_cache_version_all_db_boundaries(db_module, frequency):
    db = db_module.db
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {"currency": "UTC"}
    table = db.klines_tables("currency", "BTC/USDT")
    with db.engine.begin() as con:
        con.execute(table.__table__.insert().values(code="BTC/USDT", dt=dt.datetime(2025,1,1), f=frequency,o=999,c=999,h=999,l=999,v=999))
    assert db.klines_query("currency", "BTC/USDT", frequency) == []
    assert db.klines_last_datetime("currency", "BTC/USDT", frequency) is None
    db.klines_insert("currency", "BTC/USDT", frequency, frame(["2025-01-01T00:00Z"]))
    rows = db.klines_query("currency", "BTC/USDT", frequency)
    assert [(r.f, r.o) for r in rows] == [(frequency, 1)]
    assert db.klines_last_datetime("currency", "BTC/USDT", frequency) == "2025-01-01T00:00:00+00:00"
    db.klines_delete("currency", "BTC/USDT", frequency, ct.as_utc("2025-01-01"))
    assert db.klines_query("currency", "BTC/USDT", frequency) == []
    with db.engine.connect() as con:
        assert con.execute(select(table.f, table.o)).all() == [(frequency, 999)]


def test_noncrypto_storage_unchanged(db_module):
    db = db_module.db
    data = frame(["2025-01-01T15:00+08:00"])
    db.klines_insert("a", "SH.000001", "d", data)
    row = db.klines_query("a", "SH.000001", "d")[0]
    assert row.dt == dt.datetime(2025, 1, 1, 15)
    assert db.klines_last_datetime("a", "SH.000001", "d") == "2025-01-01"
    with db.engine.connect() as con:
        assert con.execute(select(ct._REGISTRY)).all() == []


@pytest.mark.parametrize("zone", ["UTC", "Asia/Shanghai", "America/New_York"])
def test_utc_daily_and_three_hour_ohlcv(converter, zone):
    data = frame(["2024-02-28T23:59Z", "2024-02-29T00:00Z", "2024-02-29T02:59Z", "2024-02-29T03:00Z", "2024-02-29T23:59Z", "2024-03-01T00:00Z"])
    data["date"] = data.date.dt.tz_convert(zone)
    original = data.copy(deep=True)
    daily = converter(data, "d")
    assert list(daily.date) == list(pd.to_datetime(["2024-02-28", "2024-02-29", "2024-03-01"], utc=True))
    assert list(daily.open) == [1,2,6]
    assert list(daily.close) == [2,6,7]
    assert list(daily.volume) == [10,40,10]
    assert list(daily.high) == [9,9,9] and list(daily.low) == [0,0,0]
    h3 = converter(data, "3h")
    assert list(h3.date.dt.hour) == [21,0,3,21,0]
    assert list(h3.open) == [1,2,4,5,6]
    assert list(h3.close) == [2,4,5,6,7]
    assert list(h3.volume) == [10,20,10,10,10]
    pd.testing.assert_frame_equal(data, original)
    assert converter(data.iloc[:0], "d").empty


@pytest.mark.parametrize("offset", [0, 8, -5])
@pytest.mark.parametrize("adapter", ["exchange_binance", "exchange_binance_spot"])
def test_provider_utc_independent_of_simulated_host_without_tzset(converter, offset, adapter):
    # Windows has no tzset. Simulate the actual datetime APIs that used to depend
    # on the host, and prove the sentinel changes naive timestamps in each case.
    class HostDatetime(dt.datetime):
        def timestamp(self):
            if self.tzinfo is None:
                return self.replace(tzinfo=dt.timezone(dt.timedelta(hours=offset))).timestamp()
            return super().timestamp()
        @classmethod
        def fromtimestamp(cls, value, tz=None):
            if tz is None:
                return dt.datetime.fromtimestamp(value, dt.timezone(dt.timedelta(hours=offset))).replace(tzinfo=None)
            return dt.datetime.fromtimestamp(value, tz)
    host = SimpleNamespace(datetime=HostDatetime, timezone=dt.timezone)
    base_ms = int(ct.as_utc("2025-01-01").timestamp()*1000)
    assert int(HostDatetime(2025,1,1).timestamp()*1000) == base_ms-offset*3600000
    calls = []
    def fetch(*args, **kwargs):
        calls.append(kwargs["params"])
        return [[base_ms,1,3,0,2,10]]
    name = "ExchangeBinance" if adapter == "exchange_binance" else "ExchangeBinanceSpot"
    cls = compile_node(f"exchange/{adapter}.py", name,
        {"datetime": host, "time": time, "fetch_ohlcv_with_retry": fetch,
         "paginate_ohlcv": paginate_ohlcv, "convert_currency_kline_frequency": converter},
        {"online_klines", "increment_klines_by_online"})
    ex = cls(); ex.exchange = object(); ex._ohlcv_lock = RLock(); ex.tz = pytz.timezone("Asia/Shanghai")
    output = ex.online_klines("BTC/USDT", "60m", "2025-01-01 00:00:00", "2025-01-01T09:00+08:00")
    assert calls[-1] == {"startTime": base_ms, "endTime": base_ms+3600000}
    assert output.date.iloc[0] == ct.as_utc("2025-01-01")
    cursor = latest_cached_datetime(output)
    assert cursor == "2025-01-01T00:00:00+00:00"
    ex.increment_klines_by_online("BTC/USDT", "60m", cursor)
    assert calls[-1]["startTime"] == base_ms


def test_mysql_upsert_uses_same_wall_boundary_and_namespaced_frequency(db_module, monkeypatch):
    db = db_module.db
    table = db.klines_tables("currency", "BTC/USDT")
    statements = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement): statements.append(statement.compile(dialect=mysql.dialect()))
        def commit(self): pass
    monkeypatch.setattr(db, "Session", Session)
    monkeypatch.setattr(db, "crypto_storage_timezone", lambda market: "Asia/Shanghai")
    monkeypatch.setattr(db, "klines_tables", lambda *args: table)
    monkeypatch.setattr(db_module.config, "DB_TYPE", "mysql")
    db.klines_insert("currency", "BTC/USDT", "3h", frame(["2025-01-01T00:00Z"]))
    assert "ON DUPLICATE KEY UPDATE" in str(statements[0])
    assert statements[0].params["dt_m0"] == dt.datetime(2025,1,1,8)
    assert statements[0].params["f_m0"] == "3hC1"
    ddl = str(CreateTable(ct._REGISTRY).compile(dialect=mysql.dialect()))
    assert "PRIMARY KEY (market)" in ddl and "timezone VARCHAR(64) NOT NULL" in ddl


def test_artifacts_versioned_without_reusing_old_paths(tmp_path):
    old = tmp_path / "state.pkl"
    old.write_bytes(b"preserve")
    new = ct.artifact_path(old)
    assert new != str(old) and ct.artifact_path(new) == new
    assert old.read_bytes() == b"preserve"
    with pytest.raises(ct.CryptoTimezoneError, match="仅供历史查看"):
        ct.require_current_version("currency", None)
    ct.require_current_version("a", None)
    ct.require_current_version("currency", ct.CRYPTO_TIME_VERSION)


@pytest.fixture
def exchange_db(db_module, converter):
    from tradingview_zy.base import Market
    cls = compile_node("exchange/exchange_db.py", "ExchangeDB", {
        "db": db_module.db, "Market": Market,
        "convert_currency_kline_frequency": converter,
        "market_timezone": lambda market: pytz.UTC if ct.is_crypto(market) else pytz.timezone("Asia/Shanghai"),
        "fun": SimpleNamespace(str_to_datetime=lambda value, tz: tz.localize(dt.datetime.fromisoformat(value))),
    }, {"__init__", "klines", "__convert_date", "query_last_datetime", "insert_klines", "del_klines", "convert_kline_frequency"})
    return cls


@pytest.mark.parametrize("market", ["currency", "currency_spot"])
def test_exchange_db_sqlite_roundtrip_and_incremental_sync(db_module, exchange_db, market):
    from tradingview_zy.sync_batch import BatchDeadline, DeadlineCaller, sync_incremental_series
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {market: "Asia/Shanghai"}
    ex = exchange_db(market)
    ex.insert_klines("BTC/USDT", "60m", frame(["2025-01-01T00:00Z"]))
    calls = []
    class Source:
        def klines(self, code, frequency, start_date=None, args=None):
            calls.append(start_date)
            if len(calls) == 1:
                return frame(["2025-01-01T00:00Z", "2025-01-01T01:00Z"])
            return frame([])
    result = sync_incremental_series(destination=ex, source=Source(), code="BTC/USDT", frequency="60m",
        start_date="2024-12-31 00:00:00", query_args={}, stop_rows=1, max_pages=3,
        deadline=BatchDeadline(10), caller=DeadlineCaller(max_concurrent=1), per_call_timeout=3)
    assert calls == ["2025-01-01T00:00:00+00:00", "2025-01-01T01:00:00+00:00"]
    assert result.rows_written == 2
    result = ex.klines("BTC/USDT", "60m", "2025-01-01T08:00+08:00", "2025-01-01T09:00+08:00")
    assert list(result.date) == [ct.as_utc("2025-01-01"), ct.as_utc("2025-01-01T01:00Z")]
    ex.del_klines("BTC/USDT", "60m", ct.as_utc("2025-01-01"))
    assert len(ex.klines("BTC/USDT", "60m")) == 1


@pytest.mark.parametrize("market", ["currency", "currency_spot"])
@pytest.mark.parametrize("cache", [True, False])
def test_backtest_utc_bounds_loop_and_no_future_bars(db_module, exchange_db, monkeypatch, market, cache):
    from tradingview_zy.backtesting.backtest_klines import BackTestKlines
    fake = types.ModuleType("tradingview_zy.exchange.exchange_db")
    fake.ExchangeDB = exchange_db
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    db_module.config.CRYPTO_STORAGE_TIMEZONES = {market: "Asia/Shanghai"}
    db_module.db.klines_insert(market, "BTC/USDT", "60m", frame([
        "2024-12-31T23:00Z", "2025-01-01T00:00Z", "2025-01-01T01:00Z", "2025-01-01T02:00Z"]))
    replay = BackTestKlines(market, "2025-01-01 00:00:00", "2025-01-01T10:00+08:00", ["60m"])
    assert replay.start_date == ct.as_utc("2025-01-01")
    assert replay.end_date == ct.as_utc("2025-01-01T02:00Z")
    replay.load_data_to_cache = cache
    replay.init("BTC/USDT", "60m")
    assert len(replay.loop_datetime_list["60m"]) == 3
    dates = []
    while replay.next():
        dates.append(replay.now_date)
        history = replay.klines("BTC/USDT", "60m")
        assert (history.date < replay.now_date).all()
    replay.bar.close()
    assert dates == [ct.as_utc(f"2025-01-01T0{hour}:00Z") for hour in range(3)]


def test_noncrypto_exchange_db_display_keeps_wall_timezone(db_module, exchange_db):
    db_module.db.klines_insert("a", "SH.000001", "d", frame(["2025-01-01T00:00+08:00"]))
    result = exchange_db("a").klines("SH.000001", "d")
    assert result.date.iloc[0] == pd.Timestamp("2025-01-01T15:00+08:00")


def test_backtest_legacy_result_cannot_be_optimized_or_resaved():
    cls = compile_node("backtesting/backtest.py", "BackTest", {
        "require_current_version": ct.require_current_version,
        "CRYPTO_TIME_VERSION": ct.CRYPTO_TIME_VERSION,
    }, {"_require_time_version", "run", "run_params", "save"})
    old = cls(); old.market = "currency"; old.save_file = "old.pkl"
    with pytest.raises(ct.CryptoTimezoneError): old.run_params({})
    with pytest.raises(ct.CryptoTimezoneError): old.save()
    with pytest.raises(ct.CryptoTimezoneError): old.run("60m")


def test_configured_sync_preserves_old_checkpoint_and_uses_new_identity(tmp_path):
    import json
    from tradingview_zy.sync_batch import run_configured_sync
    config = {
        "market": "currency", "mode": "incremental", "universe": {"type": "list", "codes": []},
        "source": {"class": "unused.Source"}, "destination": {"class": "unused.Destination"},
        "frequencies": {"60m": {"start_date": "2025-01-01"}},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    old = tmp_path / "checkpoint.json"
    old.write_text("preserve", encoding="utf-8")
    result = run_configured_sync(config_path=config_path, checkpoint_path=old,
        batch_deadline_seconds=5, per_call_timeout=2)
    assert result.checkpoint == ct.artifact_path(old)
    assert old.read_text(encoding="utf-8") == "preserve"
    assert Path(result.checkpoint).exists()


def test_mysql_query_delete_and_latest_compile_consistent_boundaries(db_module, monkeypatch):
    from sqlalchemy import delete
    db = db_module.db
    table = db.klines_tables("currency", "BTC/USDT")
    compiled = []
    class Query:
        def __init__(self, target):
            self.statement = select(target)
            self.conditions = []
        def filter(self, *conditions):
            self.conditions.extend(conditions)
            self.statement = self.statement.where(*conditions)
            return self
        def order_by(self, *columns):
            self.statement = self.statement.order_by(*columns)
            return self
        def limit(self, n):
            self.statement = self.statement.limit(n)
            return self
        def all(self):
            compiled.append(self.statement.compile(dialect=mysql.dialect()))
            return []
        def first(self):
            compiled.append(self.statement.limit(1).compile(dialect=mysql.dialect()))
            return (dt.datetime(2025,1,1,9),)
        def delete(self):
            compiled.append(delete(table).where(*self.conditions).compile(dialect=mysql.dialect()))
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def query(self, target): return Query(target)
        def commit(self): pass
    monkeypatch.setattr(db, "Session", Session)
    monkeypatch.setattr(db, "crypto_storage_timezone", lambda market: "Asia/Shanghai")
    monkeypatch.setattr(db, "klines_tables", lambda *args: table)
    db.klines_query("currency", "BTC/USDT", "3h", "2025-01-01T00:00Z", "2025-01-01T01:00Z")
    assert compiled[-1].params["dt_1"] == dt.datetime(2025,1,1,8)
    assert compiled[-1].params["dt_2"] == dt.datetime(2025,1,1,9)
    assert compiled[-1].params["f_1"] == "3hC1"
    assert db.klines_last_datetime("currency", "BTC/USDT", "3h") == "2025-01-01T01:00:00+00:00"
    assert compiled[-1].params["f_1"] == "3hC1"
    db.klines_delete("currency", "BTC/USDT", "3h", "2025-01-01T00:00Z")
    assert compiled[-1].params["dt_1"] == dt.datetime(2025,1,1,8)
    assert compiled[-1].params["f_1"] == "3hC1"


def test_mysql_binding_uses_read_fast_path_and_serialized_recheck(monkeypatch):
    from contextlib import contextmanager
    events = []
    state = {"zone": None}
    class Result:
        def __init__(self, value): self.value = value
        def scalar_one_or_none(self): return self.value
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, statement):
            sql = statement.compile(dialect=mysql.dialect())
            events.append(str(sql))
            if str(sql).startswith("SELECT"):
                return Result(state["zone"])
            state["zone"] = sql.params["timezone"]
            return Result(None)
        def rollback(self): events.append("rollback")
        def begin(self): events.append("begin")
        def commit(self): events.append("commit")
    class Engine:
        dialect = mysql.dialect()
        def connect(self): return Connection()
    @contextmanager
    def locked(engine, timeout):
        events.append("lock")
        yield Connection()
    monkeypatch.setattr(ct, "_locked_connection", locked)
    engine = Engine()
    assert ct.storage_timezone(engine, "currency", "Asia/Shanghai") == "Asia/Shanghai"
    assert events.count("lock") == 1
    assert sum(event.startswith("SELECT") for event in events) == 2
    events.clear()
    assert ct.storage_timezone(engine, "currency") == "Asia/Shanghai"
    assert len(events) == 1 and events[0].startswith("SELECT")
    with pytest.raises(ct.CryptoTimezoneError, match="已锁定"):
        ct.storage_timezone(engine, "currency", "UTC")


@pytest.mark.parametrize("cache", [True, False])
def test_multifrequency_replay_rebuilds_partial_crypto_bars_without_future_close(db_module, exchange_db, converter, monkeypatch, cache):
    from tradingview_zy.backtesting.backtest_klines import BackTestKlines
    fake = types.ModuleType("tradingview_zy.exchange.exchange_db")
    fake.ExchangeDB = exchange_db
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    data = frame(pd.date_range("2025-01-01", periods=361, freq="min", tz="UTC"))
    # Distinct closes make any accidental inclusion of later minutes observable.
    for frequency in ("1m", "60m", "3h"):
        db_module.db.klines_insert("currency", "BTC/USDT", frequency,
            data if frequency == "1m" else converter(data, frequency))
    replay = BackTestKlines("currency", "2025-01-01 03:01:00", "2025-01-01 03:02:00", ["3h", "60m", "1m"])
    replay.load_data_to_cache = cache
    replay.init("BTC/USDT", "1m")
    assert replay.next()
    for frequency in replay.frequencys:
        result = replay.klines("BTC/USDT", frequency)
        assert result.close.iloc[-1] == 182  # 03:00 minute, not 03:01 or full 03:00 hour/3h bar
        assert result.date.iloc[-1] < replay.now_date
    replay.bar.close()


def test_optimization_identity_does_not_probe_old_crypto_cache():
    import copy
    import hashlib
    events = []
    cls = compile_node("backtesting/backtest.py", "BackTest", {
        "require_current_version": ct.require_current_version, "CRYPTO_TIME_VERSION": ct.CRYPTO_TIME_VERSION,
        "CryptoTimezoneError": ct.CryptoTimezoneError, "artifact_path": ct.artifact_path,
        "copy": copy, "hashlib": hashlib,
        "os": SimpleNamespace(path=SimpleNamespace(isfile=lambda path: events.append(("probe", path)) or False)),
    }, {"_require_time_version", "run_params"})
    class Child:
        def __init__(self, config):
            self.log = SimpleNamespace(info=lambda *args: None)
        def run(self, frequency): events.append(("run", frequency))
        def save(self): events.append(("save", self.save_file))
        def positions(self): return pd.DataFrame()
    cls.run_params.__globals__["BackTest"] = Child
    instance = cls()
    for key, value in dict(market="currency", crypto_time_version=ct.CRYPTO_TIME_VERSION,
        data_config={}, base_code="BTC/USDT", codes=["BTC/USDT"], frequencys=["60m"],
        start_datetime="2025-01-01", end_datetime="2025-01-02", strategy=None, mode="signal",
        init_balance=100, fee_rate=0, max_pos=1, futures_parameter_version=None,
        load_data_to_cache=True, next_frequency="60m", evaluate="profit_rate").items():
        setattr(instance, key, value)
    result = instance.run_params({"length": 5})
    assert ct.CRYPTO_TIME_VERSION in result["save_file"]
    assert events == [("probe", result["save_file"]), ("run", "60m"), ("save", result["save_file"])]


@pytest.mark.parametrize("cache", [True, False])
@pytest.mark.parametrize("missing_start", [True, False])
def test_direct_three_hour_replay_cannot_reuse_future_high_volume(db_module, exchange_db, converter, monkeypatch, cache, missing_start):
    from tradingview_zy.backtesting.backtest_klines import BackTestKlines
    fake = types.ModuleType("tradingview_zy.exchange.exchange_db")
    fake.ExchangeDB = exchange_db
    monkeypatch.setitem(sys.modules, fake.__name__, fake)
    data = frame(pd.date_range("2025-01-01", periods=180, freq="min", tz="UTC"))
    data["high"] = 150
    data.loc[121:, "high"] = 999
    data.loc[121:, "low"] = -999
    data.loc[121:, "volume"] = 1000
    data.loc[179, "close"] = 122  # Future full-bar close matches current; high/volume still leak.
    db_module.db.klines_insert("currency", "BTC/USDT", "3h", converter(data, "3h"))
    db_module.db.klines_insert("currency", "BTC/USDT", "1m", data.iloc[30:] if missing_start else data)
    replay = BackTestKlines("currency", "2025-01-01 02:01:00", "2025-01-01 02:02:00", ["3h", "1m"])
    replay.load_data_to_cache = cache
    replay.init("BTC/USDT", "1m")
    assert replay.next()
    if missing_start:
        with pytest.raises(ct.CryptoTimezoneError, match="基础历史不足"):
            replay.klines("BTC/USDT", "3h")
    else:
        result = replay.klines("BTC/USDT", "3h").iloc[-1]
        assert result[["open", "high", "low", "close", "volume"]].tolist() == [1, 150, 0, 122, 1210]
    replay.bar.close()
