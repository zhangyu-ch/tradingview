from __future__ import annotations

import importlib.util
import os
import stat
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from tradingview_zy.secret_store import ManagedSecretStore  # noqa: E402
from tradingview_zy.settings_security import (  # noqa: E402
    feishu_secret_is_configured,
    merge_feishu_settings,
    migrate_feishu_settings,
)


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


def test_blank_feishu_secret_preserves_reference_and_non_blank_rotates(tmp_path):
    store = ManagedSecretStore(tmp_path)
    existing = {
        "fs_app_id": "old-id",
        "fs_app_secret": "sentinel-secret",
        "fs_user_id": "old-user",
    }
    migrated, changed = migrate_feishu_settings(existing, store=store)
    assert changed is True
    assert "fs_app_secret" not in migrated
    assert migrated["fs_app_secret_ref"].startswith("managed://")
    assert feishu_secret_is_configured(migrated, store=store)

    preserved, superseded = merge_feishu_settings(
        migrated,
        app_id=" new-id ",
        app_secret="   ",
        user_id=" new-user ",
        store=store,
    )
    assert preserved == {
        "fs_app_id": "new-id",
        "fs_app_secret_ref": migrated["fs_app_secret_ref"],
        "fs_user_id": "new-user",
    }
    assert superseded is None

    rotated, superseded = merge_feishu_settings(
        migrated,
        app_id="new-id",
        app_secret=" replacement-secret ",
        user_id="new-user",
        store=store,
    )
    assert rotated["fs_app_secret_ref"].startswith("managed://")
    assert rotated["fs_app_secret_ref"] != migrated["fs_app_secret_ref"]
    assert superseded == migrated["fs_app_secret_ref"]
    assert "replacement-secret" not in repr(rotated)


def test_setting_page_source_never_embeds_or_logs_the_saved_secret():
    app_source = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "__init__.py"
    ).read_text(encoding="utf-8")
    template_source = (
        ROOT
        / "web"
        / "tradingview_zy_chart"
        / "cl_app"
        / "templates"
        / "setting.html"
    ).read_text(encoding="utf-8")

    get_start = app_source.index('def setting():')
    save_route = app_source.index('@app.route("/setting/save"', get_start)
    get_block = app_source[get_start:save_route]

    assert '"fs_app_secret":' not in get_block
    assert "fs_app_secret_configured" in get_block
    assert '"Cache-Control": "no-store"' in get_block
    assert 'type="password" name="fs_app_secret" value=""' in template_source
    assert "{{ fs_app_secret }}" not in template_source
    assert "console.log(data.field)" not in template_source
    assert "留空保持不变" in template_source
