from __future__ import annotations

import pytest

from tradingview_zy.web_api_validation import (
    WebParameterError,
    parse_bounded_text,
    parse_int,
    parse_market,
    parse_resolution,
    parse_strict_bool,
    parse_symbol,
    parse_time_range,
)


@pytest.mark.parametrize("value", [None, "yes", "1", 1, "truthy", ""])
def test_parse_strict_bool_rejects_truthy_guessing(value):
    with pytest.raises(WebParameterError):
        parse_strict_bool(value, field="firstDataRequest")


def test_parse_strict_bool_accepts_only_true_false():
    assert parse_strict_bool(" TRUE ", field="flag") is True
    assert parse_strict_bool("false", field="flag") is False


@pytest.mark.parametrize("value", [None, "", "01", "1.2", True, "1 "])
def test_parse_int_rejects_noncanonical_values(value):
    with pytest.raises(WebParameterError):
        parse_int(value, field="limit", minimum=1, maximum=100)


def test_parse_int_and_time_range_apply_bounds_and_order():
    assert parse_int("100", field="limit", minimum=1, maximum=100) == 100
    assert parse_time_range("-2", "5") == (-2, 5)
    with pytest.raises(WebParameterError):
        parse_time_range("6", "5")


@pytest.mark.parametrize(
    "symbol",
    [None, "", "a", "a:", ":x", "a:x:y", "unknown:x", "a:bad\ncode"],
)
def test_parse_symbol_rejects_missing_ambiguous_or_unknown_values(symbol):
    with pytest.raises(WebParameterError):
        parse_symbol(symbol, allowed_markets={"a", "hk"})


def test_parse_symbol_normalizes_market_and_code():
    assert parse_symbol(" A : SH.000001 ", allowed_markets={"a"}) == ("a", "SH.000001")


def test_parse_market_and_resolution_are_registry_bounded():
    assert parse_market(" HK ", allowed_markets={"a", "hk"}) == "hk"
    assert parse_resolution("1D", resolution_map={"1D": "d"}) == ("1D", "d")
    with pytest.raises(WebParameterError):
        parse_market("fx", allowed_markets={"a", "hk"})
    with pytest.raises(WebParameterError):
        parse_resolution("13", resolution_map={"1D": "d"})


def test_search_text_allows_empty_query_but_bounds_controls_and_length():
    assert parse_bounded_text("", field="query", allow_empty=True) == ""
    with pytest.raises(WebParameterError):
        parse_bounded_text("x\ny", field="query", allow_empty=True)
    with pytest.raises(WebParameterError):
        parse_bounded_text("x" * 101, field="query", max_chars=100, allow_empty=True)


@pytest.mark.parametrize(
    ("route_name", "required_token"),
    [
        ("tv_symbol_info", "parse_market"),
        ("tv_symbols", "parse_symbol"),
        ("tv_search", "parse_market"),
        ("tv_history", "parse_time_range"),
        ("tv_footprint", "parse_symbol"),
        ("tv_timescale_marks", "parse_time_range"),
        ("tv_marks", "parse_time_range"),
        ("tv_del_marks", "parse_symbol"),
    ],
)
def test_public_routes_use_shared_validation_before_side_effects(route_name, required_token):
    source = open("web/tradingview_zy_chart/cl_app/__init__.py", encoding="utf-8").read()
    start = source.index(f"    def {route_name}(")
    candidates = [position for marker in ("\n    @app.route", "\n    # ") if (position := source.find(marker, start + 10)) != -1]
    block = source[start:min(candidates)]
    assert required_token in block
    side_effect_positions = [
        position
        for token in ("get_exchange(", "db.")
        if (position := block.find(token)) != -1
    ]
    assert side_effect_positions
    validation_positions = [block.find(token) for token in ("parse_market", "parse_symbol", "parse_time_range") if block.find(token) != -1]
    assert min(validation_positions) < min(side_effect_positions)


def test_routes_expose_stable_udf_and_regular_api_errors():
    source = open("web/tradingview_zy_chart/cl_app/__init__.py", encoding="utf-8").read()
    assert 'return {"s": "error", "errmsg": str(exc)}' in source
    assert '"invalid_search_request"' in source
    assert '"invalid_marks_request"' in source
