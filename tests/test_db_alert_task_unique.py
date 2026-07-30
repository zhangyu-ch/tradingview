from __future__ import annotations

import datetime
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    inspect,
    select,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateIndex, CreateTable

from tradingview_zy.db_schema import (
    ALERT_TASK_UNIQUE_COLUMNS,
    ALERT_TASK_UNIQUE_INDEX_NAME,
    alert_task_unique_key_exists,
    ensure_alert_task_unique_key,
)

ROOT = Path(__file__).resolve().parents[1]


def _install_demo_config_if_needed() -> None:
    try:
        importlib.import_module("tradingview_zy.config")
        return
    except ModuleNotFoundError:
        pass

    config_path = ROOT / "src" / "tradingview_zy" / "config.py.demo"
    spec = importlib.util.spec_from_file_location("tradingview_zy.config", config_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tradingview_zy.config"] = module
    spec.loader.exec_module(module)


def _legacy_alert_task_table(engine):
    metadata = MetaData()
    table = Table(
        "cl_alert_task",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("market", String(20)),
        Column("task_name", String(100)),
        Column("is_run", Integer),
        Column("dt", DateTime),
    )
    metadata.create_all(engine)
    return table


def _unique_column_sets(inspector, table_name: str) -> set[frozenset[str]]:
    result = {
        frozenset(item.get("column_names") or ())
        for item in inspector.get_unique_constraints(table_name)
    }
    result.update(
        frozenset(item.get("column_names") or ())
        for item in inspector.get_indexes(table_name)
        if item.get("unique")
    )
    return result


def test_legacy_migration_preserves_rows_disables_older_duplicate_and_adds_unique_key():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table = _legacy_alert_task_table(engine)
    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [
                {
                    "id": 1,
                    "market": "a",
                    "task_name": "突破监控",
                    "is_run": 1,
                    "dt": datetime.datetime(2025, 1, 1, 9, 0),
                },
                {
                    "id": 2,
                    "market": "a",
                    "task_name": "突破监控",
                    "is_run": 0,
                    "dt": datetime.datetime(2025, 1, 2, 9, 0),
                },
            ],
        )

    result = ensure_alert_task_unique_key(engine)

    assert result.unique_key_created is True
    assert len(result.resolved_duplicates) == 1
    resolution = result.resolved_duplicates[0]
    assert resolution.kept_id == 1
    assert resolution.disabled_id == 2
    assert alert_task_unique_key_exists(engine)

    with engine.connect() as connection:
        rows = connection.execute(select(table).order_by(table.c.id)).mappings().all()
    assert len(rows) == 2  # Migration is non-destructive.
    assert rows[0]["task_name"] == "突破监控"
    assert rows[0]["is_run"] == 1
    assert rows[1]["is_run"] == 0
    assert "duplicate-disabled-2" in rows[1]["task_name"]

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                table.insert().values(
                    market="a",
                    task_name="突破监控",
                    is_run=1,
                    dt=datetime.datetime.now(),
                )
            )


def test_legacy_migration_is_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table = _legacy_alert_task_table(engine)
    with engine.begin() as connection:
        connection.execute(
            table.insert(),
            [
                {"id": 1, "market": "hk", "task_name": "同名任务", "is_run": 1},
                {"id": 2, "market": "hk", "task_name": "同名任务", "is_run": 1},
            ],
        )

    first = ensure_alert_task_unique_key(engine)
    with engine.connect() as connection:
        rows_after_first = connection.execute(
            select(table.c.id, table.c.task_name, table.c.is_run).order_by(table.c.id)
        ).all()
    second = ensure_alert_task_unique_key(engine)
    with engine.connect() as connection:
        rows_after_second = connection.execute(
            select(table.c.id, table.c.task_name, table.c.is_run).order_by(table.c.id)
        ).all()

    assert first.unique_key_created is True
    assert second.unique_key_created is False
    assert second.resolved_duplicates == ()
    assert rows_after_second == rows_after_first



def test_existing_database_unique_index_ddl_is_valid_for_mysql():
    metadata = MetaData()
    table = Table(
        "cl_alert_task",
        metadata,
        Column("market", String(20)),
        Column("task_name", String(100)),
    )
    index = Index(
        ALERT_TASK_UNIQUE_INDEX_NAME,
        table.c.market,
        table.c.task_name,
        unique=True,
    )
    ddl = str(CreateIndex(index).compile(dialect=mysql.dialect()))
    assert ddl == (
        "CREATE UNIQUE INDEX uq_cl_alert_task_market_task_name "
        "ON cl_alert_task (market, task_name)"
    )

