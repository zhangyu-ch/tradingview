import json
import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


ROOT = Path(__file__).resolve().parents[1]
STATIC_JS = ROOT / "web/tradingview_zy_chart/cl_app/static/js"
TEMPLATES = ROOT / "web/tradingview_zy_chart/cl_app/templates"
SAFE_DOM_JS = STATIC_JS / "safe_dom.js"
ZIXUAN_JS = STATIC_JS / "zixuan.js"
ALERT_JS = STATIC_JS / "alert.js"
UTILS_JS = STATIC_JS / "utils.js"
INDEX_TEMPLATE = TEMPLATES / "index.html"
XUANGU_TEMPLATE = TEMPLATES / "xuangu_list.html"


def run_node(source: str) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is required for first-party JavaScript security tests")
    completed = subprocess.run(
        [node, "-e", source],
        cwd=ROOT,
        text=True,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def test_xuangu_metadata_uses_json_data_and_text_nodes_only():
    source = XUANGU_TEMPLATE.read_text(encoding="utf-8")

    assert "eval(" not in source
    assert "const task_infos = {{ task_infos | tojson }};" in source
    assert ".task_memo').text(" in source
    assert ".frequency_memo').text(" in source
    assert ".task_memo').html(" not in source
    assert ".frequency_memo').html(" not in source


def test_safe_dom_is_loaded_before_every_dynamic_renderer():
    index = INDEX_TEMPLATE.read_text(encoding="utf-8")
    safe_index = index.index("js/safe_dom.js")

    assert safe_index < index.index("js/zixuan.js")
    assert safe_index < index.index("js/alert.js")


def test_safe_dom_and_watchlist_renderers_escape_html_attributes_and_css():
    payload = '<img src=x onerror=globalThis.pwned=true>"\'&'
    script = f"""
const assert = require('assert');
const SafeDom = require({json.dumps(str(SAFE_DOM_JS))});
const watchlist = require({json.dumps(str(ZIXUAN_JS))});
const payload = {json.dumps(payload)};

assert.strictEqual(
  SafeDom.escapeHtml(payload),
  '&lt;img src=x onerror=globalThis.pwned=true&gt;&quot;&#39;&amp;'
);
assert.strictEqual(SafeDom.safeCssColor('#16baaa'), '#16baaa');
assert.strictEqual(SafeDom.safeCssColor('red; background:url(javascript:1)'), '');

const codeCell = watchlist.renderZixuanCodeCell({{
  name: payload,
  code: 'A" onmouseover=alert(1)',
  color: 'red;position:fixed',
}});
assert(!codeCell.includes('<img'));
assert(!codeCell.includes('style='));
assert(codeCell.includes('&lt;img'));
assert(codeCell.includes('&quot; onmouseover'));

const rateCell = watchlist.renderZixuanRateCell({{
  code: 'A" onmouseover=alert(1)',
  rate: payload,
  price: payload,
}});
assert(!rateCell.includes('<img'));
assert(rateCell.includes('data-code="A&quot; onmouseover=alert(1)"'));

class Element {{
  constructor(tag) {{
    this.tag = tag;
    this.dataset = {{}};
    this.style = {{}};
    this.children = [];
    this.textContent = '';
    this.className = '';
  }}
  replaceChildren() {{ this.children = []; }}
  append(...children) {{ this.children.push(...children); }}
}}
const target = new Element('div');
target.dataset.code = payload;
global.document = {{
  querySelectorAll(selector) {{ return selector === '.code_rate' ? [target] : []; }},
  createElement(tag) {{ return new Element(tag); }},
}};
watchlist.updateZixuanRateElements(
  {{code: payload, rate: payload, price: payload}},
  '#ff5722'
);
assert.strictEqual(target.children.length, 2);
assert.strictEqual(target.children[0].textContent, payload + '%');
assert.strictEqual(target.children[1].textContent, payload);
assert.strictEqual(globalThis.pwned, undefined);

const searchItems = watchlist.sanitizeSearchItems([{{name: payload, value: payload}}]);
assert.strictEqual(searchItems[0].name, SafeDom.escapeHtml(payload));
assert.strictEqual(searchItems[0].raw_name, payload);
assert.strictEqual(searchItems[0].value, payload);
assert.strictEqual(
  watchlist.sanitizeSearchItems(searchItems)[0].name,
  SafeDom.escapeHtml(payload)
);
"""
    run_node(script)


def test_alert_renderer_escapes_every_server_controlled_field():
    payload = '<svg onload="globalThis.pwned=1">&'
    script = f"""
const assert = require('assert');
const renderer = require({json.dumps(str(ALERT_JS))});
const payload = {json.dumps(payload)};
const output = renderer.recordRow({{
  name: payload,
  code: payload,
  frequency: payload,
  event_type: payload,
  action: payload,
  score: payload,
  msg: payload,
  datetime_str: payload,
  task_name: payload,
}});
assert(!output.includes('<svg'));
assert(!output.includes(payload));
assert.strictEqual((output.match(/&lt;svg/g) || []).length, 9);
assert.strictEqual(globalThis.pwned, undefined);
"""
    run_node(script)


def test_dynamic_select_options_are_created_as_text_nodes():
    script = f"""
const assert = require('assert');
const SafeDom = require({json.dumps(str(SAFE_DOM_JS))});
const payload = '<svg onload=globalThis.pwned=true>';
const select = {{
  children: [],
  ownerDocument: {{
    createElement(tag) {{ return {{tag, value: '', textContent: ''}}; }}
  }},
  appendChild(child) {{ this.children.push(child); }}
}};
const option = SafeDom.appendOption(select, payload, payload);
assert.strictEqual(option.value, payload);
assert.strictEqual(option.textContent, payload);
assert.strictEqual(globalThis.pwned, undefined);
"""
    run_node(script)


def test_xuangu_template_autoescapes_options_and_script_json():
    environment = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
    )
    environment.globals["url_for"] = (
        lambda endpoint, filename: f"/static/{filename}"
    )
    payload = '\"><img src=x onerror="globalThis.pwned=1">'

    rendered = environment.get_template("xuangu_list.html").render(
        market="a",
        tasks={payload: {"name": payload}},
        task_infos={
            payload: {"task_memo": payload, "frequency_memo": payload}
        },
        frequencys={"d": payload},
        zixuan_groups=[{"name": payload}],
    )

    assert payload not in rendered
    assert "<img src=x" not in rendered
    assert "\\u003cimg" in rendered
    assert "&lt;img" in rendered


def test_targeted_sources_do_not_reintroduce_raw_html_sinks():
    targeted = [
        ZIXUAN_JS.read_text(encoding="utf-8"),
        ALERT_JS.read_text(encoding="utf-8"),
        XUANGU_TEMPLATE.read_text(encoding="utf-8"),
    ]
    for source in targeted:
        assert "eval(" not in source
        assert ".html(" not in source
        assert "innerHTML =" not in source
        assert "insertAdjacentHTML" not in source

    alert = targeted[1]
    assert "AlertSafeDom.recordRow(d)" in alert
    assert "<option value='${item.task_name}'" not in alert
    assert '$("<option>",' in alert


def test_cached_search_history_uses_raw_label_not_escaped_markup():
    source = UTILS_JS.read_text(encoding="utf-8")

    assert "data.arr[0].raw_name" in source
    assert "JSON.stringify(uniqueItems)" in source
