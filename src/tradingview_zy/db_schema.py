from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Index, MetaData, Table, func, inspect, select, update
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import CreateIndex

ALERT_TASK_TABLE_NAME = "cl_alert_task"
ALERT_TASK_UNIQUE_COLUMNS = ("market", "task_name")
ALERT_TASK_UNIQUE_INDEX_NAME = "uq_cl_alert_task_market_task_name"
ALERT_TASK_NAME_MAX_LENGTH = 100

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertTaskDuplicateResolution:
    """Describe one legacy duplicate task that was preserved but disabled."""

    market: str | None
    original_task_name: str | None
    kept_id: int
    disabled_id: int
    disabled_task_name: str


@dataclass(frozen=True)
class AlertTaskUniqueMigrationResult:
    unique_key_created: bool
    resolved_duplicates: tuple[AlertTaskDuplicateResolution, ...] = ()


def _same_columns(candidate: list[str] | tuple[str, ...] | None) -> bool:
    if not candidate or len(candidate) != len(ALERT_TASK_UNIQUE_COLUMNS):
        return False
    return set(candidate) == set(ALERT_TASK_UNIQUE_COLUMNS)


def alert_task_unique_key_exists(bind: Engine | Connection) -> bool:
    """Return whether the physical table already enforces the business key."""

    inspector = inspect(bind)
    if ALERT_TASK_TABLE_NAME not in inspector.get_table_names():
        return False

    for constraint in inspector.get_unique_constraints(ALERT_TASK_TABLE_NAME):
        if _same_columns(constraint.get("column_names")):
            return True
    for index in inspector.get_indexes(ALERT_TASK_TABLE_NAME):
        if index.get("unique") and _same_columns(index.get("column_names")):
            return True
    return False


def _row_order_key(row: dict[str, Any]) -> tuple[bool, bool, str, int]:
    dt = row.get("dt")
    if isinstance(dt, datetime.datetime):
        dt_value = dt.isoformat()
    elif dt is None:
        dt_value = ""
    else:
        dt_value = str(dt)
    return row.get("is_run") == 1, dt is not None, dt_value, int(row["id"])


def _name_key(market: str | None, task_name: str | None) -> tuple[str, str]:
    # MySQL's configured utf8mb4_general_ci collation is case-insensitive and
    # ignores trailing spaces for ordinary VARCHAR comparisons. Being
    # conservative here prevents the migration from generating a name that
    # MySQL would still consider equal to an existing name.
    return (market or "").casefold().rstrip(), (task_name or "").casefold().rstrip()


def _disabled_duplicate_name(
    original_name: str | None,
    row_id: int,
    market: str | None,
    used_names: set[tuple[str, str]],
) -> str:
    base = (original_name or "未命名任务").strip() or "未命名任务"
    attempt = 1
    while True:
        suffix = f" [duplicate-disabled-{row_id}]"
        if attempt > 1:
            suffix = f" [duplicate-disabled-{row_id}-{attempt}]"
        prefix_length = max(ALERT_TASK_NAME_MAX_LENGTH - len(suffix), 0)
        candidate = f"{base[:prefix_length]}{suffix}"
        key = _name_key(market, candidate)
        if key not in used_names:
            used_names.add(key)
            return candidate
        attempt += 1


def _where_equal(column, value):
    return column.is_(None) if value is None else column == value


