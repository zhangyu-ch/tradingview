from __future__ import annotations

import ast
from pathlib import Path

import pytest

from test_support.web_routes import route_node, route_source

from tradingview_zy.market_metadata import tradingview_symbol_metadata


ROOT = Path(__file__).resolve().parents[1]
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        ("a", {"type": "stock", "session": "0930-1130,1300-1500:23456", "timezone": "Asia/Shanghai"}),
        ("hk", {"type": "stock", "session": "0930-1200,1300-1600:23456", "timezone": "Asia/Hong_Kong"}),
        ("us", {"type": "stock", "session": "0930-1600:23456", "timezone": "America/New_York"}),
        ("fx", {"type": "forex", "session": "24x5", "timezone": "America/New_York"}),
        ("currency", {"type": "crypto", "session": "24x7", "timezone": "Etc/UTC"}),
        ("currency_spot", {"type": "crypto", "session": "24x7", "timezone": "Etc/UTC"}),
        ("ny_futures", {"type": "futures", "session": "1800-1700:23456", "timezone": "America/New_York"}),
    ],
)
def test_cash_fx_crypto_and_globex_descriptors_are_market_aware(market, expected) -> None:
    assert tradingview_symbol_metadata(market) == expected


@pytest.mark.parametrize(
    ("code", "session"),
    [
        ("KQ.m@SHFE.rb", "2100-2300,0900-1015,1030-1130,1330-1500:23456"),
        ("SHFE.CU2608", "2100-0100,0900-1015,1030-1130,1330-1500:23456"),
        ("SHFE.AG2612", "2100-0230,0900-1015,1030-1130,1330-1500:23456"),
        ("CFFEX.IF2608", "0930-1130,1300-1500:23456"),
        ("CFFEX.T2609", "0930-1130,1300-1515:23456"),
        ("CZCE.AP610", "0900-1015,1030-1130,1330-1500:23456"),
    ],
)
def test_cn_futures_sessions_follow_versioned_instrument_profiles(code, session) -> None:
    assert tradingview_symbol_metadata("futures", code) == {
        "type": "futures",
        "session": session,
        "timezone": "Asia/Shanghai",
    }


def test_unknown_cn_futures_never_fall_back_to_24x7_or_a_guessed_night_session() -> None:
    metadata = tradingview_symbol_metadata("futures", "SHFE.NEW9999")
    assert metadata["session"] == "0900-1015,1030-1130,1330-1500:23456"
    assert metadata["session"] not in {"24x7", "24x5"}


def test_unsupported_market_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported TradingView market"):
        tradingview_symbol_metadata("unknown")


def _route(name: str) -> ast.FunctionDef:
    return route_node(name)


def test_symbol_and_search_routes_consume_authoritative_descriptors() -> None:
    source = (
        ROOT / "web/tradingview_zy_chart/cl_app/blueprints/udf.py"
    ).read_text(encoding="utf-8")
    assert "market_session =" not in source
    assert "market_timezone =" not in source
    assert "market_types =" not in source
    assert "get_localzone" not in source

    for name in ("tv_symbols", "tv_search"):
        route = _route(name)
        calls = [
            node for node in ast.walk(route)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "tradingview_symbol_metadata"
        ]
        assert calls, name

    search_source = route_source("tv_search")
    normalized_search_source = search_source.replace("'", '"')
    assert 'authoritative_type = tradingview_symbol_metadata(exchange)["type"]' in normalized_search_source
    assert '"type": type_value' not in normalized_search_source
    assert "type_value and type_value != authoritative_type" in search_source
