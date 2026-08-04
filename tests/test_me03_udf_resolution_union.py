from __future__ import annotations

import ast
from pathlib import Path

from test_support.web_routes import route_node, route_source

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
    route = route_node("tv_config")
    calls = [
        node
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "all_market_frequencies"
    ]
    assert len(calls) == 1
    assert ast.unparse(calls[0].args[0]) == "services.market_frequencies"
    source = route_source("tv_config")
    assert 'market_frequencies["ny_futures"]' not in source
    assert 'market_frequencies["a"]' not in source
