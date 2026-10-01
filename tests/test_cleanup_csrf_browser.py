from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEGACY_SECRET = "stored-secret-must-never-reach-browser"
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="real Chromium gate runs only when RUN_BROWSER_TESTS=1",
)


@pytest.fixture(scope="module")
def browser_app(tmp_path_factory):
    directory = tmp_path_factory.mktemp("csrf-browser")
    ready = directory / "ready.json"
    with (directory / "server.log").open("w+", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "test_support/csrf_browser_server.py"),
             str(directory), str(ready), LEGACY_SECRET],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 40
            while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if not ready.exists():
                log.seek(0)
                pytest.fail(f"isolated web app did not start:\n{log.read()}")
            yield json.loads(ready.read_text(encoding="utf-8"))["url"]
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


@pytest.fixture
def browser_page(browser_app):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        options = {"headless": True}
        if executable := os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"):
            options["executable_path"] = executable
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page()
            # Tests never send telemetry or contact a real market provider.
            page.route("**/*", lambda route: route.continue_()
                       if route.request.url.startswith(browser_app + "/")
                       else route.abort())
            yield page
        finally:
            browser.close()


def test_parent_jquery_fetch_xhr_have_exactly_one_token(browser_app, browser_page):
    page = browser_page
    page.goto(browser_app + "/csrf-browser")
    results = page.evaluate("""async () => {
      const token = window.TRADINGVIEW_ZY_CSRF_TOKEN;
      const originalFetch = window.fetch;
      const originalSend = XMLHttpRequest.prototype.send;
      TRADINGVIEW_ZY_CSRF.install(window);
      TRADINGVIEW_ZY_CSRF.install(window);
      const responses = [];
      responses.push(await $.ajax({url: '/csrf-probe', method: 'POST', data: {x: 1}}));
      responses.push(await $.ajax({url: '/csrf-probe', method: 'POST',
        headers: {'X-CSRF-Token': token}}));
      responses.push(await (await fetch('/csrf-probe', {method: 'PUT', body: 'put'})).json());
      responses.push(await (await fetch(new URL('/csrf-probe', location.href),
        {method: 'PATCH', body: 'url-object'})).json());
      responses.push(await (await fetch(new Request(location.origin + '/csrf-probe',
        {method: 'POST', body: 'request-body', headers: {'X-Probe': 'kept'}}))).json());
      const xhr = new XMLHttpRequest();
      const send = (method, explicit) => new Promise((resolve, reject) => {
        xhr.open(method, '/csrf-probe');
        if (explicit) xhr.setRequestHeader('x-cSrF-tOkEn', token);
        xhr.onload = () => xhr.status === 200 ? resolve(JSON.parse(xhr.responseText)) : reject(xhr.status);
        xhr.onerror = reject;
        xhr.send();
      });
      responses.push(await send('DELETE', true));
      responses.push(await send('POST', false));
      const safe = await send('GET', false);
      const wrong = await fetch('/csrf-probe', {method: 'POST', headers: {'X-CSRF-Token': 'wrong'}});
      const explicitWrong = await new Promise(resolve => {
        const x = new XMLHttpRequest(); x.open('POST', '/csrf-probe');
        x.setRequestHeader('X-CSRF-Token', 'wrong'); x.onload = () => resolve(x.status); x.send();
      });
      return {token, responses, safe, fetchOverridesStaleToken: wrong.status,
        explicitWrong, installedOnce: originalFetch === window.fetch && originalSend === XMLHttpRequest.prototype.send};
    }""")
    assert results["installedOnce"] is True
    assert all(response["token"] == results["token"] for response in results["responses"])
    assert results["responses"][2]["body"] == "put"
    assert results["responses"][3]["body"] == "url-object"
    assert results["responses"][4]["body"] == "request-body"
    assert results["responses"][4]["custom"] == "kept"
    assert results["safe"]["token"] is None
    assert results["fetchOverridesStaleToken"] == 200
    assert results["explicitWrong"] == 403


def test_cross_origin_requests_and_forms_do_not_leak_token(browser_app, browser_page):
    page = browser_page
    outbound = []

    def other_origin(route):
        outbound.append(route.request.headers)
        route.fulfill(status=200, body="{}", headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Type": "application/json",
        })

    page.route("https://csrf-other.invalid/**", other_origin)
    page.goto(browser_app + "/csrf-browser")
    result = page.evaluate("""async () => {
      const url = 'https://csrf-other.invalid/probe';
      await fetch(url, {method: 'POST', body: 'fetch'});
      await $.ajax({url, method: 'POST', data: 'jquery'});
      await new Promise(resolve => {
        const x = new XMLHttpRequest(); x.open('POST', url); x.onload = resolve; x.send('xhr');
      });
      const form = document.getElementById('probe-form');
      form.addEventListener('submit', event => event.preventDefault());
      const submit = submitter => {
        form.dispatchEvent(new SubmitEvent('submit', {bubbles: true, cancelable: true, submitter}));
        return form.querySelector('input[name="_csrf_token"]')?.value || null;
      };
      const sameOrigin = submit();
      form.action = url;
      const crossOrigin = submit();
      form.action = '/csrf-probe';
      const restored = submit();
      form.method = 'get';
      const safe = submit();
      form.method = 'post';
      const button = document.createElement('button');
      button.setAttribute('formaction', url); form.appendChild(button);
      const override = submit(button);
      const frame = document.createElement('iframe');
      frame.hidden = true;
      await new Promise(resolve => {
        frame.onload = resolve; frame.src = url; document.body.appendChild(frame);
      });
      const crossFrameInstalled = TRADINGVIEW_ZY_CSRF.install(frame.contentWindow);
      return {sameOrigin, restored, crossOrigin, safe, override, crossFrameInstalled,
        token: TRADINGVIEW_ZY_CSRF_TOKEN};
    }""")
    assert len(outbound) >= 3
    assert all("x-csrf-token" not in headers for headers in outbound)
    assert result["sameOrigin"] == result["restored"] == result["token"]
    assert result["crossOrigin"] is result["safe"] is result["override"] is None
    assert result["crossFrameInstalled"] is False


