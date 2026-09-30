"""Versioned startup migrations, serialized across processes and connections."""

from __future__ import annotations

import errno
import hashlib
import os
import threading
import time
import weakref
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, Table, inspect, select, text


class SchemaMigrationError(RuntimeError):
    """The database requires an operator action before it can be used safely."""


_SCHEMA = Table(
    "cl_schema_version",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("version", Integer, nullable=False),
    mysql_collate="utf8mb4_general_ci",
)
_MEMORY_LOCKS = weakref.WeakKeyDictionary()
_MEMORY_LOCKS_GUARD = threading.Lock()


def _schema_version(connection) -> int:
    if not inspect(connection).has_table(_SCHEMA.name):
        return 0
    value = connection.execute(
        select(_SCHEMA.c.version).where(_SCHEMA.c.id == 1)
    ).scalar_one_or_none()
    return int(value or 0)


@contextmanager
def migration_connection(bind):
    """Allow a migration to run standalone or inside the startup transaction."""
    if hasattr(bind, "connect"):
        with bind.begin() as connection:
            yield connection
    else:
        yield bind


@contextmanager
def _sqlite_file_lock(path: Path, timeout: float):
    # Do not unlink the lock file: another process may already hold its inode.
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                if time.monotonic() >= deadline:
                    raise SchemaMigrationError("等待 SQLite 结构迁移锁超时，请稍后重试") from error
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _sqlite_lock(engine, timeout: float):
    database = engine.url.database
    if not database or database == ":memory:" or engine.url.query.get("mode") == "memory":
        with _MEMORY_LOCKS_GUARD:
            lock = _MEMORY_LOCKS.setdefault(engine, threading.RLock())
        if not lock.acquire(timeout=timeout):
            raise SchemaMigrationError("等待内存数据库结构迁移锁超时")
        try:
            yield
        finally:
            lock.release()
    else:
        path = Path(database).resolve()
        with _sqlite_file_lock(path.with_name(path.name + ".schema.lock"), timeout):
            yield


@contextmanager
def _locked_connection(engine, timeout: float):
    if engine.dialect.name == "sqlite":
        with _sqlite_lock(engine, timeout):
            with engine.connect() as connection:
                yield connection
        return
    if engine.dialect.name != "mysql":
        raise SchemaMigrationError("不支持此数据库的结构迁移锁")

    # GET_LOCK is connection-scoped and survives MySQL DDL implicit commits.
    # Hash the database name only: different application DB users must share it.
    name = "tradingview_schema_" + hashlib.sha256(
        str(engine.url.database).encode("utf-8")
    ).hexdigest()[:40]
    with engine.connect() as connection:
        acquired = connection.execute(
            text("SELECT GET_LOCK(:name, :timeout)"),
            {"name": name, "timeout": int(timeout)},
        ).scalar_one()
        if acquired != 1:
            connection.rollback()
            raise SchemaMigrationError("等待 MySQL 结构迁移锁超时或数据库拒绝加锁")
        try:
            yield connection
        finally:
            connection.rollback()
            connection.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})
            connection.commit()


def initialize_schema(engine, metadata, migrations, *, lock_timeout: float = 60) -> None:
    """Create tables once and apply only newer idempotent migrations.

    SQLite DDL and the version marker share an explicit transaction. MySQL DDL
    may commit implicitly, so failed migrations must remain safe to retry.
    """
    target_version = len(migrations)
    with engine.connect() as connection:
        version = _schema_version(connection)
    if version > target_version:
        raise SchemaMigrationError("数据库结构版本高于当前程序，请使用对应版本的程序")
    if version == target_version:
        return

    with _locked_connection(engine, lock_timeout) as connection:
        version = _schema_version(connection)
        if version > target_version:
            raise SchemaMigrationError("数据库结构版本高于当前程序，请使用对应版本的程序")
        if version == target_version:
            return
        connection.rollback()
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.begin()
        try:
            _SCHEMA.create(connection, checkfirst=True)
            metadata.create_all(connection)
            for migrate in migrations[version:]:
                migrate(connection)
            connection.execute(_SCHEMA.delete().where(_SCHEMA.c.id == 1))
            connection.execute(_SCHEMA.insert().values(id=1, version=target_version))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
