"""Crypto runtime UTC and immutable, explicitly confirmed legacy wall-time storage."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import pytz
from sqlalchemy import Column, MetaData, String, Table, inspect, select

from tradingview_zy.schema_migrations import _locked_connection, migration_connection

CRYPTO_TIME_VERSION = "crypto-utc-c1"
CRYPTO_MARKETS = frozenset(("currency", "currency_spot"))
_REGISTRY = Table(
    "cl_crypto_storage_timezone", MetaData(),
    Column("market", String(32), primary_key=True),
    Column("timezone", String(64), nullable=False),
    mysql_collate="utf8mb4_general_ci",
)


class CryptoTimezoneError(ValueError):
    """Operator confirmation or source reconstruction is required."""


def is_crypto(market) -> bool:
    return getattr(market, "value", market) in CRYPTO_MARKETS


def storage_frequency(market, frequency: str) -> str:
    # Old synthesized OHLCV cannot be repaired by relabeling its datetime.
    if is_crypto(market) and frequency in {"3h", "10m", "2m"}:
        return frequency + "C1"
    return frequency


def artifact_path(value):
    """Use a new namespace without deleting or overwriting pre-UTC artifacts."""
    if value is None:
        return None
    path = Path(value)
    marker = "_" + CRYPTO_TIME_VERSION
    if marker not in path.stem:
        path = path.with_name(path.stem + marker + path.suffix)
    return str(path)


def require_current_version(market, version):
    if is_crypto(market) and version != CRYPTO_TIME_VERSION:
        raise CryptoTimezoneError("旧数字货币结果仅供历史查看，时间语义未验证；请用新配置重跑，不能续跑、优化或转交易")


def as_utc(value) -> dt.datetime:
    """Naive API/config inputs explicitly mean UTC, never the host timezone."""
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise CryptoTimezoneError("数字货币时间不能为空")
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize("UTC")
    return stamp.tz_convert("UTC").to_pydatetime()


def _zone(name):
    if not isinstance(name, str) or name not in pytz.all_timezones_set:
        raise CryptoTimezoneError("存储时区必须是明确的 IANA 时区（例如 UTC / Asia/Shanghai），不能使用 local")
    return pytz.timezone(name)


def from_storage(value, timezone: str) -> dt.datetime:
    value = pd.Timestamp(value).to_pydatetime()
    if value.tzinfo is not None:
        raise CryptoTimezoneError("存储日期应为无时区钟面值")
    try:
        return _zone(timezone).localize(value, is_dst=None).astimezone(dt.timezone.utc)
    except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError) as exc:
        raise CryptoTimezoneError(
            f"{timezone} 存储时间 {value} 存在 DST 歧义或不存在；停止读写，核对原始时间戳或采用方案 B 重建"
        ) from exc


def to_storage(value, timezone: str) -> dt.datetime:
    wall = as_utc(value).astimezone(_zone(timezone)).replace(tzinfo=None)
    # Aware input alone cannot make a repeated naive storage key reversible.
    from_storage(wall, timezone)
    return wall


def migrate_crypto_storage_timezone(bind):
    """Append-only schema migration 5. Does not infer or bind any old data."""
    with migration_connection(bind) as connection:
        _REGISTRY.create(connection, checkfirst=True)


def storage_timezone(engine, market, configured=None) -> str:
    """Bind once per market/database, serialized with the existing cross-process lock.

    All application writers bind before creating a K-line table or inserting rows.
    Old programs/importers must be stopped during rollout; external SQL is not managed.
    """
    market = getattr(market, "value", market)
    if market not in CRYPTO_MARKETS:
        raise ValueError("not a crypto market")
    if configured is not None:
        _zone(configured)

    def checked(bound):
        _zone(bound)
        if configured is not None and configured != bound:
            raise CryptoTimezoneError(
                f"{market} 存储时区已锁定为 {bound}，不能改成 {configured}；恢复配置，不要修改台账"
            )
        return bound

    query = select(_REGISTRY.c.timezone).where(_REGISTRY.c.market == market)
    # Immutable bindings need no writer lock; keep chart reads available during writes.
    with engine.connect() as connection:
        bound = connection.execute(query).scalar_one_or_none()
    if bound is not None:
        return checked(bound)
    with _locked_connection(engine, 60) as connection:
        connection.rollback()
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.begin()
        try:
            bound = connection.execute(query).scalar_one_or_none()
            if bound is not None:
                bound = checked(bound)
                connection.commit()
                return bound
            if configured is None:
                for name in inspect(connection).get_table_names():
                    if not name.startswith(f"{market}_klines_"):
                        continue
                    table = Table(name, MetaData(), autoload_with=connection)
                    if connection.execute(select(table).limit(1)).first() is not None:
                        raise CryptoTimezoneError(
                            f"{market} 存在未登记旧行情，不能推断其时区。请停写并备份，核实所有旧数据的写入时区，"
                            f"然后设置 CRYPTO_STORAGE_TIMEZONES['{market}'] 为已确认的 IANA 时区；"
                            "仅确认上海来源时才填 Asia/Shanghai。混合或未知来源请采用方案 B 重建。"
                        )
            bound = configured or "UTC"
            connection.execute(_REGISTRY.insert().values(market=market, timezone=bound))
            connection.commit()
            return bound
        except Exception:
            connection.rollback()
            raise