def test_real_chart_iframe_saves_reloads_and_deletes_layout(browser_app, browser_page):
    page = browser_page
    with page.expect_response(lambda response:
            "/tv/1.1/charts" in response.url and response.request.method == "POST", timeout=60000) as saved:
        page.goto(browser_app + "/csrf-browser?chart=1")
    assert saved.value.status == 200
    token = page.evaluate("TRADINGVIEW_ZY_CSRF_TOKEN")
    assert saved.value.request.headers["x-csrf-token"] == token
    page.wait_for_function("window.chartReady === true")
    iframe = next(frame for frame in page.frames if frame.url.startswith("blob:"))
    assert iframe.evaluate("document.querySelector('meta[name=csrf-token]')") is None
    assert iframe.evaluate("document.baseURI").startswith(browser_app)
    assert page.evaluate("TRADINGVIEW_ZY_CSRF.install(document.querySelector('#tv_chart_container_test iframe').contentWindow)") is True

    # The parent uses the real widget API; the requests originate in its iframe.
    saved_records = page.evaluate("new Promise(resolve => manager.widget.getSavedCharts(resolve))")
    assert len(saved_records) == 1
    assert saved_records[0]["name"] == "default"
    page.evaluate("""async () => {
      await manager.widget.activeChart().createShape(
        {time: Math.floor(Date.now()/86400000)*86400 - 86400, price: 100},
        {shape: 'horizontal_line'});
      await new Promise((resolve, reject) => manager.widget.saveChartToServer(resolve, reject,
        {defaultChartName: 'default'}));
    }""")
    assert page.evaluate("manager.widget.activeChart().getAllShapes().length") == 1
    page.evaluate("record => manager.widget.loadChartFromServer(record)", saved_records[0])
    page.wait_for_function("manager.widget.activeChart().getAllShapes().length === 1")
    with page.expect_response(lambda response:
            "/tv/1.1/charts" in response.url and response.request.method == "DELETE") as deleted:
        page.evaluate("id => new Promise(resolve => manager.widget.removeChartFromServer(id, resolve))",
                      saved_records[0]["id"])
    assert deleted.value.status == 200
    assert deleted.value.request.headers["x-csrf-token"] == token
    assert page.evaluate("new Promise(resolve => manager.widget.getSavedCharts(resolve))") == []


def test_content_table_style_is_opt_in(browser_app, browser_page):
    page = browser_page
    page.goto(browser_app + "/csrf-browser")
    borders = page.evaluate("""() => Object.fromEntries(['plain', 'content'].map(id =>
      [id, ['', ' tr', ' td', ' th'].map(selector =>
        getComputedStyle(document.querySelector('#' + id + selector)).borderTopStyle)]))""")
    assert borders == {"plain": ["none"] * 4, "content": ["solid"] * 4}


def test_settings_form_saves_proxy_without_exposing_legacy_secret(browser_app, browser_page):
    page = browser_page
    console = []
    errors = []
    page.on("console", lambda message: console.append(message.text))
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(browser_app + "/csrf-browser")
    response = page.goto(browser_app + "/setting")
    assert response.status == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert LEGACY_SECRET not in response.text()
    assert page.locator('input[name="proxy_host"]').input_value() == "127.0.0.1"
    assert page.locator('input[name="proxy_port"]').input_value() == "7890"
    assert page.locator('input[name="fs_app_secret"]').count() == 0
    assert LEGACY_SECRET not in page.content()

    page.locator('input[name="proxy_host"]').fill(" browser-proxy.invalid ")
    page.locator('input[name="proxy_port"]').fill(" 1080 ")
    with page.expect_response(lambda response:
            response.url == browser_app + "/setting/save"
            and response.request.method == "POST") as saved:
        page.get_by_role("button", name="保存").click()
    assert saved.value.status == 200
    assert saved.value.json() == {"ok": True}
    assert LEGACY_SECRET not in saved.value.request.post_data
    assert LEGACY_SECRET not in saved.value.text()
    page.reload()
    assert page.locator('input[name="proxy_host"]').input_value() == "browser-proxy.invalid"
    assert page.locator('input[name="proxy_port"]').input_value() == "1080"
    assert page.locator('input[name="fs_app_secret"]').count() == 0
    assert LEGACY_SECRET not in page.content()
    assert all(LEGACY_SECRET not in message for message in console)
    assert errors == []
