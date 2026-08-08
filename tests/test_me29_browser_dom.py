from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BROWSER_TESTS") != "1",
    reason="real Chromium gate runs only in the dedicated CI job",
)


def test_rendered_settings_dom_never_contains_existing_secret() -> None:
    from jinja2 import Environment, FileSystemLoader
    from playwright.sync_api import sync_playwright

    sentinel = "stored-secret-must-never-reach-dom"
    template_root = ROOT / "web/tradingview_zy_chart/cl_app/templates"
    environment = Environment(loader=FileSystemLoader(str(template_root)), autoescape=True)
    environment.globals["url_for"] = lambda endpoint, **values: f"/{values.get('filename', '')}"
    environment.globals["csrf_token"] = lambda: "browser-contract-test-csrf-token"
    environment.loader = FileSystemLoader([str(template_root)])
    template = environment.get_template("setting.html")
    html = template.render(
        fs_app_id="cli_test",
        fs_app_secret=sentinel,
        fs_app_secret_configured=True,
        fs_user_id="ou_test",
        proxy_host="127.0.0.1",
        proxy_port="7890",
    )
    # Avoid external requests and unrelated JavaScript execution in this DOM-only gate.
    html = re.sub(r"<script[^>]+src=[^>]+></script>", "", html, flags=re.I)

    assert sentinel not in html
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            field = page.locator('input[name="fs_app_secret"]')
            assert field.count() == 1
            assert field.get_attribute("type") == "password"
            assert field.get_attribute("value") == ""
            assert field.get_attribute("autocomplete") == "new-password"
            assert "留空保持不变" in (field.get_attribute("placeholder") or "")
            assert sentinel not in page.content()
        finally:
            browser.close()
