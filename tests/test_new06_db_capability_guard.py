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


def test_registry_exists_but_does_not_overclaim_db_security_metadata() -> None:
    assert REGISTRY.exists()
    source = REGISTRY.read_text(encoding="utf-8")
    assert "DB_CAPABILITIES" in source


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
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("me10_registry_guard", REGISTRY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        for market_spec in module.MARKET_REGISTRY.values():
            capabilities = market_spec.providers["db"].capabilities
            assert module.Capability.SECURITY_MASTER not in capabilities
            assert module.Capability.PLATES not in capabilities
    finally:
        sys.modules.pop(spec.name, None)

def test_capability_documentation_is_explicit_about_db_limitations() -> None:
    text = (ROOT / "docs/provider-capabilities.md").read_text(encoding="utf-8")
    assert "does **not** provide an authoritative security master" in text
    assert "Declaring `SECURITY_MASTER` or `PLATES`" in text
