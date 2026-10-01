from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from flask import Flask, render_template


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


def test_symbol_changes_refresh_watchlist_once_for_all_chart_layouts() -> None:
    app = Flask("chart_symbols", template_folder=str(INDEX_HTML.parent))
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf"
    with app.test_request_context():
        html = render_template(
            "index.html",
            market_catalog=[{"value": "currency", "desc": "数字货币"}],
            market_frequencys={"currency": {"d": "日线"}},
            market_default_codes={"currency": "BTC/USDT"},
            default_market="currency",
        )
    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>\s*(.*?)\s*</script>", html, re.S | re.I
    )
    harness = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const inputs = JSON.parse(fs.readFileSync(0, 'utf8'));
for (const count of [1, 2, 4]) {
  for (const deferred of [false, true]) {
    const state = {market: 'currency', currency_code: 'BTC/USDT'};
    const requests = [];
    const pending = [];
    const symbolEvents = [];
    const targets = [];
    let reloads = 0;
    const jquery = () => ({});
    jquery.ajax = options => requests.push(options);
    const context = {
      console: {log() {}, error() {}}, setTimeout, clearTimeout,
      $: jquery,
      window: {JSON, TRADINGVIEW_ZY_CSRF: {install: () => true}},
      document: {
        getElementsByTagName: () => [{}],
        getElementById: () => ({querySelector: () => ({contentWindow: {}})})
      },
      localStorage: {tv_chart: '{}'},
      location: {reload() { reloads++; }},
      Utils: {
        get_market: () => state.market,
        get_code: () => state[state.market + '_code'],
        set_local_data(key, value) { state[key] = value; }
      },
      layui: {each: (items, fn) => items.forEach((item, index) => fn(index, item))}
    };
    vm.createContext(context);
    vm.runInContext(inputs.charts, context);
    vm.runInContext(inputs.watchlist, context);
    for (const script of inputs.inline) vm.runInContext(script, context);
    for (let i = 0; i < count; i++) {
      const manager = vm.runInContext(`new ChartManager('${i}')`, context);
      let changed;
      const chart = {
        onSymbolChanged: () => ({subscribe(_, callback) { changed = callback; }}),
        onIntervalChanged: () => ({subscribe() {}}),
        onDataLoaded: () => ({subscribe() {}}),
        setSymbol(ticker) {
          targets.push(ticker);
          if (deferred) pending.push(() => changed({ticker}));
          else changed({ticker});
        }
      };
      manager.widget = {
        activeChart: () => chart,
        headerReady: () => ({then() {}}),
        onChartReady(callback) { callback(); },
        subscribe() {}, saveChartToServer() {}
      };
      manager.setupEventListeners();
      symbolEvents.push(changed);
      context.chart_widgets.push(manager.widget);
    }
    context.change_chart_ticker('currency', 'ETH/USDT');
    for (const callback of pending) callback();
    assert.deepEqual(targets, Array(count).fill('currency:ETH/USDT'));
    assert.equal(requests.length, 1, `${count} charts, deferred=${deferred}`);
    assert.equal(requests[0].type, 'GET');
    assert.equal(requests[0].url, '/get_stock_zixuan/currency/ETH__USDT');
    assert.equal(state.currency_code, 'ETH/USDT');

    requests.length = 0;
    for (const callback of symbolEvents) callback({ticker: 'currency:ETH/USDT'});
    assert.equal(requests.length, 0, 'repeated widget notifications do not refetch');
    symbolEvents[0]({ticker: 'currency:SOL/USDT'});
    assert.equal(requests.length, 1, 'a direct widget change still refreshes');
    assert.equal(requests[0].url, '/get_stock_zixuan/currency/SOL__USDT');
    assert.equal(state.currency_code, 'SOL/USDT');
    context.ZiXuan.render_zixuan_opts();
    assert.equal(requests.length, 2, 'membership changes may explicitly refresh the same code');
    symbolEvents[0](null);
    symbolEvents[0]({ticker: 'invalid'});
    symbolEvents[0]({ticker: 'hk:00700'});
    assert.equal(reloads, 1, 'cross-market changes keep the page reload contract');
    assert.equal(state.market, 'hk');
    assert.equal(requests.length, 2);
  }
}
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=json.dumps({
            "charts": CHARTS_JS.read_text(encoding="utf-8"),
            "watchlist": (CHARTS_JS.parent / "zixuan.js").read_text(encoding="utf-8"),
            "inline": scripts,
        }),
        cwd=ROOT, text=True, capture_output=True, check=False, timeout=30,
    )
    assert result.returncode == 0, result.stderr
