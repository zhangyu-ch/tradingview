from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
import tomllib
import zipfile
from pathlib import Path
from types import SimpleNamespace

from test_support.web_routes import compile_route

ROOT = Path(__file__).resolve().parents[1]


def test_shared_proxy_utils_import_without_notification_sdk_or_secret_store():
    script = textwrap.dedent(
        """
        import importlib.abc
        import sys
        import types

        class ForbidNotifications(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.startswith('lark_oapi') or fullname in {
                    'tradingview_zy.settings_security',
                    'tradingview_zy.messaging_reliability',
                    'tradingview_zy.secret_store',
                }:
                    raise AssertionError('unwanted import: ' + fullname)

        sys.meta_path.insert(0, ForbidNotifications())
        config = types.ModuleType('tradingview_zy.config')
        config.PROXY_HOST, config.PROXY_PORT = 'fallback-host', 7890
        database = types.ModuleType('tradingview_zy.db')
        saved_proxy = {'host': 'saved-host', 'port': '1080'}
        def cache_get(key):
            assert key == 'req_proxy'
            return saved_proxy
        database.db = types.SimpleNamespace(cache_get=cache_get)
        sys.modules['tradingview_zy.config'] = config
        sys.modules['tradingview_zy.db'] = database

        from tradingview_zy.utils import config_get_proxy
        result = config_get_proxy()
        assert result == saved_proxy
        result['host'] = 'mutated'
        assert saved_proxy['host'] == 'saved-host'
        saved_proxy['host'] = ''
        assert config_get_proxy() == {'host': 'fallback-host', 'port': 7890}
        assert not any(name.startswith('lark_oapi') for name in sys.modules)
        """
    )
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_proxy_settings_keep_legacy_notification_data_private_and_untouched():
    from flask import Flask, render_template, request

    sentinel = "legacy-secret-must-not-be-read-or-rendered"
    cached = {
        "req_proxy": {"host": "old-proxy", "port": "7890"},
        "fs_keys": {"fs_app_secret": sentinel},
    }
    reads = []
    writes = []

    def cache_get(key):
        reads.append(key)
        assert key == "req_proxy"
        return cached.get(key)

    def cache_set(key, value):
        writes.append(key)
        assert key == "req_proxy"
        cached[key] = value

    app = Flask(
        "b4_settings",
        template_folder=str(ROOT / "web/tradingview_zy_chart/cl_app/templates"),
    )
    app.jinja_env.globals["csrf_token"] = lambda: "test-csrf"
    namespace = {
        "db": SimpleNamespace(cache_get=cache_get, cache_set=cache_set),
        "request": request,
        "render_template": render_template,
    }
    app.add_url_rule("/setting", view_func=compile_route("setting", namespace))
    app.add_url_rule(
        "/setting/save",
        view_func=compile_route("setting_save", namespace),
        methods=["POST"],
    )
    client = app.test_client()
    response = client.get("/setting")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"
    assert "old-proxy" in response.text
    assert sentinel not in response.text
    assert "fs_app_secret" not in response.text
    assert "飞书" not in response.text

    response = client.post(
        "/setting/save",
        data={
            "proxy_host": " new-proxy ",
            "proxy_port": " 1080 ",
            "fs_app_secret": "stale-browser-form-value",
        },
    )
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert cached["req_proxy"] == {"host": "new-proxy", "port": "1080"}
    assert cached["fs_keys"] == {"fs_app_secret": sentinel}
    assert reads == ["req_proxy"]
    assert writes == ["req_proxy"]


def test_feishu_source_archive_is_complete_and_hash_verified():
    archive = ROOT / "archive/feishu-notifications-legacy.zip"
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read("MANIFEST.json"))
        assert manifest["baseline_commit"] == "7bece6861d9411d11e4573f6b41efc17e4f68db5"
        files = {entry["path"] for entry in manifest["files"]}
        assert {
            "src/tradingview_zy/utils.py",
            "src/tradingview_zy/settings_security.py",
            "src/tradingview_zy/messaging_reliability.py",
            "tests/test_nx03_feishu_config_copy.py",
            "pyproject.toml",
            "uv.lock",
        } <= files
        assert "src/tradingview_zy/config.py" not in files
        for entry in manifest["files"]:
            path = Path(entry["path"])
            assert not path.is_absolute()
            assert ".." not in path.parts
            data = source.read(entry["path"])
            assert len(data) == entry["bytes"]
            assert hashlib.sha256(data).hexdigest() == entry["sha256"]
        assert b"def send_fs_msg(" in source.read("src/tradingview_zy/utils.py")
        assert source.read("RESTORE.md").decode("utf-8").replace("\r\n", "\n") == (
            ROOT / "archive/feishu-notifications.md"
        ).read_text(encoding="utf-8")


def test_notification_runtime_dependencies_and_controls_are_removed():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not any(dep.startswith("lark-oapi") for dep in project["project"]["dependencies"])
    locked = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    assert "lark-oapi" not in {package["name"] for package in locked["package"]}
    for name in ("settings_security.py", "messaging_reliability.py"):
        assert not (ROOT / "src/tradingview_zy" / name).exists()
    for relative in (
        "src/tradingview_zy/config.py.demo",
        "web/tradingview_zy_chart/cl_app/templates/alert.html",
        "web/tradingview_zy_chart/cl_app/static/js/alert.js",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "FEISHU_" not in source
        assert "is_send_msg" not in source
