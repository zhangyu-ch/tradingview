from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script/remediation/check_secret_exposure.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("secret_exposure_guard", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_setting_page_has_no_secret_exposure() -> None:
    assert _load_checker().validate_root(ROOT) == []


def test_guard_detects_original_template_and_console_leak() -> None:
    app = '''
def setting():
    config = {"fs_app_secret": stored_secret}
    return config
@app.route("/setting/save", methods=["POST"])
def save():
    pass
'''
    template = '''
<input type="text" name="fs_app_secret" value="{{ fs_app_secret }}">
<script>console.log(data.field);</script>
'''
    errors = _load_checker().validate(app, template)
    joined = "\n".join(errors)
    assert "embeds the persisted" in joined
    assert "type=password" in joined
    assert "browser console" in joined
    assert "GET route returns" in joined
    assert "non-cacheable" in joined
