from __future__ import annotations

import importlib
import math
import sys
import types
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from tradingview_zy.alert_strategy_storage import (
    STRATEGY_CONFIG_MAX_BYTES,
    STRATEGY_MEMO_MAX_BYTES,
    StrategyStorageValidationError,
    build_strategy_config,
    normalize_strategy_config,
    normalize_strategy_memo,
    parse_strategy_kwargs,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"


def _load_db(tmp_path):
    for name in ["tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config"]:
        sys.modules.pop(name, None)
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: timezone.utc
    sys.modules["tzlocal"] = tzlocal

    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "nx10"
    config.DB_HOST = "127.0.0.1"
    config.DB_PORT = 3306
    config.DB_USER = "user"
    config.DB_PWD = "password"
    config.get_data_path = lambda: tmp_path
    sys.modules["tradingview_zy.config"] = config
    package = importlib.import_module("tradingview_zy")
    package.config = config
    return importlib.import_module("tradingview_zy.db")


def test_strategy_json_contract_rejects_non_objects_nonfinite_and_byte_overflow() -> None:
    assert parse_strategy_kwargs('{"window": 20}') == {"window": 20}
    assert '"strategy_id":"demo"' in build_strategy_config("demo", {"window": 20})

    for raw in ["[]", "NaN", '{"x": NaN}', '{"x": Infinity}']:
        with pytest.raises(StrategyStorageValidationError):
            parse_strategy_kwargs(raw)

    with pytest.raises(StrategyStorageValidationError):
        normalize_strategy_config({"x": math.inf})
    with pytest.raises(StrategyStorageValidationError):
        normalize_strategy_config({1: "not-a-string-key"})
    with pytest.raises(StrategyStorageValidationError):
        parse_strategy_kwargs("中" * (STRATEGY_CONFIG_MAX_BYTES // 3 + 1))


def test_strategy_memo_uses_utf8_bytes_and_rejects_nul() -> None:
    assert normalize_strategy_memo("备注") == "备注"
    with pytest.raises(StrategyStorageValidationError):
        normalize_strategy_memo("bad\x00memo")
    with pytest.raises(StrategyStorageValidationError):
        normalize_strategy_memo("中" * (STRATEGY_MEMO_MAX_BYTES // 3 + 1))


def test_legacy_alert_table_migration_is_idempotent_and_backfills(tmp_path) -> None:
    module = _load_db(tmp_path / "bootstrap")
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE cl_alert_task (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market VARCHAR(20),
                    task_name VARCHAR(100),
                    check_idx_ma_info VARCHAR(200),
                    check_idx_macd_info VARCHAR(200)
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO cl_alert_task "
                "(market, task_name, check_idx_ma_info, check_idx_macd_info) "
                "VALUES ('a', 'legacy', '{\"strategy_id\":\"old\"}', 'old memo')"
            )
        )

    module.migrate_alert_strategy_storage(engine)
    module.migrate_alert_strategy_storage(engine)

    columns = {item["name"]: item["type"] for item in inspect(engine).get_columns("cl_alert_task")}
    assert "strategy_config" in columns
    assert "strategy_memo" in columns
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT strategy_config, strategy_memo FROM cl_alert_task")
        ).one()
    assert row.strategy_config == '{"strategy_id":"old"}'
    assert row.strategy_memo == "old memo"
    engine.dispose()
    module.db.engine.dispose()


def test_long_strategy_config_and_memo_round_trip_through_dedicated_text_columns(tmp_path) -> None:
    module = _load_db(tmp_path)
    config_text = build_strategy_config("demo", {"message": "中" * 500, "window": 20})
    memo = "备注" * 300
    assert len(config_text) > 200
    assert len(memo) > 200

    assert module.db.task_save_strategy(
        market="a",
        task_name="long",
        zx_group="watch",
        frequency="d",
        interval_minutes=5,
        strategy_config=config_text,
        strategy_memo=memo,
        is_run=1,
        is_send_msg=1,
    )
    row = module.db.task_query(market="a")[0]
    assert row.strategy_config == config_text
    assert row.strategy_memo == memo
    assert row.strategy_config_text == config_text
    assert row.strategy_memo_text == memo
    assert row.check_idx_ma_info in (None, "")
    assert row.check_idx_macd_info in (None, "")

    updated = build_strategy_config("demo", {"message": "新" * 600})
    assert module.db.task_update_strategy(
        id=row.id,
        market="a",
        task_name="long",
        zx_group="watch",
        frequency="30m",
        interval_minutes=10,
        strategy_config=updated,
        strategy_memo="更新" * 250,
        is_run=0,
        is_send_msg=0,
    )
    current = module.db.task_query(id=row.id)[0]
    assert current.strategy_config == updated
    assert current.strategy_memo == "更新" * 250
    module.db.engine.dispose()


def test_save_detects_database_side_truncation(tmp_path) -> None:
    module = _load_db(tmp_path)

    def truncate_before_flush(session, flush_context, instances):
        for obj in session.new:
            if isinstance(obj, module.TableByAlertTask) and obj.strategy_config_text:
                obj.strategy_config_text = obj.strategy_config_text[:20]

    event.listen(module.db.Session, "before_flush", truncate_before_flush)
    try:
        with pytest.raises(RuntimeError, match="round-trip"):
            module.db.task_save_strategy(
                market="a",
                task_name="truncated",
                zx_group="watch",
                frequency="d",
                interval_minutes=5,
                strategy_config=build_strategy_config("demo", {"value": "x" * 200}),
                strategy_memo="memo",
                is_run=1,
                is_send_msg=1,
            )
    finally:
        event.remove(module.db.Session, "before_flush", truncate_before_flush)
    assert module.db.task_query(market="a") == []
    module.db.engine.dispose()


def test_schema_and_web_route_use_new_storage_boundary_before_persistence(tmp_path) -> None:
    module = _load_db(tmp_path)
    ddl = str(CreateTable(module.TableByAlertTask.__table__).compile(dialect=mysql.dialect()))
    assert "strategy_config TEXT" in ddl
    assert "strategy_memo TEXT" in ddl

    source = WEB_APP.read_text(encoding="utf-8")
    parse_pos = source.index("parse_strategy_kwargs(request.form.get")
    validate_pos = source.index("validate_registered_strategy(", parse_pos)
    build_pos = source.index("build_strategy_config(strategy_id, strategy_kwargs)", validate_pos)
    save_pos = source.index("_alert_tasks.alert_save(alert_config)", build_pos)
    assert parse_pos < validate_pos < build_pos < save_pos
    module.db.engine.dispose()
