from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from flask import Flask, render_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "web/tradingview_zy_chart/cl_app/templates"


def test_page_start_and_watchlist_events_own_one_periodic_rate_timer() -> None:
    app = Flask("rate_timer", template_folder=str(TEMPLATES))
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf"
    with app.test_request_context():
        html = render_template(
            "index.html",
            market_catalog=[{"value": "a", "desc": "A股"}],
            market_frequencys={"a": {"d": "日线"}},
            market_default_codes={"a": "SH.000001"},
            default_market="a",
        )
    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>\s*(.*?)\s*</script>", html, re.S | re.I
    )
    harness = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const ready = [];
const events = new Map();
const timers = new Map();
let nextId = 1;
let updates = 0;
const jquery = (target) => {
  if (typeof target === 'function') { ready.push(target); return; }
  return {
    attr: (name) => target[name],
    empty() {}, css() {}, append() {}, hide() {}
  };
};
const context = {
  console,
  $: jquery,
  window: { innerHeight: 1000, JSON },
  document: { getElementsByTagName: () => [{}] },
  localStorage: { tv_chart: '{}' },
  setInterval(callback, delay) {
    assert.equal(typeof callback, 'function', 'interval must receive a callable');
    const id = nextId++;
    timers.set(id, { callback, delay });
    return id;
  },
  clearInterval(id) { timers.delete(id); },
  ZiXuan: {
    init_zixuan_opts() {}, render_zixuan_opts() {},
    stocks_update_rate() { updates += 1; }
  },
  Charts: { show_tv_chart() { return {}; } },
  Utils: {
    get_market: () => 'a', get_local_data: () => 'single', render_fixbar() {}
  },
  layui: {
    use(callback) { callback(); },
    dropdown: { render() {} },
    element: { on(name, callback) { events.set(name, callback); } },
    form: { val() {}, on() {} }
  }
};
vm.createContext(context);
for (const script of JSON.parse(process.argv[1])) vm.runInContext(script, context);
for (const callback of ready) callback();
assert.equal(updates, 1, 'page startup must refresh immediately');
assert.equal(timers.size, 1, 'page startup must schedule one timer');
const firstId = [...timers.keys()][0];
assert.equal(timers.get(firstId).delay, 30000);
timers.get(firstId).callback();
assert.equal(updates, 2, 'scheduled refresh must run');

const collapse = events.get('collapse(collapse-opts)');
assert.equal(typeof collapse, 'function', 'page must wire the collapse event');
const watchlist = { 'data-ca-title': '自选组' };
collapse({ title: watchlist, show: true });
assert.equal(updates, 3);
assert.equal(timers.size, 1, 'reopening must replace rather than leak the timer');
assert.equal(timers.has(firstId), false, 'old timer must be cancelled');
assert.equal([...timers.values()][0].delay, 30000);
collapse({ title: watchlist, show: false });
assert.equal(timers.size, 0, 'closing must cancel the timer');
collapse({ title: watchlist, show: false });
collapse({ title: { 'data-ca-title': '关于' }, show: true });
assert.equal(timers.size, 0, 'unrelated panels must not start rate refresh');
assert.equal(updates, 3);
collapse({ title: watchlist, show: true });
assert.equal(timers.size, 1);
assert.equal(updates, 4);
[...timers.values()][0].callback();
assert.equal(updates, 5);
'''
    result = subprocess.run(
        ["node", "-e", harness, json.dumps(scripts)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
