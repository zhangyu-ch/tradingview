from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PROVIDER = ROOT / "src/tradingview_zy/exchange/exchange_db.py"
REGISTRY = ROOT / "src/tradingview_zy/market_registry.py"


def _method_node(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _is_unimplemented(node: ast.FunctionDef) -> bool:
    body = node.body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    if len(body) == 1 and isinstance(body[0], ast.Return):
        value = body[0].value
        return isinstance(value, (ast.List, ast.Tuple, ast.Set)) and not value.elts
    return False


def test_local_tree_does_not_contain_the_reported_overclaiming_registry() -> None:
    # The uploaded local ZIP predates the remote MarketRegistry change. The exact
    # NEW-06 regression is therefore absent and must not be fabricated locally.
    assert not REGISTRY.exists()


def test_db_exposes_only_a_persisted_code_catalog_not_security_metadata() -> None:
    source = DB_PROVIDER.read_text(encoding="utf-8")
    all_stocks = _method_node(source, "all_stocks")
    all_stocks_source = ast.get_source_segment(source, all_stocks) or ""

    # NX-23 may expose codes already present in K-line storage, but that is not
    # an authoritative security master: names remain the code itself and the
    # plate metadata methods must stay explicitly unsupported.
    assert "db.klines_codes(self.market)" in all_stocks_source
    assert '{"code": code, "name": code}' in all_stocks_source
    assert _is_unimplemented(_method_node(source, "stock_owner_plate"))
    assert _is_unimplemented(_method_node(source, "plate_stocks"))


def test_future_registry_cannot_overreport_db_capabilities() -> None:
    if not REGISTRY.exists():
        return
    source = REGISTRY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target_text = ast.get_source_segment(source, node) or ""
            if "DB_CAPABILITIES" in target_text:
                assignments.append(target_text)
    joined = "\n".join(assignments)
    assert "SECURITY_MASTER" not in joined
    assert "PLATES" not in joined


def test_capability_documentation_is_explicit_about_db_limitations() -> None:
    text = (ROOT / "docs/provider-capabilities.md").read_text(encoding="utf-8")
    assert "does **not** provide an authoritative security master" in text
    assert "Declaring `SECURITY_MASTER` or `PLATES`" in text
