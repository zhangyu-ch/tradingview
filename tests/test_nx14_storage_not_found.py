from __future__ import annotations

from pathlib import Path

import pytest

from test_support.web_routes import route_source

from tradingview_zy.web_api_validation import (
    WebParameterError,
    parse_bounded_text,
    parse_positive_int,
)


@pytest.mark.parametrize("value", [None, True, False, 0, -1, "", "0", "-1", "1.0", "01", " 1"])
def test_parse_positive_int_rejects_noncanonical_values(value):
    with pytest.raises(WebParameterError):
        parse_positive_int(value, field="chart")


def test_parse_positive_int_accepts_int_and_canonical_string():
    assert parse_positive_int(7, field="chart") == 7
    assert parse_positive_int("7", field="chart") == 7


@pytest.mark.parametrize("value", [None, "", "   ", "bad\nname", "x" * 201])
def test_parse_bounded_text_rejects_invalid_template_names(value):
    with pytest.raises(WebParameterError):
        parse_bounded_text(value, field="template", max_chars=200)


def test_parse_bounded_text_trims_valid_name():
    assert parse_bounded_text("  momentum  ", field="template") == "momentum"


def test_chart_routes_validate_before_db_and_handle_not_found():
    charts = route_source("tv_charts")
    assert "parse_positive_int" in charts
    assert charts.index("parse_positive_int") < charts.index("services.database.tv_chart_get")
    assert "chart_not_found" in charts
    assert "invalid_chart_id" in charts


def test_template_routes_validate_and_handle_not_found():
    templates = route_source("tv_study_templates")
    assert "parse_bounded_text" in templates
    assert "template_not_found" in templates
    assert "invalid_template_name" in templates
