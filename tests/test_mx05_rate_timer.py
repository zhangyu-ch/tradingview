from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "web/tradingview_zy_chart/cl_app/templates/index.html"


def _template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def _timer_helpers(source: str) -> str:
    start = source.index("    function stop_rate_update_timer()")
    end = source.index("    var market_frequencys", start)
    return source[start:end]


def test_rate_timer_never_receives_the_function_result() -> None:
    source = _template()
    assert not re.search(
        r"setInterval\s*\(\s*ZiXuan\.stocks_update_rate\s*\(\s*\)", source
    )
    assert "start_rate_update_timer();" in source
    assert "stop_rate_update_timer();" in source


def test_rate_timer_is_singleton_like_and_periodically_invokes_callback() -> None:
    helpers = _timer_helpers(_template())
    harness = f"""
'use strict';
let callbacks = [];
let cleared = [];
let nextId = 1;
let interval_update_rates;
const ZiXuan = {{ stocks_update_rate: () => {{ calls += 1; }} }};
let calls = 0;
function setInterval(callback, delay) {{
  if (typeof callback !== 'function') throw new Error('callback must be a function');
  if (delay !== 30000) throw new Error('unexpected delay');
  callbacks.push(callback);
  return nextId++;
}}
function clearInterval(id) {{ cleared.push(id); }}
{helpers}
start_rate_update_timer();
if (calls !== 1 || callbacks.length !== 1 || interval_update_rates !== 1) throw new Error('first start failed');
callbacks[0]();
if (calls !== 2) throw new Error('scheduled callback did not run');
start_rate_update_timer();
if (calls !== 3 || callbacks.length !== 2 || interval_update_rates !== 2) throw new Error('restart failed');
if (cleared.length !== 1 || cleared[0] !== 1) throw new Error('old timer was not cleared');
stop_rate_update_timer();
if (cleared.length !== 2 || cleared[1] !== 2 || interval_update_rates !== undefined) throw new Error('stop failed');
"""
    result = subprocess.run(
        ["node", "-e", harness], cwd=ROOT, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_inline_script_remains_javascript_parseable_after_jinja_substitution() -> None:
    source = _template()
    inline_scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>\s*(.*?)\s*</script>", source, re.S | re.I
    )
    assert inline_scripts
    checker = "new Function(process.argv[1]);"
    for javascript in inline_scripts:
        javascript = re.sub(
            r"\{\{\s*market_frequencys\|\s*tojson\s*\}\}", "{}", javascript
        )
        javascript = re.sub(
            r"\{\{\s*market_default_codes\.[^}]+\}\}", "TEST", javascript
        )
        result = subprocess.run(
            ["node", "-e", checker, javascript],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
