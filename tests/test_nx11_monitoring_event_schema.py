from __future__ import annotations

import datetime as dt
import importlib
import math
import sys
import types
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from tradingview_zy.monitoring_events import (
    MonitoringEventType,
    legacy_action,
    legacy_event_type,
    legacy_score,
    normalize_monitoring_action,
    normalize_monitoring_event,
    normalize_monitoring_event_type,
    normalize_monitoring_score,
)
from tradingview_zy.strategies.base import StrategyAction

ROOT = Path(__file__).resolve().parents[1]
ALERT_TASKS = ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "alert_tasks.py"
ALERT_JS = ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "static" / "js" / "alert.js"


def _load_db(tmp_path):
    for name in ["tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config"]:
        sys.modules.pop(name, None)
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: timezone.utc
    sys.modules["tzlocal"] = tzlocal

    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "nx11"
    config.DB_HOST = "127.0.0.1"
    config.DB_PORT = 3306
    config.DB_USER = "user"
    config.DB_PWD = "password"
    config.get_data_path = lambda: tmp_path
    sys.modules["tradingview_zy.config"] = config
    package = importlib.import_module("tradingview_zy")
    package.config = config
    return importlib.import_module("tradingview_zy.db")


def test_monitoring_event_domain_accepts_only_persistable_actions_and_finite_scores() -> None:
    assert normalize_monitoring_event_type("strategy_signal") is MonitoringEventType.STRATEGY_SIGNAL
    assert normalize_monitoring_action("watch") is StrategyAction.WATCH
    assert normalize_monitoring_score(123456789.123456) == 123456789.123456
    assert normalize_monitoring_event(
        event_type=MonitoringEventType.STRATEGY_SIGNAL,
        action=StrategyAction.CLOSE,
        score=-0.25,
    ).score == -0.25

    for value in ["sig", "unknown", "x" * 100]:
        with pytest.raises(ValueError):
            normalize_monitoring_event_type(value)
    for value in [StrategyAction.SELECT, StrategyAction.IGNORE, "unknown"]:
        with pytest.raises(ValueError):
            normalize_monitoring_action(value)
    for value in [True, "1.0", math.nan, math.inf, -math.inf]:
        with pytest.raises((TypeError, ValueError)):
            normalize_monitoring_score(value)  # type: ignore[arg-type]


def test_legacy_conversion_is_explicit_and_fail_closed() -> None:
    assert legacy_event_type("sig") is MonitoringEventType.STRATEGY_SIGNAL
    assert legacy_event_type("signal") is MonitoringEventType.STRATEGY_SIGNAL
    assert legacy_event_type("legacy-unknown") is None
    assert legacy_action("buy") is StrategyAction.BUY
    assert legacy_action("select") is None
    assert legacy_score("1.235e+08") == 123500000.0
    assert legacy_score("not-a-number") is None
    assert legacy_score("nan") is None


def test_legacy_alert_record_migration_is_idempotent_and_backfills_only_known_values(tmp_path) -> None:
    module = _load_db(tmp_path / "bootstrap")
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-alerts.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE cl_alert_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market VARCHAR(20), stock_code VARCHAR(20), frequency VARCHAR(10),
                    line_type VARCHAR(5), bi_is_done VARCHAR(10), bi_is_td VARCHAR(10),
                    line_dt DATETIME
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO cl_alert_record "
                "(market,stock_code,frequency,line_type,bi_is_done,bi_is_td) VALUES "
                "('a','SH.1','d','sig','watch','0.9877'),"
                "('a','SH.2','d','signal','buy','1.235e+08'),"
                "('a','SH.3','d','other','select','NaN')"
            )
        )

    module.migrate_alert_event_storage(engine)
    module.migrate_alert_event_storage(engine)

    columns = {item["name"]: item["type"] for item in inspect(engine).get_columns("cl_alert_record")}
    assert {"event_type", "action", "score"} <= set(columns)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT event_type,action,score,line_type,bi_is_done,bi_is_td "
                "FROM cl_alert_record ORDER BY id"
            )
        ).mappings().all()
    assert rows[0]["event_type"] == "strategy_signal"
    assert rows[0]["action"] == "watch"
    assert rows[0]["score"] == pytest.approx(0.9877)
    assert rows[1]["event_type"] == "strategy_signal"
    assert rows[1]["action"] == "buy"
    assert rows[1]["score"] == pytest.approx(123500000.0)
    assert rows[2]["event_type"] is None
    assert rows[2]["action"] is None
    assert rows[2]["score"] is None
    indexes = {item["name"] for item in inspect(engine).get_indexes("cl_alert_record")}
    assert "table_alert_record_event_lookup_idx" in indexes
    engine.dispose()
    module.db.engine.dispose()


