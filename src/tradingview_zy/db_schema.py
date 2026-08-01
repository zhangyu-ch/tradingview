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

# ---------------------------------------------------------------------------
# v6 data-integrity migrations
# ---------------------------------------------------------------------------
import hashlib

from sqlalchemy import text

TV_MARKS_PRICE_TABLE_NAME = "cl_tv_marks_price"
TV_MARKS_PRICE_UNIQUE_COLUMNS = ("market", "stock_code", "mark_time", "mark_label")
TV_MARKS_PRICE_UNIQUE_INDEX_NAME = "uq_cl_tv_marks_price_business_key"
ALERT_RECORD_TABLE_NAME = "cl_alert_record"
ALERT_RECORD_EVENT_KEY_COLUMN = "event_key"
ALERT_RECORD_UNIQUE_INDEX_NAME = "uq_cl_alert_record_event_key"


@dataclass(frozen=True)
class UniqueKeyMigrationResult:
    table: str
    created: bool
    duplicates_removed: int = 0
    rows_backfilled: int = 0


def _normalise_event_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        value = value.replace(tzinfo=None, microsecond=0)
        return value.isoformat(sep=" ")
    return str(value)


def build_alert_event_key(
    *,
    market: str,
    task_name: str,
    stock_code: str,
    frequency: str,
    action: str,
    score: str,
    event_type: str,
    event_time: Any,
) -> str:
    """Return a stable event identity independent from polling time."""
    # Score and display text may be recalculated on every poll. They are
    # deliberately excluded from identity so one logical signal remains one
    # event even when its presentation metadata changes.
    fields = (
        market,
        task_name,
        stock_code,
        frequency,
        action,
        event_type,
        _normalise_event_time(event_time),
    )
    payload = "\x1f".join("" if value is None else str(value).strip() for value in fields)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _has_unique_columns(bind: Engine | Connection, table_name: str, columns: tuple[str, ...]) -> bool:
    inspector = inspect(bind)
    expected = set(columns)
    for constraint in inspector.get_unique_constraints(table_name):
        if set(constraint.get("column_names") or ()) == expected:
            return True
    for index in inspector.get_indexes(table_name):
        if index.get("unique") and set(index.get("column_names") or ()) == expected:
            return True
    return False


def ensure_tv_marks_price_unique_key(engine: Engine) -> UniqueKeyMigrationResult:
    inspector = inspect(engine)
    if TV_MARKS_PRICE_TABLE_NAME not in inspector.get_table_names():
        return UniqueKeyMigrationResult(TV_MARKS_PRICE_TABLE_NAME, False)
    if _has_unique_columns(engine, TV_MARKS_PRICE_TABLE_NAME, TV_MARKS_PRICE_UNIQUE_COLUMNS):
        return UniqueKeyMigrationResult(TV_MARKS_PRICE_TABLE_NAME, False)

    metadata = MetaData()
    table = Table(TV_MARKS_PRICE_TABLE_NAME, metadata, autoload_with=engine)
    missing = set(TV_MARKS_PRICE_UNIQUE_COLUMNS) - set(table.c.keys())
    if missing:
        raise RuntimeError(f"{TV_MARKS_PRICE_TABLE_NAME} 缺少字段 {sorted(missing)}")

    removed = 0
    with engine.begin() as connection:
        groups = connection.execute(
            select(
                *(table.c[name] for name in TV_MARKS_PRICE_UNIQUE_COLUMNS),
                func.max(table.c.id).label("keep_id"),
                func.count(table.c.id).label("row_count"),
            )
            .group_by(*(table.c[name] for name in TV_MARKS_PRICE_UNIQUE_COLUMNS))
            .having(func.count(table.c.id) > 1)
        ).mappings().all()
        for group in groups:
            filters = [
                _where_equal(table.c[name], group[name])
                for name in TV_MARKS_PRICE_UNIQUE_COLUMNS
            ]
            result = connection.execute(
                table.delete().where(*filters, table.c.id != group["keep_id"])
            )
            removed += int(result.rowcount or 0)
        index = Index(
            TV_MARKS_PRICE_UNIQUE_INDEX_NAME,
            *(table.c[name] for name in TV_MARKS_PRICE_UNIQUE_COLUMNS),
            unique=True,
        )
        connection.execute(CreateIndex(index))

    if not _has_unique_columns(engine, TV_MARKS_PRICE_TABLE_NAME, TV_MARKS_PRICE_UNIQUE_COLUMNS):
        raise RuntimeError("价格标记唯一键迁移失败")
    return UniqueKeyMigrationResult(TV_MARKS_PRICE_TABLE_NAME, True, removed)


def ensure_alert_record_event_key(engine: Engine) -> UniqueKeyMigrationResult:
    inspector = inspect(engine)
    if ALERT_RECORD_TABLE_NAME not in inspector.get_table_names():
        return UniqueKeyMigrationResult(ALERT_RECORD_TABLE_NAME, False)

    columns = {column["name"] for column in inspector.get_columns(ALERT_RECORD_TABLE_NAME)}
    added_column = ALERT_RECORD_EVENT_KEY_COLUMN not in columns
    with engine.begin() as connection:
        if added_column:
            connection.execute(
                text(
                    f"ALTER TABLE {ALERT_RECORD_TABLE_NAME} "
                    f"ADD COLUMN {ALERT_RECORD_EVENT_KEY_COLUMN} VARCHAR(64)"
                )
            )

    metadata = MetaData()
    table = Table(ALERT_RECORD_TABLE_NAME, metadata, autoload_with=engine)
    backfilled = 0
    removed = 0
    with engine.begin() as connection:
        rows = connection.execute(select(table)).mappings().all()
        seen: dict[str, int] = {}
        for row in rows:
            key = row.get(ALERT_RECORD_EVENT_KEY_COLUMN) or build_alert_event_key(
                market=row.get("market") or "",
                task_name=row.get("task_name") or "",
                stock_code=row.get("stock_code") or "",
                frequency=row.get("frequency") or "",
                action=row.get("bi_is_done") or "",
                score=row.get("bi_is_td") or "",
                event_type=row.get("line_type") or "",
                event_time=row.get("line_dt"),
            )
            previous = seen.get(key)
            if previous is None or int(row["id"]) > previous:
                if previous is not None:
                    connection.execute(table.delete().where(table.c.id == previous))
                    removed += 1
                seen[key] = int(row["id"])
                if row.get(ALERT_RECORD_EVENT_KEY_COLUMN) != key:
                    connection.execute(
                        update(table).where(table.c.id == row["id"]).values(event_key=key)
                    )
                    backfilled += 1
            else:
                connection.execute(table.delete().where(table.c.id == row["id"]))
                removed += 1

        if not _has_unique_columns(connection, ALERT_RECORD_TABLE_NAME, ("event_key",)):
            index = Index(ALERT_RECORD_UNIQUE_INDEX_NAME, table.c.event_key, unique=True)
            connection.execute(CreateIndex(index))

    if not _has_unique_columns(engine, ALERT_RECORD_TABLE_NAME, ("event_key",)):
        raise RuntimeError("监控事件唯一键迁移失败")
    return UniqueKeyMigrationResult(
        ALERT_RECORD_TABLE_NAME,
        added_column or backfilled > 0 or removed > 0,
        removed,
        backfilled,
    )
