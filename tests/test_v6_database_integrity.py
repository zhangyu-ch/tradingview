from __future__ import annotations

import datetime as dt
from types import MethodType

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from tradingview_zy import config
from tradingview_zy.db import (
    Base,
    DB,
    TableByAlertRecord,
    TableByKlineSyncBatch,
    TableByTVMarks,
    TableByTVMarksPrice,
)


def make_db(tmp_path, monkeypatch) -> DB:
    monkeypatch.setattr(config, "DB_TYPE", "sqlite")
    db_class = DB.__wrapped__
    instance = db_class.__new__(db_class)
    instance.engine = create_engine(f"sqlite:///{tmp_path / 'v6.sqlite'}", poolclass=NullPool)
    instance.Session = sessionmaker(bind=instance.engine)
    instance._DB__cache_tables = {}
    Base.metadata.create_all(instance.engine)
    return instance


@pytest.fixture
def database(tmp_path, monkeypatch):
    instance = make_db(tmp_path, monkeypatch)
    try:
        yield instance
    finally:
        instance.engine.dispose()


def kline_frame(rows: int, code: str = "SH.600000") -> pd.DataFrame:
    dates = pd.date_range("2026-01-02 09:30", periods=rows, freq="min", tz="Asia/Shanghai")
    return pd.DataFrame(
        {
            "date": dates,
            "code": [code] * rows,
            "frequency": ["1m"] * rows,
            "open": [10.0] * rows,
            "high": [10.5] * rows,
            "low": [9.5] * rows,
            "close": [10.1] * rows,
            "volume": list(range(1, rows + 1)),
        }
    )


def test_hi04_price_marks_are_idempotent_and_never_delete_timeline_marks(database):
    with database.Session.begin() as session:
        session.add(
            TableByTVMarks(
                market="a",
                stock_code="SH.600000",
                stock_name="浦发",
                frequency="1m",
                mark_time=123,
                mark_label="A",
                mark_tooltip="timeline",
                mark_shape="circle",
                mark_color="red",
                dt=dt.datetime.now(),
            )
        )

    args = ("a", "SH.600000", "浦发", "1m", 123, "A", "price", "white", "red")
    assert database.marks_add_by_price(*args) is True
    assert database.marks_add_by_price(*args) is True

    with database.Session() as session:
        assert session.scalar(select(func.count()).select_from(TableByTVMarks)) == 1
        assert session.scalar(select(func.count()).select_from(TableByTVMarksPrice)) == 1
    assert database.marks_del_by_price("a", "A") is True
    with database.Session() as session:
        assert session.scalar(select(func.count()).select_from(TableByTVMarks)) == 1
        assert session.scalar(select(func.count()).select_from(TableByTVMarksPrice)) == 0


def test_nx12_alert_events_use_stable_key_and_duplicate_poll_is_noop(database):
    payload = dict(
        market="a",
        task_name="突破",
        stock_code="SH.600000",
        stock_name="浦发",
        frequency="5m",
        alert_msg="hit",
        action="buy",
        score="0.9",
        event_type="sig",
        event_time=dt.datetime(2026, 1, 2, 10, 0),
    )
    assert database.alert_event_save(**payload) is True
    assert database.alert_event_save(**payload) is False
    # A recalculated score is presentation metadata, not a new event identity.
    changed_score = {**payload, "score": "0.95"}
    assert database.alert_event_save(**changed_score) is False
    with database.Session() as session:
        records = session.scalars(select(TableByAlertRecord)).all()
    assert len(records) == 1
    assert len(records[0].event_key) == 64


def test_me08_kline_chunks_and_audit_roll_back_as_one_batch(database):
    original = database._execute_kline_chunk
    calls = 0

    def fail_second(self, session, table, rows, in_position):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected second chunk failure")
        return original(session, table, rows, in_position)

    database._execute_kline_chunk = MethodType(fail_second, database)
    with pytest.raises(RuntimeError, match="second chunk"):
        database.klines_insert("a", "SH.600000", "1m", kline_frame(501))

    table = database.klines_tables("a", "SH.600000")
    with database.Session() as session:
        assert session.scalar(select(func.count()).select_from(table)) == 0
        assert session.scalar(select(func.count()).select_from(TableByKlineSyncBatch)) == 0


def test_me08_successful_kline_batch_is_upserted_and_audited(database):
    frame = kline_frame(3, "SH.600001")
    assert database.klines_insert("a", "SH.600001", "1m", frame) is True
    changed = frame.copy()
    changed.loc[1, "close"] = 10.3
    assert database.klines_insert("a", "SH.600001", "1m", changed) is True

    table = database.klines_tables("a", "SH.600001")
    with database.Session() as session:
        assert session.scalar(select(func.count()).select_from(table)) == 3
        audits = session.scalars(select(TableByKlineSyncBatch)).all()
    assert len(audits) == 2
    assert all(audit.row_count == 3 and len(audit.content_hash) == 64 for audit in audits)
