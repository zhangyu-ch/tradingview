from __future__ import annotations

import ast
from pathlib import Path

from tradingview_zy.market_metadata import all_market_frequencies, market_frequencies

ROOT = Path(__file__).resolve().parents[1]
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"


def test_frequency_union_includes_every_market_and_future_unique_values() -> None:
    markets = market_frequencies()
    markets["ny_futures"] = [*markets["ny_futures"], "10s"]
    union = all_market_frequencies(markets)
    assert "10s" in union
    for frequencies in markets.values():
        assert set(frequencies) <= set(union)
    assert len(union) == len(set(union))


def test_real_tv_config_uses_dynamic_market_union() -> None:
    tree = ast.parse(WEB_APP.read_text(encoding="utf-8"))
    create_app = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )
    route = next(
        node
        for node in create_app.body
        if isinstance(node, ast.FunctionDef) and node.name == "tv_config"
    )
    calls = [
        node
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "all_market_frequencies"
    ]
    assert len(calls) == 1
    assert isinstance(calls[0].args[0], ast.Name)
    assert calls[0].args[0].id == "market_frequencys"
    source = ast.get_source_segment(WEB_APP.read_text(encoding="utf-8"), route) or ""
    assert 'market_frequencys["ny_futures"]' not in source
    assert 'market_frequencys["a"]' not in source
