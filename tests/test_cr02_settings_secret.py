from __future__ import annotations

import importlib.util
import os
import stat
import sys
import types
from pathlib import Path

import pytest

from test_support.web_routes import route_source

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

def _load_web_security_without_external_werkzeug():
    security_stub = types.ModuleType("werkzeug.security")
    security_stub.check_password_hash = lambda _stored, _candidate: False
    werkzeug_stub = types.ModuleType("werkzeug")
    werkzeug_stub.security = security_stub

    previous_werkzeug = sys.modules.get("werkzeug")
    previous_security = sys.modules.get("werkzeug.security")
    sys.modules["werkzeug"] = werkzeug_stub
    sys.modules["werkzeug.security"] = security_stub
    try:
        path = SRC / "tradingview_zy" / "web_security.py"
        spec = importlib.util.spec_from_file_location("cr02_web_security", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_werkzeug is None:
            sys.modules.pop("werkzeug", None)
        else:
            sys.modules["werkzeug"] = previous_werkzeug
        if previous_security is None:
            sys.modules.pop("werkzeug.security", None)
        else:
            sys.modules["werkzeug.security"] = previous_security


def test_remote_passwordless_bind_is_rejected_and_secret_is_persistent(tmp_path):
    web_security = _load_web_security_without_external_werkzeug()

    with pytest.raises(RuntimeError, match="尚未配置登录密码"):
        web_security.validate_web_access("0.0.0.0", "", "")
    web_security.validate_web_access("127.0.0.1", "", "")

    first = web_security.resolve_web_secret_key(tmp_path, environ={})
    second = web_security.resolve_web_secret_key(tmp_path, environ={})
    assert first == second
    assert len(first.encode("utf-8")) >= 32
    if os.name != "nt":
        assert stat.S_IMODE((tmp_path / "web_secret_key").stat().st_mode) == 0o600


def test_setting_page_source_never_embeds_or_logs_the_saved_secret():
    get_block = route_source("setting")
    template_source = (
        ROOT
        / "web"
        / "tradingview_zy_chart"
        / "cl_app"
        / "templates"
        / "setting.html"
    ).read_text(encoding="utf-8")

    assert '"fs_app_secret":' not in get_block
    assert "fs_app_secret" not in get_block
    normalized_get_block = get_block.replace("'", '"')
    assert '"Cache-Control": "no-store"' in normalized_get_block
    assert '"Pragma": "no-cache"' in normalized_get_block
    assert "fs_app_secret" not in template_source
    assert "{{ fs_app_secret }}" not in template_source
    assert "console.log(data.field)" not in template_source
    assert 'name="proxy_host"' in template_source
    assert 'name="proxy_port"' in template_source
