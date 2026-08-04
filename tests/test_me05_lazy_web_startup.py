from __future__ import annotations

import ast

from pathlib import Path

from tradingview_zy.market_metadata import market_default_codes, market_frequencies

ROOT = Path(__file__).resolve().parents[1]


def test_static_market_metadata_needs_no_provider_construction() -> None:
    frequencies = market_frequencies()
    defaults = market_default_codes()
    assert set(frequencies) == set(defaults) == {
        "a", "hk", "fx", "us", "futures", "ny_futures", "currency", "currency_spot"
    }
    assert defaults["a"] == "SH.000001"
    assert "d" in frequencies["us"]


def test_create_app_startup_metadata_does_not_call_get_exchange() -> None:
    path = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    create_app = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    calls = [node for node in ast.walk(create_app) if isinstance(node, ast.Call)]
    called_names = {
        node.func.id for node in calls if isinstance(node.func, ast.Name)
    }
    assert {"market_frequencies", "market_default_codes", "market_catalog"} <= called_names
    assert not any(
        (isinstance(node.func, ast.Name) and node.func.id == "get_exchange")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "get_exchange")
        for node in calls
    )
    assert "WebAppServices.create(" in source
    assert "register_blueprints(app)" in source


def test_metadata_module_has_no_sdk_or_exchange_imports() -> None:
    source = (ROOT / "src/tradingview_zy/market_metadata.py").read_text(encoding="utf-8")
    assert "get_exchange" not in source
    assert "tradingview_zy.exchange" not in source
    assert "tqsdk" not in source
    assert "ccxt" not in source
