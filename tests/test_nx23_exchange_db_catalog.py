from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, create_engine, insert

from tradingview_zy.database_catalog import list_market_kline_codes

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_discovers_distinct_codes_from_existing_partition_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    metadata = MetaData()
    first = Table(
        "a_klines_sh_6000",
        metadata,
        Column("code", String(20), nullable=False),
        Column("f", String(5), nullable=False),
    )
    second = Table(
        "a_klines_sz_0000",
        metadata,
        Column("code", String(20), nullable=False),
        Column("f", String(5), nullable=False),
    )
    other_market = Table(
        "hk_klines_700",
        metadata,
        Column("code", String(20), nullable=False),
    )
    Table("a_klines_metadata", metadata, Column("value", String(20)))
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(first),
            [
                {"code": "SH.600000", "f": "d"},
                {"code": "SH.600000", "f": "30m"},
            ],
        )
        connection.execute(insert(second), [{"code": "SZ.000001", "f": "d"}])
        connection.execute(insert(other_market), [{"code": "HK.00700"}])

    assert list_market_kline_codes(engine, "a") == ["SH.600000", "SZ.000001"]
    assert list_market_kline_codes(engine, "hk") == ["HK.00700"]
    assert list_market_kline_codes(engine, "us") == []
    engine.dispose()


def test_catalog_rejects_empty_market_to_avoid_broad_table_scan() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        list_market_kline_codes(engine, "  ")
    except ValueError as exc:
        assert "market" in str(exc)
    else:
        raise AssertionError("empty market must not scan every K-line table")
    finally:
        engine.dispose()


def test_real_db_provider_returns_only_persisted_market_codes(tmp_path: Path) -> None:
    code = r'''
import datetime
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

config = types.ModuleType("tradingview_zy.config")
config.DB_TYPE = "sqlite"
config.DB_DATABASE = "catalog"
config.get_data_path = lambda: Path(sys.argv[1])
sys.modules["tradingview_zy.config"] = config

from tradingview_zy.db import db
from tradingview_zy.domain import UnsupportedCapabilityError
from tradingview_zy.exchange.exchange_db import ExchangeDB

assert Path(db.engine.url.database) == Path(sys.argv[1]) / "db/catalog.sqlite"
provider = ExchangeDB("a")
assert provider.all_stocks() == []
bars = pd.DataFrame([
    {
        "date": datetime.datetime(2026, 8, 3, 15, 0),
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.5,
        "volume": 1000.0,
    }
])
try:
    for symbol in ("SZ.000001", "SH.600000"):
        db.klines_insert("a", symbol, "d", bars)
    db.klines_insert("a", "SH.600000", "30m", bars)
    db.klines_insert("hk", "HK.00700", "d", bars)
    assert provider.all_stocks() == [
        {"code": "SH.600000", "name": "SH.600000"},
        {"code": "SZ.000001", "name": "SZ.000001"},
    ]
    assert ExchangeDB("hk").all_stocks() == [
        {"code": "HK.00700", "name": "HK.00700"},
    ]
    assert ExchangeDB("us").all_stocks() == []
    for operation in (provider.stock_owner_plate, provider.plate_stocks):
        with pytest.raises(UnsupportedCapabilityError):
            operation("SH.600000")
finally:
    db.engine.dispose()
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
