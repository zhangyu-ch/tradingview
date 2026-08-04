from __future__ import annotations

import importlib
import sys
import threading
import types
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from tradingview_zy.tv_storage import (
    TVStorageFieldError,
    TVStoragePolicy,
    TVStorageQuotaError,
    enforce_quota,
    normalize_chart_payload,
    normalize_drawing_payload,
    normalize_identifier,
)

ROOT = Path(__file__).resolve().parents[1]
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"


def _load_db(tmp_path, **limits):
    for name in ["tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config"]:
        sys.modules.pop(name, None)
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: timezone.utc
    sys.modules["tzlocal"] = tzlocal

    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "rv06"
    config.DB_HOST = "127.0.0.1"
    config.DB_PORT = 3306
    config.DB_USER = "user"
    config.DB_PWD = "password"
    config.get_data_path = lambda: tmp_path
    for name, value in limits.items():
        setattr(config, name, value)
    sys.modules["tradingview_zy.config"] = config
    package = importlib.import_module("tradingview_zy")
    package.config = config
    return importlib.import_module("tradingview_zy.db")


def _chart(module, name: str, content: str = "{}") -> int:
    return module.db.tv_chart_save("chart", "client", "user", name, content, "A", "D")


def test_default_policy_matches_documented_limits() -> None:
    assert TVStoragePolicy() == TVStoragePolicy(
        chart_max_bytes=512 * 1024,
        template_max_bytes=256 * 1024,
        drawing_max_bytes=512 * 1024,
        max_charts=100,
        max_templates=200,
        max_drawings=2000,
        max_total_bytes=16 * 1024 * 1024,
    )


def test_identifiers_are_bounded_by_utf8_bytes_and_reject_controls() -> None:
    assert normalize_identifier(" client ", field="client", max_bytes=10) == "client"
    with pytest.raises(TVStorageFieldError):
        normalize_identifier("中中", field="client", max_bytes=5)
    with pytest.raises(TVStorageFieldError):
        normalize_identifier("bad\nname", field="name", max_bytes=50)
    with pytest.raises(TVStorageFieldError):
        normalize_identifier("\ud800", field="name", max_bytes=50)


@pytest.mark.parametrize(
    ("kind", "limit", "normalizer"),
    [
        (
            "chart",
            8,
            lambda policy, value: normalize_chart_payload(
                policy,
                chart_type="chart",
                client_id="c",
                user_id="u",
                name="n",
                content=value,
                symbol="A",
                resolution="D",
            ),
        ),
        (
            "template",
            8,
            lambda policy, value: normalize_chart_payload(
                policy,
                chart_type="template",
                client_id="c",
                user_id="u",
                name="n",
                content=value,
                symbol="",
                resolution="",
            ),
        ),
        (
            "drawing",
            8,
            lambda policy, value: normalize_drawing_payload(
                policy,
                client_id="c",
                user_id="u",
                layout_id="l",
                chart_id="ch",
                symbol="",
                state=value,
            ),
        ),
    ],
)
def test_each_blob_type_has_its_own_hard_utf8_boundary(kind, limit, normalizer) -> None:
    kwargs = {
        "chart_max_bytes": 100,
        "template_max_bytes": 100,
        "drawing_max_bytes": 100,
    }
    kwargs[f"{kind}_max_bytes"] = limit
    policy = TVStoragePolicy(**kwargs)
    normalizer(policy, "x" * limit)
    with pytest.raises(TVStorageFieldError):
        normalizer(policy, "x" * (limit + 1))


def test_chart_and_template_save_are_name_upserts_not_unbounded_duplicates(tmp_path) -> None:
    module = _load_db(tmp_path)
    first = _chart(module, "same", "one")
    second = _chart(module, "same", "two")
    assert first == second
    rows = module.db.tv_chart_list("chart", "client", "user")
    assert len(rows) == 1
    assert rows[0].content == "two"

    t1 = module.db.tv_chart_save("template", "client", "user", "t", "one", "", "")
    t2 = module.db.tv_chart_save("template", "client", "user", "t", "two", "", "")
    assert t1 == t2
    assert len(module.db.tv_chart_list("template", "client", "user")) == 1
    module.db.engine.dispose()


def test_record_quotas_reject_growth_but_allow_updating_existing_record(tmp_path) -> None:
    module = _load_db(tmp_path, TV_STORAGE_MAX_CHARTS=1)
    saved_id = _chart(module, "one", "a")
    assert _chart(module, "one", "b") == saved_id
    with pytest.raises(TVStorageQuotaError):
        _chart(module, "two", "c")
    assert [row.name for row in module.db.tv_chart_list("chart", "client", "user")] == ["one"]
    module.db.engine.dispose()


