from __future__ import annotations

import ast
from pathlib import Path

from sqlalchemy.engine import URL, make_url

ROOT = Path(__file__).resolve().parents[1]
DB_SOURCE = ROOT / "src/tradingview_zy/db.py"


def _build_mysql_url():
    tree = ast.parse(DB_SOURCE.read_text(encoding="utf-8"), filename=str(DB_SOURCE))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "build_mysql_url"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {"URL": URL}
    exec(compile(module, str(DB_SOURCE), "exec"), namespace)
    return namespace["build_mysql_url"]


def test_special_characters_round_trip_through_structured_url() -> None:
    build = _build_mysql_url()
    username = "user@desk"
    password = "p@ss:/%#?& word"
    database = "trade/db"

    url = build(
        username=username,
        password=password,
        host="db.internal",
        port="3307",
        database=database,
    )
    rendered = url.render_as_string(hide_password=False)
    parsed = make_url(rendered)

    assert parsed.username == username
    assert parsed.password == password
    assert parsed.database == database
    assert parsed.port == 3307
    assert parsed.query["charset"] == "utf8mb4"
    assert "%40" in rendered and "%2F" in rendered and "%25" in rendered


def test_default_string_rendering_redacts_password() -> None:
    build = _build_mysql_url()
    secret = "never-print-this"
    url = build(
        username="root",
        password=secret,
        host="127.0.0.1",
        port=3306,
        database="trading",
    )

    assert secret not in str(url)
    assert "***" in str(url)


def test_db_constructor_uses_structured_builder_not_dsn_interpolation() -> None:
    source = DB_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DB_SOURCE))
    db_class = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "DB"
    )
    init = next(
        node
        for node in db_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )

    assert "build_mysql_url(" in ast.unparse(init)
    assert not any(
        isinstance(node, ast.JoinedStr)
        and "mysql+pymysql://" in (ast.get_source_segment(source, node) or "")
        for node in ast.walk(init)
    )
