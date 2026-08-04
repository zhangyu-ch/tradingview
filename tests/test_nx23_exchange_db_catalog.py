from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, create_engine, insert

from tradingview_zy.database_catalog import list_market_kline_codes

ROOT = Path(__file__).resolve().parents[1]
EXCHANGE_DB_SOURCE = ROOT / "src/tradingview_zy/exchange/exchange_db.py"


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


def test_exchange_db_maps_persisted_codes_to_legacy_stock_contract() -> None:
    tree = ast.parse(
        EXCHANGE_DB_SOURCE.read_text(encoding="utf-8"),
        filename=str(EXCHANGE_DB_SOURCE),
    )
    exchange_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ExchangeDB"
    )
    method = next(
        node
        for node in exchange_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "all_stocks"
    )
    module = ast.Module(body=[method], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, str(EXCHANGE_DB_SOURCE), "exec"), namespace)

    class FakeDB:
        def klines_codes(self, market: str) -> list[str]:
            assert market == "a"
            return ["SH.600000", "SZ.000001"]

    fn = namespace["all_stocks"]
    fn.__globals__["db"] = FakeDB()
    result = fn(type("Provider", (), {"market": "a"})())

    assert result == [
        {"code": "SH.600000", "name": "SH.600000"},
        {"code": "SZ.000001", "name": "SZ.000001"},
    ]


def test_real_db_provider_returns_codes_after_kline_insert(tmp_path: Path) -> None:
    code = r'''
import datetime
import sys
import types

import pandas as pd

tzlocal = types.ModuleType("tzlocal")
tzlocal.get_localzone = lambda: "UTC"
sys.modules["tzlocal"] = tzlocal

from tradingview_zy.db import db
from tradingview_zy.exchange.exchange_db import ExchangeDB

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
for symbol in ("SH.600000", "SH.600001"):
    db.klines_insert("a", symbol, "d", bars)

provider = ExchangeDB("a")
assert provider.all_stocks() == [
    {"code": "SH.600000", "name": "SH.600000"},
    {"code": "SH.600001", "name": "SH.600001"},
]
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
