from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# The offline verification image does not include Werkzeug. The CSRF helper only
# needs the sibling password-check symbol to import, so provide a deliberately
# inert test stub rather than weakening production code.
try:
    import werkzeug.security  # noqa: F401
except ModuleNotFoundError:
    import hashlib
    import hmac

    werkzeug = types.ModuleType("werkzeug")
    security = types.ModuleType("werkzeug.security")

    def _generate_password_hash(candidate: str) -> str:
        return "test-sha256$" + hashlib.sha256(candidate.encode("utf-8")).hexdigest()

    def _check_password_hash(stored: str, candidate: str) -> bool:
        return hmac.compare_digest(stored, _generate_password_hash(candidate))

    security.check_password_hash = _check_password_hash
    security.generate_password_hash = _generate_password_hash
    werkzeug.security = security
    sys.modules["werkzeug"] = werkzeug
    sys.modules["werkzeug.security"] = security

from tradingview_zy.web_security import (  # noqa: E402
    CSRF_FORM_FIELD,
    CSRF_HEADER,
    get_csrf_token,
    rotate_csrf_token,
    validate_csrf_request,
)


def _request(
    method: str = "POST",
    *,
    token: str | None = None,
    form_token: str | None = None,
    origin: str | None = None,
    referer: str | None = None,
    host_url: str = "https://app.example/",
) -> SimpleNamespace:
    headers: dict[str, str] = {}
    form: dict[str, str] = {}
    if token is not None:
        headers[CSRF_HEADER] = token
    if form_token is not None:
        form[CSRF_FORM_FIELD] = form_token
    if origin is not None:
        headers["Origin"] = origin
    if referer is not None:
        headers["Referer"] = referer
    return SimpleNamespace(
        method=method,
        headers=headers,
        form=form,
        host_url=host_url,
    )


def test_safe_methods_do_not_require_a_token() -> None:
    session: dict[str, str] = {}
    for method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        assert validate_csrf_request(_request(method), session) == (
            True,
            "safe_method",
        )


def test_unsafe_methods_require_the_session_bound_token() -> None:
    session: dict[str, str] = {}
    token = get_csrf_token(session)

    assert validate_csrf_request(_request(), session) == (False, "invalid_token")
    assert validate_csrf_request(_request(token="wrong"), session) == (
        False,
        "invalid_token",
    )
    assert validate_csrf_request(_request(token=token), session) == (True, "ok")
    assert validate_csrf_request(_request(form_token=token), session) == (True, "ok")


def test_origin_and_referer_are_rejected_when_cross_site() -> None:
    session: dict[str, str] = {}
    token = get_csrf_token(session)

    assert validate_csrf_request(
        _request(token=token, origin="https://evil.example"), session
    ) == (False, "cross_origin")
    assert validate_csrf_request(
        _request(token=token, referer="https://evil.example/page"), session
    ) == (False, "cross_origin")
    assert validate_csrf_request(
        _request(token=token, origin="https://app.example"), session
    ) == (True, "ok")
    assert validate_csrf_request(
        _request(token=token, referer="https://app.example/settings"), session
    ) == (True, "ok")


def test_explicit_trusted_origin_is_supported_without_trusting_every_origin() -> None:
    session: dict[str, str] = {}
    token = get_csrf_token(session)
    request = _request(token=token, origin="https://admin.example")

    assert validate_csrf_request(
        request, session, trusted_origins=("https://admin.example",)
    ) == (True, "ok")
    assert validate_csrf_request(
        request, session, trusted_origins=("https://another.example",)
    ) == (False, "cross_origin")


def test_rotating_token_invalidates_the_previous_value() -> None:
    session: dict[str, str] = {}
    old = get_csrf_token(session)
    new = rotate_csrf_token(session)

    assert new != old
    assert validate_csrf_request(_request(token=old), session) == (
        False,
        "invalid_token",
    )
    assert validate_csrf_request(_request(token=new), session) == (True, "ok")


def test_web_routes_and_browser_clients_enforce_the_csrf_contract() -> None:
    app_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
    ).read_text(encoding="utf-8")
    alert_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/static/js/alert.js"
    ).read_text(encoding="utf-8")
    csrf_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/static/js/csrf.js"
    ).read_text(encoding="utf-8")
    dark_template = (
        ROOT / "web/tradingview_zy_chart/cl_app/templates/dark.html"
    ).read_text(encoding="utf-8")
    login_template = (
        ROOT / "web/tradingview_zy_chart/cl_app/templates/login.html"
    ).read_text(encoding="utf-8")

    assert "@app.before_request" in app_source
    assert "validate_csrf_request(" in app_source
    assert '@app.route("/alert_del/<id>", methods=["POST"])' in app_source
    assert '@app.route("/alert_del/<id>", methods=["GET"])' not in app_source
    assert 'type: "POST"' in alert_source
    assert '<meta name="csrf-token"' in dark_template
    assert "js/csrf.js" in dark_template
    assert 'name="_csrf_token"' in login_template

    # Cover every browser request mechanism used by this legacy front-end.
    assert "ajaxPrefilter" in csrf_source
    assert "window.fetch" in csrf_source
    assert "XMLHttpRequest.prototype.send" in csrf_source
    assert 'input[name="_csrf_token"]' in csrf_source
    assert "X-CSRF-Token" in csrf_source
