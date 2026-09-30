from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, request
from sqlalchemy import Column, Integer, MetaData, Table, UniqueConstraint, create_engine, event, inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateIndex

from test_support.web_routes import compile_route
from tradingview_zy.alert_strategy_storage import (
    StrategyStorageValidationError,
    build_strategy_config,
    normalize_strategy_memo,
    parse_strategy_kwargs,
)
from tradingview_zy.alert_task_validation import DuplicateAlertTaskError
from tradingview_zy.schema_migrations import SchemaMigrationError, initialize_schema
import tradingview_zy.schema_migrations as migrations

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def db_module(monkeypatch, tmp_path):
    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "b16_b17"
    config.get_data_path = lambda: tmp_path
    fun = types.ModuleType("tradingview_zy.fun")
    fun.singleton = lambda cls: cls
    package = importlib.import_module("tradingview_zy")
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config)
    monkeypatch.setitem(sys.modules, "tradingview_zy.fun", fun)
    monkeypatch.setattr(package, "config", config, raising=False)
    monkeypatch.setattr(package, "fun", fun, raising=False)
    spec = importlib.util.spec_from_file_location(
        "test_b16_b17_db", ROOT / "src/tradingview_zy/db.py"
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    yield module
    module.db.engine.dispose()


def _steps(module):
    return (
        module.migrate_alert_task_uniqueness,
        module.migrate_alert_strategy_storage,
        module.migrate_alert_event_storage,
        module.migrate_tv_storage_schema,
        module.migrate_crypto_storage_timezone,
    )


def _task(name="unique", market="a"):
    return dict(
        market=market, task_name=name, zx_group="watch", frequency="d",
        interval_minutes=5, strategy_config=build_strategy_config("demo", {}),
        strategy_memo="memo", is_run=1,
    )


def test_primary_key_tables_have_no_redundant_unique_constraint(db_module):
    klines = db_module.db.klines_tables("a", "SH.000001")
    for model in (db_module.TableByZxGroup, klines):
        assert not any(isinstance(c, UniqueConstraint) for c in model.__table__.constraints)
    assert "is_send_msg" not in db_module.TableByAlertTask.__table__.columns


def test_sqlite_migration_lock_times_out_without_changing_database(tmp_path):
    database = tmp_path / "locked.sqlite"
    engine = create_engine(f"sqlite:///{database}")
    try:
        with migrations._sqlite_file_lock(database.with_name(database.name + ".schema.lock"), 1):
            with pytest.raises(SchemaMigrationError, match="迁移锁超时"):
                initialize_schema(engine, MetaData(), (lambda connection: None,), lock_timeout=.01)
        assert inspect(engine).get_table_names() == []
        initialize_schema(engine, MetaData(), (lambda connection: None,))
    finally:
        engine.dispose()


def test_task_identity_is_unique_on_insert_and_update_with_cross_market_allowed(db_module):
    db = db_module.db
    assert db.task_save_strategy(**_task())
    with pytest.raises(DuplicateAlertTaskError):
        db.task_save_strategy(**_task(" unique "))
    assert db.task_save_strategy(**_task(market="hk"))
    assert db.task_save_strategy(**_task("second"))
    by_name = {row.task_name: row for row in db.task_query(market="a")}
    first, second = by_name["unique"], by_name["second"]
    assert db.task_update_strategy(id=first.id, **_task())
    with pytest.raises(DuplicateAlertTaskError):
        db.task_update_strategy(id=second.id, **_task())
    assert db.task_query(id=second.id)[0].task_name == "second"
    assert len(db.task_query()) == 3


def test_legacy_task_methods_share_the_unique_name_boundary(db_module):
    payload = _task()
    payload.pop("strategy_config")
    payload.pop("strategy_memo")
    payload.update({key: "" for key in (
        "check_bi_type", "check_bi_beichi", "check_bi_mmd", "check_xd_type",
        "check_xd_beichi", "check_xd_mmd", "check_idx_ma_info", "check_idx_macd_info",
    )})
    assert db_module.db.task_save(**payload)
    with pytest.raises(DuplicateAlertTaskError):
        db_module.db.task_save(**payload)
    assert db_module.db.task_save(**{**payload, "task_name": "other"})
    second = next(row for row in db_module.db.task_query(market="a") if row.task_name == "other")
    with pytest.raises(DuplicateAlertTaskError):
        db_module.db.task_update(id=second.id, **payload)


def test_database_index_prevents_writes_that_bypass_application_check(db_module):
    db_module.db.task_save_strategy(**_task())
    with pytest.raises(IntegrityError):
        with db_module.db.Session.begin() as session:
            session.add(db_module.TableByAlertTask(market="a", task_name="unique"))
    indexes = inspect(db_module.db.engine).get_indexes("cl_alert_task")
    assert any(i["name"] == "table_market_task_name_unique" and i["unique"] for i in indexes)
    index = next(iter(db_module.TableByAlertTask.__table__.indexes))
    ddl = str(CreateIndex(index).compile(dialect=mysql.dialect()))
    assert "CREATE UNIQUE INDEX" in ddl and "(market, task_name)" in ddl


def test_concurrent_unique_violation_is_translated_without_hiding_other_integrity_errors(db_module):
    # Simulate a race at the DB boundary after the pre-check has passed.
    error = IntegrityError(
        "insert", {}, Exception("UNIQUE constraint failed: cl_alert_task.market, cl_alert_task.task_name")
    )
    with pytest.raises(DuplicateAlertTaskError) as caught:
        with db_module.db._task_write_session("a", "race"):
            raise error
    assert caught.value.__cause__ is error
    other = IntegrityError("insert", {}, Exception("NOT NULL constraint failed: another.column"))
    with pytest.raises(IntegrityError) as caught:
        with db_module.db._task_write_session("a", "race"):
            raise other
    assert caught.value is other


def test_task_route_reports_duplicate_through_existing_json_error_contract():
    def fail_save(config):
        raise DuplicateAlertTaskError()

    service = SimpleNamespace(alert_save=fail_save)
    route = compile_route("alert_save", {
        "request": request,
        "_alert_tasks": SimpleNamespace(resolve=lambda: (service, None)),
        "config": SimpleNamespace(ALERT_STRATEGIES={"demo": object()}),
        "parse_strategy_kwargs": parse_strategy_kwargs,
        "StrategyStorageValidationError": StrategyStorageValidationError,
        "validate_registered_strategy": lambda *args: None,
        "build_strategy_config": build_strategy_config,
        "normalize_strategy_memo": normalize_strategy_memo,
    })
    app = Flask(__name__)
    with app.test_request_context("/alert_save", method="POST", data={"strategy_id": "demo"}):
        assert route() == {"ok": False, "msg": str(DuplicateAlertTaskError())}


def test_old_nullable_message_column_without_default_does_not_break_new_task_writes(db_module, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old-message-column.sqlite'}")
    # Baseline model declared this nullable Integer with no server/client default.
    legacy = db_module.TableByAlertTask.__table__.to_metadata(MetaData())
    legacy.indexes.clear()
    legacy.append_column(Column("is_send_msg", Integer, nullable=True))
    legacy.create(engine)
    try:
        initialize_schema(engine, db_module.Base.metadata, _steps(db_module))
        old_db = object.__new__(db_module.DB)
        old_db.Session = sessionmaker(bind=engine)
        assert old_db.task_save_strategy(**_task())
        task = old_db.task_query(market="a")[0]
        assert old_db.task_update_strategy(id=task.id, **_task("updated"))
        with engine.connect() as connection:
            row = connection.execute(text("SELECT task_name, is_send_msg FROM cl_alert_task")).one()
        assert row == ("updated", None)
        assert "is_send_msg" in {c["name"] for c in inspect(engine).get_columns("cl_alert_task")}
    finally:
        engine.dispose()


def test_legacy_duplicate_migration_preserves_tasks_and_does_not_advance_version(db_module, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'duplicates.sqlite'}")
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE cl_alert_task (id INTEGER PRIMARY KEY, market VARCHAR(20), "
                "task_name VARCHAR(100), check_idx_ma_info VARCHAR(200), check_idx_macd_info VARCHAR(200))"
            ))
            connection.execute(text("INSERT INTO cl_alert_task VALUES (1,'a','duplicate','{}',''),(2,'a','duplicate','{}','')"))
        with pytest.raises(SchemaMigrationError, match="duplicate"):
            initialize_schema(engine, db_module.Base.metadata, _steps(db_module))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT id, task_name FROM cl_alert_task ORDER BY id")).all() == [(1,"duplicate"),(2,"duplicate")]
        assert not inspect(engine).has_table("cl_schema_version")
        with engine.begin() as connection:
            connection.execute(text("UPDATE cl_alert_task SET task_name='resolved' WHERE id=2"))
        initialize_schema(engine, db_module.Base.metadata, _steps(db_module))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version FROM cl_schema_version")).scalar_one() == 5
        assert "strategy_config" in {c["name"] for c in inspect(engine).get_columns("cl_alert_task")}
    finally:
        engine.dispose()


def test_current_schema_startup_only_reads_version_and_succeeds_while_other_writer_holds_lock(db_module):
    engine = db_module.db.engine
    statements = []
    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(engine, "before_cursor_execute", record)
    try:
        with engine.connect() as writer:
            writer.exec_driver_sql("BEGIN IMMEDIATE")
            statements.clear()
            initialize_schema(engine, db_module.Base.metadata, _steps(db_module))
            assert not any(word in sql.upper() for sql in statements for word in ("UPDATE", "ALTER", "CREATE", "CL_ALERT_RECORD", "CL_ALERT_TASK"))
            assert any("cl_schema_version" in sql for sql in statements)
            writer.rollback()
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_failed_sqlite_migration_rolls_back_ddl_data_and_version_then_retries(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'retry.sqlite'}")
    metadata = MetaData()
    Table("sample", metadata, Column("id", Integer, primary_key=True))
    def fail(connection):
        connection.execute(text("ALTER TABLE sample ADD COLUMN value INTEGER"))
        connection.execute(text("INSERT INTO sample VALUES (1, 7)"))
        raise RuntimeError("failure")
    try:
        with pytest.raises(RuntimeError, match="failure"):
            initialize_schema(engine, metadata, (fail,))
        assert inspect(engine).get_table_names() == []
        initialize_schema(engine, metadata, (lambda connection: None,))
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version FROM cl_schema_version")).scalar_one() == 1
    finally:
        engine.dispose()


def test_in_memory_schema_and_future_version_fail_closed():
    engine = create_engine("sqlite:///:memory:")
    try:
        initialize_schema(engine, MetaData(), (lambda connection: None,))
        initialize_schema(engine, MetaData(), (lambda connection: pytest.fail("reran"),))
        with engine.begin() as connection:
            connection.execute(text("UPDATE cl_schema_version SET version=99"))
        with pytest.raises(SchemaMigrationError, match="版本高于"):
            initialize_schema(engine, MetaData(), (lambda connection: None,))
    finally:
        engine.dispose()


def test_concurrent_first_db_imports_are_serialized(tmp_path):
    script = r'''
import importlib, pathlib, sys, time, types
root, data, child = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(root / 'src'))
config = types.ModuleType('tradingview_zy.config')
config.DB_TYPE = 'sqlite'
config.DB_DATABASE = 'concurrent'
config.get_data_path = lambda: data
fun = types.ModuleType('tradingview_zy.fun')
fun.singleton = lambda cls: cls
sys.modules['tradingview_zy.config'] = config
sys.modules['tradingview_zy.fun'] = fun
child.touch()
while not (data / 'start').exists():
    time.sleep(.01)
m = importlib.import_module('tradingview_zy.db')
with m.db.engine.connect() as connection:
    assert connection.exec_driver_sql('SELECT version FROM cl_schema_version').scalar_one() == 5
m.db.engine.dispose()
'''
    processes = [subprocess.Popen(
        [sys.executable, "-c", script, str(ROOT), str(tmp_path), str(tmp_path / f"ready-{index}")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) for index in range(4)]
    try:
        deadline = time.monotonic() + 20
        while len(list(tmp_path.glob("ready-*"))) < 4 and time.monotonic() < deadline:
            time.sleep(.02)
        (tmp_path / "start").touch()
        for process in processes:
            out, err = process.communicate(timeout=60)
            assert process.returncode == 0, (out, err)
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()


def test_mysql_type_changes_are_conditional_and_keep_comments(db_module, monkeypatch):
    connection = SimpleNamespace(dialect=mysql.dialect())
    columns = [
        {"name": "user_id", "type": mysql.INTEGER(), "nullable": True, "default": None, "comment": "custom owner"},
        {"name": "content", "type": mysql.TEXT(), "nullable": True, "default": None, "comment": None},
    ]
    monkeypatch.setattr(db_module, "inspect", lambda bind: SimpleNamespace(get_columns=lambda table: columns))
    changes = db_module._mysql_tv_column_changes(connection, db_module.TableByTVCharts.__table__, ("user_id", "content"))
    assert len(changes) == 2
    assert "VARCHAR(50)" in changes[0] and "COMMENT 'custom owner'" in changes[0]
    assert "MEDIUMTEXT" in changes[1] and "COMMENT '布局内容'" in changes[1]
    columns[0]["type"] = mysql.VARCHAR(50)
    columns[1]["type"] = mysql.MEDIUMTEXT()
    assert db_module._mysql_tv_column_changes(connection, db_module.TableByTVCharts.__table__, ("user_id", "content")) == []
    columns[1]["type"] = mysql.LONGTEXT()
    assert db_module._mysql_tv_column_changes(connection, db_module.TableByTVCharts.__table__, ("content",)) == []


@pytest.mark.parametrize("acquired", [0, 1, None])
def test_mysql_lock_uses_one_connection_and_releases_after_failure(acquired):
    calls = []
    class Connection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return SimpleNamespace(scalar_one=lambda: acquired)
        def rollback(self):
            calls.append(("rollback", {}))
        def commit(self):
            calls.append(("commit", {}))
    connection = Connection()
    engine = SimpleNamespace(dialect=SimpleNamespace(name="mysql"), url=SimpleNamespace(database="test_db"), connect=lambda: connection)
    if acquired == 1:
        with pytest.raises(RuntimeError, match="migration failed"):
            with migrations._locked_connection(engine, 2) as held:
                assert held is connection
                raise RuntimeError("migration failed")
        assert any("RELEASE_LOCK" in sql for sql, _ in calls)
    else:
        with pytest.raises(SchemaMigrationError):
            with migrations._locked_connection(engine, 2):
                pytest.fail("entered without lock")
        assert not any("RELEASE_LOCK" in sql for sql, _ in calls)
    get = next(params for sql, params in calls if "GET_LOCK" in sql)
    assert get["timeout"] == 2 and len(get["name"]) <= 64
    assert "test_db" not in get["name"]