def test_current_models_keep_constraints_and_mysql_table_options_together(tmp_path):
    _install_demo_config_if_needed()
    db_module = importlib.import_module("tradingview_zy.db")

    alert_table = db_module.TableByAlertTask.__table__
    alert_unique_sets = {
        frozenset(constraint.columns.keys())
        for constraint in alert_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert frozenset(ALERT_TASK_UNIQUE_COLUMNS) in alert_unique_sets
    assert alert_table.dialect_options["mysql"]["collate"] == "utf8mb4_general_ci"
    assert alert_table.c.market.nullable is False
    assert alert_table.c.task_name.nullable is False

    zx_table = db_module.TableByZxGroup.__table__
    zx_unique_sets = {
        frozenset(constraint.columns.keys())
        for constraint in zx_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert frozenset({"market", "zx_group"}) in zx_unique_sets
    assert zx_table.dialect_options["mysql"]["collate"] == "utf8mb4_general_ci"

    ddl = str(CreateTable(alert_table).compile(dialect=mysql.dialect()))
    assert "UNIQUE (market, task_name)" in ddl
    assert "COLLATE utf8mb4_general_ci" in ddl

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'dynamic.sqlite'}")
    database = object.__new__(db_module.DB.__wrapped__)
    database.engine = engine
    database.Session = sessionmaker(bind=engine)
    database._DB__cache_tables = {}
    kline_table = database.klines_tables("a", "SH.600000").__table__
    kline_unique_sets = {
        frozenset(constraint.columns.keys())
        for constraint in kline_table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert frozenset({"code", "dt", "f"}) in kline_unique_sets
    assert kline_table.dialect_options["mysql"]["collate"] == "utf8mb4_general_ci"



def test_db_startup_automatically_migrates_legacy_alert_tasks(tmp_path, monkeypatch):
    _install_demo_config_if_needed()
    db_module = importlib.import_module("tradingview_zy.db")
    config_module = importlib.import_module("tradingview_zy.config")

    monkeypatch.setattr(config_module, "DB_TYPE", "sqlite")
    monkeypatch.setattr(config_module, "DATA_PATH", str(tmp_path))
    monkeypatch.setattr(config_module, "DB_DATABASE", "legacy-hi03")

    db_dir = tmp_path / "db"
    db_dir.mkdir(parents=True)
    db_file = db_dir / "legacy-hi03.sqlite"
    legacy_engine = create_engine(f"sqlite+pysqlite:///{db_file}")
    table = _legacy_alert_task_table(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(
            table.insert(),
            [
                {"id": 1, "market": "a", "task_name": "重复任务", "is_run": 1},
                {"id": 2, "market": "a", "task_name": "重复任务", "is_run": 1},
            ],
        )
    legacy_engine.dispose()

    database = db_module.DB.__wrapped__()
    try:
        assert alert_task_unique_key_exists(database.engine)
        migrated_table = Table(
            "cl_alert_task", MetaData(), autoload_with=database.engine
        )
        with database.engine.connect() as connection:
            tasks = connection.execute(
                select(
                    migrated_table.c.id,
                    migrated_table.c.task_name,
                    migrated_table.c.is_run,
                ).order_by(migrated_table.c.id)
            ).mappings().all()
        assert len(tasks) == 2
        assert sum(task["is_run"] == 1 for task in tasks) == 1
        assert sum(
            "duplicate-disabled" in task["task_name"] for task in tasks
        ) == 1
    finally:
        database.engine.dispose()

def test_repository_rejects_duplicate_create_and_conflicting_rename(tmp_path):
    _install_demo_config_if_needed()
    db_module = importlib.import_module("tradingview_zy.db")

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'repository.sqlite'}")
    db_module.Base.metadata.create_all(engine)
    database = object.__new__(db_module.DB.__wrapped__)
    database.engine = engine
    database.Session = sessionmaker(bind=engine)
    database._DB__cache_tables = {}

    def save(name: str) -> None:
        database.task_save_strategy(
            market="a",
            task_name=name,
            zx_group="我的关注",
            frequency="5m",
            interval_minutes=5,
            strategy_config="{}",
            strategy_memo="",
            is_run=1,
            is_send_msg=0,
        )

    save("  突破监控  ")
    with pytest.raises(db_module.AlertTaskAlreadyExistsError, match="已存在"):
        save("突破监控")
    save("均线监控")

    with database.Session() as session:
        tasks = session.query(db_module.TableByAlertTask).order_by(
            db_module.TableByAlertTask.id
        ).all()
        first_id, second_id = tasks[0].id, tasks[1].id
        assert [task.task_name for task in tasks] == ["突破监控", "均线监控"]

    with pytest.raises(db_module.AlertTaskAlreadyExistsError, match="已存在"):
        database.task_update_strategy(
            id=second_id,
            market="a",
            task_name="突破监控",
            zx_group="我的关注",
            frequency="5m",
            interval_minutes=5,
            strategy_config="{}",
            strategy_memo="",
            is_run=1,
            is_send_msg=0,
        )

    with database.Session() as session:
        names = {
            task.id: task.task_name
            for task in session.query(db_module.TableByAlertTask).all()
        }
    assert names[first_id] == "突破监控"
    assert names[second_id] == "均线监控"


def test_unique_index_name_and_columns_are_visible_to_sqlalchemy_inspector():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    table = _legacy_alert_task_table(engine)
    ensure_alert_task_unique_key(engine)

    inspector = inspect(engine)
    assert frozenset(ALERT_TASK_UNIQUE_COLUMNS) in _unique_column_sets(
        inspector, table.name
    )
    assert any(
        index.get("name") == ALERT_TASK_UNIQUE_INDEX_NAME and index.get("unique")
        for index in inspector.get_indexes(table.name)
    )



def test_same_task_name_is_allowed_in_different_markets_and_same_row_can_keep_name(tmp_path):
    _install_demo_config_if_needed()
    db_module = importlib.import_module("tradingview_zy.db")

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'market-scope.sqlite'}")
    db_module.Base.metadata.create_all(engine)
    database = object.__new__(db_module.DB.__wrapped__)
    database.engine = engine
    database.Session = sessionmaker(bind=engine)
    database._DB__cache_tables = {}

    common = {
        "task_name": "突破监控",
        "zx_group": "我的关注",
        "frequency": "5m",
        "interval_minutes": 5,
        "strategy_config": "{}",
        "strategy_memo": "",
        "is_run": 1,
        "is_send_msg": 0,
    }
    database.task_save_strategy(market="a", **common)
    database.task_save_strategy(market="hk", **common)

    with database.Session() as session:
        a_task = session.query(db_module.TableByAlertTask).filter_by(market="a").one()

    assert database.task_update_strategy(
        id=a_task.id,
        market="a",
        **common,
    ) is True

    with database.Session() as session:
        rows = session.query(db_module.TableByAlertTask).order_by(
            db_module.TableByAlertTask.market
        ).all()
    assert [(row.market, row.task_name) for row in rows] == [
        ("a", "突破监控"),
        ("hk", "突破监控"),
    ]


@pytest.mark.parametrize(
    ("market", "task_name", "message"),
    [
        ("", "有效名称", "必须指定市场"),
        ("a", "   ", "名称不能为空"),
        ("a", "x" * 101, "不能超过 100"),
    ],
)
def test_alert_task_identity_validation_rejects_invalid_business_keys(
    market, task_name, message
):
    _install_demo_config_if_needed()
    db_module = importlib.import_module("tradingview_zy.db")
    with pytest.raises(db_module.AlertTaskValidationError, match=message):
        db_module.DB.__wrapped__._normalise_alert_task_identity(market, task_name)

def test_alert_save_route_returns_actionable_duplicate_message(monkeypatch):
    _install_demo_config_if_needed()
    web_root = ROOT / "web" / "tradingview_zy_chart"
    if str(web_root) not in sys.path:
        sys.path.insert(0, str(web_root))

    cl_app = importlib.import_module("cl_app")
    alert_tasks_module = importlib.import_module("cl_app.alert_tasks")
    db_module = importlib.import_module("tradingview_zy.db")

    class FakeExchange:
        @staticmethod
        def support_frequencys():
            return {"5m": "5分钟"}

        @staticmethod
        def default_code():
            return "SH.000001"

    class FakeScheduler:
        def __init__(self, *args, **kwargs):
            self.my_task_list = {}

        def add_executor(self, *args, **kwargs):
            return None

        def add_listener(self, *args, **kwargs):
            return None

        def start(self):
            return None

        def get_job(self, *args, **kwargs):
            return None

        def remove_job(self, *args, **kwargs):
            return None

    class DuplicateDB:
        @staticmethod
        def task_query(*args, **kwargs):
            return []

        @staticmethod
        def task_save_strategy(**kwargs):
            raise db_module.AlertTaskAlreadyExistsError(
                "市场 'a' 已存在名为 '突破监控' 的监控任务"
            )

    monkeypatch.setattr(cl_app, "get_exchange", lambda market: FakeExchange())
    monkeypatch.setattr(cl_app, "TornadoScheduler", FakeScheduler)
    monkeypatch.setattr(alert_tasks_module, "db", DuplicateDB())
    if hasattr(cl_app, "validate_registered_strategy"):
        monkeypatch.setattr(
            cl_app, "validate_registered_strategy", lambda *args, **kwargs: None
        )

    app = cl_app.create_app(
        {
            "TESTING": True,
            "WEB_HOST": "127.0.0.1",
            "LOGIN_PWD": "",
            "LOGIN_PWD_HASH": "",
            "WEB_SECRET_KEY": "h" * 48,
        }
    )
    app.config.update(TESTING=True)
    client = app.test_client()
    assert client.get("/login").status_code == 302

    response = client.post(
        "/alert_save",
        data={
            "id": "",
            "market": "a",
            "task_name": "突破监控",
            "interval_minutes": "5",
            "zx_group": "我的关注",
            "frequency": "5m",
            "strategy_id": "safe",
            "strategy_path": "tests.fake:Strategy",
            "strategy_kwargs": "{}",
            "strategy_memo": "",
            "is_send_msg": "0",
            "is_run": "1",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "ok": False,
        "msg": "市场 'a' 已存在名为 '突破监控' 的监控任务",
    }