def test_drawing_quota_and_upsert_key(tmp_path) -> None:
    module = _load_db(tmp_path, TV_STORAGE_MAX_DRAWINGS=1)
    assert module.db.tv_drawing_save_or_update("c", "u", "l", "1", "A", "one")
    assert module.db.tv_drawing_save_or_update("c", "u", "l", "1", "A", "two")
    assert module.db.tv_drawing_get("c", "u", "l", "1", "A") == "two"
    with pytest.raises(TVStorageQuotaError):
        module.db.tv_drawing_save_or_update("c", "u", "l", "2", "A", "three")
    module.db.engine.dispose()


def test_combined_byte_quota_spans_charts_templates_and_drawings(tmp_path) -> None:
    module = _load_db(
        tmp_path,
        TV_STORAGE_MAX_TOTAL_BYTES=10,
        TV_STORAGE_CHART_MAX_BYTES=10,
        TV_STORAGE_TEMPLATE_MAX_BYTES=10,
        TV_STORAGE_DRAWING_MAX_BYTES=10,
    )
    module.db.tv_chart_save("chart", "c", "u", "c", "1234", "A", "D")
    module.db.tv_chart_save("template", "c", "u", "t", "1234", "", "")
    with pytest.raises(TVStorageQuotaError):
        module.db.tv_drawing_save_or_update("c", "u", "l", "ch", "", "123")
    module.db.engine.dispose()


def test_historical_over_quota_namespace_may_shrink_but_not_grow() -> None:
    policy = TVStoragePolicy(max_total_bytes=10, max_charts=1)
    enforce_quota(
        policy,
        kind="chart",
        current_count=2,
        projected_count=2,
        current_total_bytes=20,
        projected_total_bytes=15,
    )
    with pytest.raises(TVStorageQuotaError):
        enforce_quota(
            policy,
            kind="chart",
            current_count=2,
            projected_count=3,
            current_total_bytes=20,
            projected_total_bytes=21,
        )


def test_legacy_migration_deduplicates_latest_and_creates_indexes(tmp_path) -> None:
    module = _load_db(tmp_path / "bootstrap")
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE cl_tv_charts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id VARCHAR(50), user_id INTEGER, chart_type VARCHAR(20),
                    symbol VARCHAR(50), resolution VARCHAR(20), content TEXT,
                    timestamp INTEGER, name VARCHAR(50)
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO cl_tv_charts "
                "(client_id,user_id,chart_type,content,timestamp,name) VALUES "
                "('c',1,'chart','old',1,'same'),('c',1,'chart','new',2,'same')"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE cl_tv_drawings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id VARCHAR(100), user_id VARCHAR(50), layout_id VARCHAR(100),
                    chart_id VARCHAR(100), symbol VARCHAR(100), state TEXT, timestamp INTEGER
                )
                """
            )
        )
    module.migrate_tv_storage_schema(engine)
    module.migrate_tv_storage_schema(engine)
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT content FROM cl_tv_charts")).scalars().all()
    assert rows == ["new"]
    chart_indexes = {item["name"] for item in inspect(engine).get_indexes("cl_tv_charts")}
    drawing_indexes = {item["name"] for item in inspect(engine).get_indexes("cl_tv_drawings")}
    assert "table_tv_charts_owner_name_unique" in chart_indexes
    assert "table_tv_charts_owner_idx" in chart_indexes
    assert "table_tv_drawings_owner_idx" in drawing_indexes
    engine.dispose()
    module.db.engine.dispose()


def test_mysql_schema_uses_mediumtext_and_unique_owner_name(tmp_path) -> None:
    module = _load_db(tmp_path)
    chart_ddl = str(CreateTable(module.TableByTVCharts.__table__).compile(dialect=mysql.dialect()))
    drawing_ddl = str(CreateTable(module.TableByTVDrawings.__table__).compile(dialect=mysql.dialect()))
    assert "MEDIUMTEXT" in chart_ddl
    assert "MEDIUMTEXT" in drawing_ddl
    assert "table_tv_charts_owner_name_unique" in chart_ddl
    module.db.engine.dispose()


def test_sqlite_quota_check_is_serialized_before_usage_read(tmp_path) -> None:
    module = _load_db(tmp_path, TV_STORAGE_MAX_CHARTS=1)
    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker(name: str) -> None:
        barrier.wait()
        try:
            _chart(module, name, name)
        except TVStorageQuotaError:
            result = "quota"
        else:
            result = "ok"
        with lock:
            results.append(result)

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == ["ok", "quota"]
    assert len(module.db.tv_chart_list("chart", "client", "user")) == 1
    module.db.engine.dispose()


def test_web_contract_has_stable_413_field_and_quota_errors() -> None:
    source = WEB_APP.read_text(encoding="utf-8")
    assert '"error": "request_too_large"' in source
    assert "except TVStorageError as error" in source
    assert '"error": error.code' in source
    assert "normalize_chart_payload(" in source
    assert "normalize_drawing_payload(" in source
