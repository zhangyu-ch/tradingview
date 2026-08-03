from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_SOURCE = ROOT / "src/tradingview_zy/db.py"


def test_db_module_has_no_executable_demo_main_block() -> None:
    source = DB_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and "__main__" in (ast.get_source_segment(source, node.test) or "")
        for node in tree.body
    )


def test_db_module_contains_no_test_marker_write() -> None:
    source = DB_SOURCE.read_text(encoding="utf-8")
    assert '"测试标记2"' not in source
    assert 'db.marks_add_by_price(' not in source


def test_production_database_singleton_remains_available() -> None:
    source = DB_SOURCE.read_text(encoding="utf-8")
    assert "db: DB = DB()" in source