@pytest.mark.parametrize("action", ["watch", "buy", "sell", "open", "close"])
def test_new_monitoring_events_round_trip_in_typed_columns_without_legacy_writes(tmp_path, action) -> None:
    module = _load_db(tmp_path / action)
    score = 123456789.123456
    event_time = dt.datetime(2026, 8, 4, 13, 45, tzinfo=timezone.utc)

    assert module.db.alert_event_save(
        market="a",
        task_name=f"task-{action}",
        stock_code="SH.000001",
        stock_name="上证指数",
        frequency="d",
        alert_msg="typed signal",
        action=action,
        score=score,
        event_type=MonitoringEventType.STRATEGY_SIGNAL,
        event_time=event_time,
    )

    with module.db.Session() as session:
        record = session.scalar(
            select(module.TableByAlertRecord).where(
                module.TableByAlertRecord.task_name == f"task-{action}"
            )
        )
        assert record is not None
        assert record.event_type_text == "strategy_signal"
        assert record.action_text == action
        assert record.score_value == score
        assert record.event_type == "strategy_signal"
        assert record.action == action
        assert record.score == score
        assert record.line_type is None
        assert record.bi_is_done is None
        assert record.bi_is_td is None
        assert record.event_time == event_time.replace(tzinfo=None)

    found = module.db.alert_record_query_by_code(
        "a", "SH.000001", "d", "sig", event_time.replace(tzinfo=None)
    )
    assert found is not None
    module.db.engine.dispose()


def test_legacy_wrapper_parses_known_values_and_rejects_unknown_without_partial_write(tmp_path) -> None:
    module = _load_db(tmp_path)
    event_time = dt.datetime(2026, 8, 4, 13, 45)
    assert module.db.alert_record_save(
        market="a", task_name="legacy", stock_code="SH.1", stock_name="A",
        frequency="d", alert_msg="legacy", bi_is_done="watch", bi_is_td="0.5",
        line_type="sig", line_dt=event_time,
    )
    with pytest.raises(ValueError):
        module.db.alert_record_save(
            market="a", task_name="bad", stock_code="SH.2", stock_name="B",
            frequency="d", alert_msg="bad", bi_is_done="select", bi_is_td="1",
            line_type="sig", line_dt=event_time,
        )
    assert [row.task_name for row in module.db.alert_record_query("a")] == ["legacy"]
    module.db.engine.dispose()


def test_invalid_generic_values_fail_before_any_row_is_committed(tmp_path) -> None:
    module = _load_db(tmp_path)
    kwargs = dict(
        market="a", task_name="invalid", stock_code="SH.000001", stock_name="上证指数",
        frequency="d", alert_msg="invalid", event_type=MonitoringEventType.STRATEGY_SIGNAL,
        event_time=dt.datetime(2026, 8, 4, 13, 45),
    )
    with pytest.raises(ValueError):
        module.db.alert_event_save(action="select", score=1.0, **kwargs)
    with pytest.raises(ValueError):
        module.db.alert_event_save(action="watch", score=math.inf, **kwargs)
    with pytest.raises(TypeError):
        module.db.alert_event_save(action="watch", score="1.0", **kwargs)
    with module.db.Session() as session:
        assert session.query(module.TableByAlertRecord).count() == 0
    module.db.engine.dispose()


def test_corrupt_typed_values_do_not_fall_back_to_legacy_columns(tmp_path) -> None:
    module = _load_db(tmp_path)
    record = module.TableByAlertRecord(
        event_type_text="unknown",
        action_text="unknown",
        score_value=math.nan,
        line_type="sig",
        bi_is_done="watch",
        bi_is_td="0.5",
    )
    assert record.event_type == ""
    assert record.action == ""
    assert record.score is None
    module.db.engine.dispose()


def test_model_uses_independent_event_action_and_double_precision_score_columns(tmp_path) -> None:
    module = _load_db(tmp_path)
    ddl = str(CreateTable(module.TableByAlertRecord.__table__).compile(dialect=mysql.dialect()))
    assert "event_type VARCHAR(32)" in ddl
    assert "action VARCHAR(16)" in ddl
    assert "score FLOAT(53)" in ddl or "score DOUBLE" in ddl
    assert "line_type VARCHAR(5)" in ddl
    module.db.engine.dispose()


def test_legacy_migration_selects_double_for_mysql_and_float_elsewhere(tmp_path) -> None:
    module = _load_db(tmp_path)
    assert module._alert_event_score_sql_type("mysql") == "DOUBLE"
    assert module._alert_event_score_sql_type("sqlite") == "FLOAT"
    module.db.engine.dispose()


def test_alert_task_and_frontend_keep_numeric_score_without_truthiness_loss() -> None:
    source = ALERT_TASKS.read_text(encoding="utf-8")
    assert "score=event.score" in source
    assert "MonitoringEventType.STRATEGY_SIGNAL" in source
    assert 'score=f"{event.score:.4g}"[:10]' not in source
    js = ALERT_JS.read_text(encoding="utf-8")
    assert 'd.score === null || d.score === undefined ? "" : d.score' in js
