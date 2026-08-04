from __future__ import annotations

from pathlib import Path

import pytest

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
    source = Path("web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    charts = source[source.index("    def tv_charts(version):"):source.index("    @app.route(\"/tv/<version>/study_templates\"")]
    assert "parse_positive_int" in charts
    assert charts.index("parse_positive_int") < charts.index("db.tv_chart_get")
    assert "chart_not_found" in charts
    assert "invalid_chart_id" in charts


def test_template_routes_validate_and_handle_not_found():
    source = Path("web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    templates = source[source.index("    def tv_study_templates(version):"):source.index("    @app.route(\"/tv/<version>/drawings\"")]
    assert "parse_bounded_text" in templates
    assert "template_not_found" in templates
    assert "invalid_template_name" in templates