def _resolve_duplicate_alert_tasks(
    connection: Connection, table: Table
) -> tuple[AlertTaskDuplicateResolution, ...]:
    duplicate_groups = connection.execute(
        select(
            table.c.market,
            table.c.task_name,
            func.count(table.c.id).label("row_count"),
        )
        .group_by(table.c.market, table.c.task_name)
        .having(func.count(table.c.id) > 1)
    ).mappings().all()

    if not duplicate_groups:
        return ()

    used_names = {
        _name_key(row.market, row.task_name)
        for row in connection.execute(
            select(table.c.market, table.c.task_name)
        ).all()
    }
    resolutions: list[AlertTaskDuplicateResolution] = []

    for group in duplicate_groups:
        rows = connection.execute(
            select(
                table.c.id,
                table.c.dt,
                table.c.market,
                table.c.task_name,
                table.c.is_run,
            ).where(
                _where_equal(table.c.market, group["market"]),
                _where_equal(table.c.task_name, group["task_name"]),
            )
        ).mappings().all()
        ordered_rows = sorted(rows, key=_row_order_key, reverse=True)
        kept = ordered_rows[0]

        for duplicate in ordered_rows[1:]:
            disabled_name = _disabled_duplicate_name(
                duplicate["task_name"],
                int(duplicate["id"]),
                duplicate["market"],
                used_names,
            )
            values: dict[str, Any] = {"task_name": disabled_name}
            if "is_run" in table.c:
                values["is_run"] = 0
            connection.execute(
                update(table).where(table.c.id == duplicate["id"]).values(**values)
            )
            resolution = AlertTaskDuplicateResolution(
                market=duplicate["market"],
                original_task_name=duplicate["task_name"],
                kept_id=int(kept["id"]),
                disabled_id=int(duplicate["id"]),
                disabled_task_name=disabled_name,
            )
            resolutions.append(resolution)
            logger.warning(
                "检测到历史重复监控任务：market=%r task_name=%r。保留 id=%s；"
                "将 id=%s 重命名为 %r 并停用，避免升级后重复调度。",
                resolution.market,
                resolution.original_task_name,
                resolution.kept_id,
                resolution.disabled_id,
                resolution.disabled_task_name,
            )

    return tuple(resolutions)


def _create_alert_task_unique_index(connection: Connection, table: Table) -> None:
    existing_names = {
        index.get("name")
        for index in inspect(connection).get_indexes(ALERT_TASK_TABLE_NAME)
    }
    if ALERT_TASK_UNIQUE_INDEX_NAME in existing_names:
        raise RuntimeError(
            f"数据库索引 {ALERT_TASK_UNIQUE_INDEX_NAME!r} 已存在，但没有覆盖 "
            f"{ALERT_TASK_UNIQUE_COLUMNS!r}；请先人工检查该索引"
        )

    index = Index(
        ALERT_TASK_UNIQUE_INDEX_NAME,
        table.c.market,
        table.c.task_name,
        unique=True,
    )
    connection.execute(CreateIndex(index))


def ensure_alert_task_unique_key(engine: Engine) -> AlertTaskUniqueMigrationResult:
    """Upgrade a legacy alert-task table to enforce ``(market, task_name)``.

    New databases receive the constraint from SQLAlchemy metadata. Existing
    databases are different: ``create_all()`` never alters an existing table.
    This migration therefore performs three safe, idempotent steps:

    1. Detect whether a unique constraint/index already exists.
    2. Preserve legacy duplicate rows by preferring an active row and then the
       most recently modified row, while renaming and disabling the others.
    3. Add a physical unique index so concurrent writers cannot reintroduce
       duplicates.
    """

    inspector = inspect(engine)
    if ALERT_TASK_TABLE_NAME not in inspector.get_table_names():
        return AlertTaskUniqueMigrationResult(unique_key_created=False)
    if alert_task_unique_key_exists(engine):
        return AlertTaskUniqueMigrationResult(unique_key_created=False)

    metadata = MetaData()
    table = Table(ALERT_TASK_TABLE_NAME, metadata, autoload_with=engine)
    missing_columns = set(ALERT_TASK_UNIQUE_COLUMNS) - set(table.c.keys())
    if missing_columns:
        raise RuntimeError(
            f"表 {ALERT_TASK_TABLE_NAME} 缺少迁移所需字段：{sorted(missing_columns)}"
        )

    with engine.begin() as connection:
        resolutions = _resolve_duplicate_alert_tasks(connection, table)
        if not alert_task_unique_key_exists(connection):
            _create_alert_task_unique_index(connection, table)

    if not alert_task_unique_key_exists(engine):
        raise RuntimeError(
            f"未能为 {ALERT_TASK_TABLE_NAME} 创建 {ALERT_TASK_UNIQUE_COLUMNS} 唯一键"
        )
    return AlertTaskUniqueMigrationResult(
        unique_key_created=True,
        resolved_duplicates=resolutions,
    )
