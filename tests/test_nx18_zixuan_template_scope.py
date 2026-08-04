from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ZIXUAN_JS = ROOT / "web/tradingview_zy_chart/cl_app/static/js/zixuan.js"


def test_watchlist_template_is_block_local() -> None:
    source = ZIXUAN_JS.read_text(encoding="utf-8")
    assert "const templet =" in source
    assert "\n              templet =" not in source
    assert "\n            templet =" not in source


def test_real_script_renders_checked_and_unchecked_without_global_leak() -> None:
    script = f"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync({json.dumps(str(ZIXUAN_JS))}, 'utf8');
let captured = null;
const jquery = function () {{ return {{ change() {{}} }}; }};
jquery.ajax = function (options) {{
  options.success([
    {{ exists: 0, zx_name: '未选', code: 'A' }},
    {{ exists: 1, zx_name: '已选', code: 'B' }}
  ]);
}};
const context = {{
  console,
  $: jquery,
  Utils: {{ get_market() {{ return 'a'; }}, get_code() {{ return 'SH.000001'; }} }},
  layui: {{
    each(items, callback) {{ items.forEach((item, index) => callback(index, item)); }},
    dropdown: {{ reloadData(_id, options) {{ captured = options.data; }} }}
  }}
}};
vm.createContext(context);
vm.runInContext(source, context);
context.ZiXuan.render_zixuan_opts();
if (Object.prototype.hasOwnProperty.call(context, 'templet')) {{
  throw new Error('templet leaked to the global context');
}}
if (!captured || captured.length !== 2) {{
  throw new Error('watchlist dropdown data was not produced');
}}
if (captured[0].templet.includes('checked')) {{
  throw new Error('unchecked item was rendered as checked');
}}
if (!captured[1].templet.includes('checked')) {{
  throw new Error('checked item lost its checked attribute');
}}
"""
    subprocess.run(["node", "-e", script], check=True, cwd=ROOT)


def test_zixuan_javascript_is_syntactically_valid() -> None:
    subprocess.run(["node", "--check", str(ZIXUAN_JS)], check=True, cwd=ROOT)
