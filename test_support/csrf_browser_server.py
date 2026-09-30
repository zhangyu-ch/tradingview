"""Isolated real-app host for the opt-in CSRF browser tests (no live providers)."""
from __future__ import annotations

import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "web/tradingview_zy_chart")]


def main() -> None:
    from flask import render_template_string, request
    from flask_login import login_user
    from werkzeug.serving import make_server

    data_path, ready_path = map(Path, sys.argv[1:3])
    # Never import the developer's config.py or touch their database/secrets.
    config_path = ROOT / "src/tradingview_zy/config.py.demo"
    config = types.ModuleType("tradingview_zy.config")
    exec(compile(config_path.read_text(encoding="utf-8"), str(config_path), "exec"), config.__dict__)
    config.DATA_PATH = str(data_path)
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "csrf_browser"
    sys.modules[config.__name__] = config
    for name in ("TRADINGVIEW_ZY_LOGIN_PASSWORD", "TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH"):
        os.environ.pop(name, None)

    from cl_app import create_app
    from cl_app.blueprints.auth import LoginUser

    app = create_app({
        "TESTING": True,
        "WEB_HOST": "127.0.0.1",
        "WEB_SECRET_KEY": "browser-test-session-key-not-for-deployment",
        "LOGIN_PWD": "",
        "LOGIN_PWD_HASH": "",
        "WEB_CSRF_TRUSTED_ORIGINS": (),
    })

    @app.get("/csrf-browser")
    def browser_page():
        login_user(LoginUser(), remember=False)
        return render_template_string("""<!doctype html>
<html><head><meta charset="utf-8"><title>CSRF browser regression</title>
<script src="/static/jquery-3.7.0.min.js"></script>
{% include 'dark.html' %}
<link rel="stylesheet" href="/static/css/app.css">
</head><body>
<table id="plain"><tr><td>plain</td></tr></table>
<table id="content" class="content-table"><tr><td>content</td></tr></table>
<form id="probe-form" method="post" action="/csrf-probe"></form>
<div id="tv_chart_container_test" style="height:600px;width:1000px"></div>
{% if chart %}
<script src="/static/charting_library/charting_library.standalone.js"></script>
<script src="/static/js/charts.js"></script>
<script>
window.Utils = {
  get_market: () => "a", get_code: () => "SH.000001",
  get_local_data: key => key === "theme" ? "light" : "1D",
  set_local_data: () => {}
};
window.ZiXuan = {};
// Only market data is synthetic; ChartManager, widget, iframe fetch, storage
// routes, CSRF validation and SQLite persistence are production code.
window.Datafeeds = { UDFCompatibleDatafeed: function () {
  return {
    onReady: cb => setTimeout(() => cb({supported_resolutions: ["1D"]}), 0),
    resolveSymbol: (name, cb) => setTimeout(() => cb({
      name: name, ticker: name, description: "Browser fixture", type: "stock",
      session: "24x7", timezone: "Asia/Shanghai", exchange: "TEST",
      minmov: 1, pricescale: 100, has_intraday: false, has_daily: true,
      supported_resolutions: ["1D"], volume_precision: 0, data_status: "endofday"
    }), 0),
    getBars: (symbol, resolution, range, cb) => {
      const bars = [];
      const end = Math.floor(range.to / 86400) * 86400;
      for (let day = range.countBack; day > 0; day--) {
        bars.push({time: (end - day * 86400) * 1000, open: 100,
          high: 102, low: 99, close: 101, volume: 1000});
      }
      setTimeout(() => cb(bars, {noData: false}), 0);
    },
    subscribeBars: () => {}, unsubscribeBars: () => {}, searchSymbols: (a,b,c,cb) => cb([])
  };
}};
window.manager = new ChartManager("test");
manager.getCustomIndicators = () => Promise.resolve([]);
manager.init();
manager.widget.onChartReady(() => {window.chartReady = true;});
</script>
{% endif %}
</body></html>""", chart=request.args.get("chart") == "1")

    @app.route("/csrf-probe", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def probe():
        return {
            "method": request.method,
            "token": request.headers.get("X-CSRF-Token"),
            "body": request.get_data(as_text=True),
            "custom": request.headers.get("X-Probe"),
            "form_token": request.form.get("_csrf_token"),
        }

    server = make_server("127.0.0.1", 0, app, threaded=True)
    ready_path.write_text(json.dumps({"url": f"http://127.0.0.1:{server.server_port}"}), encoding="utf-8")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
