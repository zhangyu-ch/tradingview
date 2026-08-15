import os
import re
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

try:
    from werkzeug.security import generate_password_hash
except (ModuleNotFoundError, ImportError):
    import hashlib
    import hmac
    import types

    def generate_password_hash(candidate: str) -> str:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return f"test-sha256${digest}"

    def _check_password_hash(stored: str, candidate: str) -> bool:
        return hmac.compare_digest(stored, generate_password_hash(candidate))

    werkzeug = types.ModuleType("werkzeug")
    security = types.ModuleType("werkzeug.security")
    security.generate_password_hash = generate_password_hash
    security.check_password_hash = _check_password_hash
    werkzeug.security = security
    sys.modules["werkzeug"] = werkzeug
    sys.modules["werkzeug.security"] = security

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradingview_zy.web_security import (
    LoginAttemptLimiter,
    resolve_login_credentials,
    resolve_web_secret_key,
    validate_web_access,
    verify_login_password,
)


def _import_cl_app_or_skip():
    for dependency in ("flask", "flask_login", "apscheduler", "pinyin", "tzlocal"):
        pytest.importorskip(dependency)
    import cl_app

    return cl_app


def _csrf_from_login_page(client) -> str:
    response = client.get("/login")
    assert response.status_code == 200
    match = re.search(
        r'name="_csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match is not None
    return match.group(1)


def _csrf_from_authenticated_page(client) -> str:
    response = client.get("/")
    assert response.status_code == 200
    match = re.search(
        r'<meta name="csrf-token" content="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match is not None
    return match.group(1)


def test_remote_bind_requires_login_credentials():
    with pytest.raises(RuntimeError, match="尚未配置登录密码"):
        validate_web_access("0.0.0.0", "", "")
    validate_web_access("127.0.0.1", "", "")
    validate_web_access("::1", "", "")
    validate_web_access("0.0.0.0", "password", "")


def test_secret_key_is_generated_once_and_persisted_privately(tmp_path):
    first = resolve_web_secret_key(tmp_path, environ={})
    second = resolve_web_secret_key(tmp_path, environ={})

    assert first == second
    assert len(first.encode("utf-8")) >= 32
    secret_file = tmp_path / "web_secret_key"
    assert secret_file.read_text(encoding="utf-8") == first
    if os.name != "nt":
        assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600


def test_explicit_secret_takes_precedence_and_short_secret_is_rejected(tmp_path):
    explicit = "x" * 48
    assert resolve_web_secret_key(tmp_path, explicit, environ={}) == explicit
    assert (
        resolve_web_secret_key(
            tmp_path, "y" * 48, environ={"TRADINGVIEW_ZY_WEB_SECRET_KEY": explicit}
        )
        == explicit
    )
    with pytest.raises(RuntimeError, match="at least 32"):
        resolve_web_secret_key(tmp_path, "short", environ={})


def test_password_hash_and_legacy_plain_password_are_supported():
    password_hash = generate_password_hash("correct horse battery staple")
    assert verify_login_password(
        "correct horse battery staple", "", password_hash
    )
    assert not verify_login_password("wrong", "", password_hash)
    assert verify_login_password("legacy", "legacy", "")
    assert not verify_login_password("wrong", "legacy", "")


def test_environment_login_credentials_override_config(monkeypatch):
    settings = SimpleNamespace(LOGIN_PWD="config", LOGIN_PWD_HASH="config-hash")
    monkeypatch.setenv("TRADINGVIEW_ZY_LOGIN_PASSWORD", "env")
    monkeypatch.setenv("TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH", "env-hash")
    assert resolve_login_credentials(settings) == ("env", "env-hash")


def test_login_attempt_limiter_blocks_and_resets():
    limiter = LoginAttemptLimiter(max_attempts=2, window_seconds=10)
    assert limiter.is_allowed("client", now=0)
    limiter.record_failure("client", now=1)
    assert limiter.is_allowed("client", now=2)
    limiter.record_failure("client", now=3)
    assert not limiter.is_allowed("client", now=4)
    assert limiter.is_allowed("client", now=20)
    limiter.record_failure("client", now=21)
    limiter.reset("client")
    assert limiter.is_allowed("client", now=22)


def test_create_app_applies_login_and_cookie_security(monkeypatch):
    cl_app = _import_cl_app_or_skip()

    fake_exchange = SimpleNamespace(
        support_frequencys=lambda: {"d": "日线"},
        default_code=lambda: "SH.000001",
    )
    monkeypatch.setattr(cl_app, "get_exchange", lambda market: fake_exchange)

    password_hash = generate_password_hash("correct-password")
    app = cl_app.create_app(
        {
            "TESTING": True,
            "WEB_HOST": "0.0.0.0",
            "LOGIN_PWD_HASH": password_hash,
            "WEB_SECRET_KEY": "z" * 48,
            "SECRET_KEY": "unsafe-generic-override",
            "SESSION_COOKIE_HTTPONLY": False,
            "WEB_COOKIE_SECURE": False,
            "WEB_MAX_LOGIN_ATTEMPTS": 5,
        }
    )

    assert app.secret_key == "z" * 48
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["REMEMBER_COOKIE_HTTPONLY"] is True

    client = app.test_client()
    redirect_response = client.get("/")
    assert redirect_response.status_code == 302
    assert "/login" in redirect_response.headers["Location"]

    csrf_token = _csrf_from_login_page(client)
    login_response = client.post(
        "/login",
        data={"password": "correct-password", "_csrf_token": csrf_token},
    )
    assert login_response.status_code == 302
    cookies = "\n".join(login_response.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookies
    assert "SameSite=Lax" in cookies


def test_create_app_rate_limits_failed_logins(monkeypatch):
    cl_app = _import_cl_app_or_skip()

    fake_exchange = SimpleNamespace(
        support_frequencys=lambda: {"d": "日线"},
        default_code=lambda: "SH.000001",
    )
    monkeypatch.setattr(cl_app, "get_exchange", lambda market: fake_exchange)

    app = cl_app.create_app(
        {
            "TESTING": True,
            "WEB_HOST": "0.0.0.0",
            "LOGIN_PWD": "correct-password",
            "WEB_SECRET_KEY": "r" * 48,
            "WEB_MAX_LOGIN_ATTEMPTS": 2,
            "WEB_LOGIN_ATTEMPT_WINDOW_SECONDS": 300,
        }
    )
    client = app.test_client()
    csrf_token = _csrf_from_login_page(client)
    payload = {"password": "wrong", "_csrf_token": csrf_token}
    assert client.post("/login", data=payload).status_code == 200
    assert client.post("/login", data=payload).status_code == 200
    assert client.post("/login", data=payload).status_code == 429


def test_local_loopback_without_password_keeps_auto_login(monkeypatch):
    cl_app = _import_cl_app_or_skip()

    fake_exchange = SimpleNamespace(
        support_frequencys=lambda: {"d": "日线"},
        default_code=lambda: "SH.000001",
    )
    monkeypatch.setattr(cl_app, "get_exchange", lambda market: fake_exchange)

    app = cl_app.create_app(
        {
            "TESTING": True,
            "WEB_HOST": "127.0.0.1",
            "LOGIN_PWD": "",
            "LOGIN_PWD_HASH": "",
            "WEB_SECRET_KEY": "l" * 48,
        }
    )
    client = app.test_client()
    login_response = client.get("/login")
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/")

    home_response = client.get("/")
    assert home_response.status_code == 200


def test_existing_secret_file_permissions_are_repaired(tmp_path):
    secret_file = tmp_path / "web_secret_key"
    secret_file.write_text("p" * 48, encoding="utf-8")
    if os.name != "nt":
        secret_file.chmod(0o644)

    assert resolve_web_secret_key(tmp_path, environ={}) == "p" * 48
    if os.name != "nt":
        assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600


def test_sources_do_not_use_fixed_flask_secret_and_demo_binds_loopback():
    app_source = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "__init__.py"
    ).read_text(encoding="utf-8")
    config_source = (
        ROOT / "src" / "tradingview_zy" / "config.py.demo"
    ).read_text(encoding="utf-8")

    assert "cl_pro_secret_key" not in app_source
    assert "WEB_HOST = '127.0.0.1'" in config_source
    assert "LOGIN_PWD_HASH = ''" in config_source
