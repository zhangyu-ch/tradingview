from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHARTS_JS = ROOT / "web/tradingview_zy_chart/cl_app/static/js/charts.js"
INDEX_HTML = ROOT / "web/tradingview_zy_chart/cl_app/templates/index.html"


def _calls(source: str) -> list[str]:
    return re.findall(r"Charts\.show_tv_chart\(([^()]*)\)", source)


def test_all_chart_display_calls_use_the_one_argument_contract() -> None:
    source = INDEX_HTML.read_text(encoding="utf-8")
    calls = _calls(source)

    assert len(calls) == 6
    assert all("," not in call for call in calls)
    assert "chart_height" not in source
    assert "win_width" not in source


def test_container_layout_still_owns_chart_dimensions() -> None:
    source = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="tv_charts_area"' in source
    assert "height: 100%" in source
    assert "win_height * 0.7" in source
    assert "win_height * 0.3" in source
    assert "win_height / 2" in source
    assert 'style: "flex:1;"' in source
    assert 'style: "width:50%;height:50%;float:left;"' in source


def test_chart_api_documents_and_exposes_one_parameter() -> None:
    source = CHARTS_JS.read_text(encoding="utf-8")
    assert "@param {string} id" in source
    assert "autosized TradingView widget" in source

    script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(CHARTS_JS))}, 'utf8');
const context = {{ console, setTimeout, clearTimeout }};
vm.createContext(context);
vm.runInContext(source, context);
if (!context.Charts || typeof context.Charts.show_tv_chart !== 'function') {{
  throw new Error('Charts.show_tv_chart was not exported');
}}
if (context.Charts.show_tv_chart.length !== 1) {{
  throw new Error(`expected arity 1, got ${{context.Charts.show_tv_chart.length}}`);
}}
"""
    subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


def test_modified_javascript_is_syntactically_valid() -> None:
    subprocess.run(["node", "--check", str(CHARTS_JS)], check=True, cwd=ROOT)
