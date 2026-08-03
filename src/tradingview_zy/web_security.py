from __future__ import annotations

import hmac
import ipaddress
import os
import secrets
import stat
import threading
import time
from collections import defaultdict, deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from werkzeug.security import check_password_hash

SECRET_ENV = "TRADINGVIEW_ZY_WEB_SECRET_KEY"
PASSWORD_ENV = "TRADINGVIEW_ZY_LOGIN_PASSWORD"
PASSWORD_HASH_ENV = "TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH"

CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FORM_FIELD = "_csrf_token"
SAFE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def get_csrf_token(session_store: Any) -> str:
    """Return a stable, session-bound CSRF token without logging or exposing secrets."""
    token = session_store.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session_store[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token(session_store: Any) -> str:
    token = secrets.token_urlsafe(32)
    session_store[CSRF_SESSION_KEY] = token
    return token


def _normalized_origin(value: str | None) -> str | None:
    if not value or value == "null":
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def validate_csrf_request(
    request_obj: Any,
    session_store: Any,
    trusted_origins: tuple[str, ...] | list[str] | set[str] = (),
) -> tuple[bool, str]:
    """Validate token and same-origin evidence for every unsafe HTTP request."""
    method = str(getattr(request_obj, "method", "GET")).upper()
    if method in SAFE_HTTP_METHODS:
        return True, "safe_method"

    expected = get_csrf_token(session_store)
    headers = getattr(request_obj, "headers", {})
    submitted = headers.get(CSRF_HEADER, "")
    if not submitted:
        form = getattr(request_obj, "form", None)
        if form is not None:
            submitted = form.get(CSRF_FORM_FIELD, "")
    if not isinstance(submitted, str) or not hmac.compare_digest(expected, submitted):
        return False, "invalid_token"

    request_origin = _normalized_origin(getattr(request_obj, "host_url", ""))
    allowed = {request_origin} if request_origin else set()
    allowed.update(
        origin
        for origin in (_normalized_origin(value) for value in trusted_origins)
        if origin is not None
    )

    origin_header = headers.get("Origin")
    referer_header = headers.get("Referer")
    supplied_origin = None
    if origin_header is not None:
        supplied_origin = _normalized_origin(origin_header)
        if supplied_origin is None:
            return False, "invalid_origin"
    elif referer_header is not None:
        supplied_origin = _normalized_origin(referer_header)
        if supplied_origin is None:
            return False, "invalid_referer"

    # Non-browser clients may omit Origin/Referer but still must present the session token.
    if supplied_origin is not None and supplied_origin not in allowed:
        return False, "cross_origin"
    return True, "ok"


def is_loopback_host(host: str) -> bool:
    host = str(host or "").strip().lower()
    if host == "localhost":
        return True
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def resolve_login_credentials(
    settings: Any, overrides: Mapping[str, Any] | None = None
) -> tuple[str, str]:
    overrides = overrides or {}
    plain = os.environ.get(
        PASSWORD_ENV,
        str(overrides.get("LOGIN_PWD", getattr(settings, "LOGIN_PWD", "")) or ""),
    )
    password_hash = os.environ.get(
        PASSWORD_HASH_ENV,
        str(
            overrides.get(
                "LOGIN_PWD_HASH", getattr(settings, "LOGIN_PWD_HASH", "")
            )
            or ""
        ),
    )
    return plain, password_hash


def validate_web_access(host: str, plain_password: str, password_hash: str) -> None:
    if is_loopback_host(host):
        return
    if plain_password == "" and password_hash == "":
        raise RuntimeError(
            "WEB_HOST 不是本机回环地址，但尚未配置登录密码。"
            "请设置 LOGIN_PWD_HASH（推荐）或 LOGIN_PWD，或者把 WEB_HOST 改为 127.0.0.1。"
        )


def verify_login_password(candidate: str | None, plain_password: str, password_hash: str) -> bool:
    candidate = candidate or ""
    if password_hash:
        try:
            return check_password_hash(password_hash, candidate)
        except (ValueError, TypeError):
            return False
    if plain_password:
        return hmac.compare_digest(plain_password, candidate)
    return False


def _validate_secret(secret: str) -> str:
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise RuntimeError("WEB_SECRET_KEY must contain at least 32 bytes")
    return secret


def resolve_web_secret_key(
    data_path: Path,
    configured_secret: str = "",
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return a stable secret, generating a private data-file on first use when blank."""

    environ = os.environ if environ is None else environ
    env_secret = environ.get(SECRET_ENV, "")
    if env_secret:
        return _validate_secret(env_secret)
    if configured_secret:
        return _validate_secret(configured_secret)

    data_path = Path(data_path)
    data_path.mkdir(parents=True, exist_ok=True)
    secret_path = data_path / "web_secret_key"

    if secret_path.exists():
        existing = _validate_secret(secret_path.read_text(encoding="utf-8").strip())
        try:
            secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return existing

    secret = secrets.token_urlsafe(48)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(secret_path, flags, stat.S_IRUSR | stat.S_IWUSR)
    except FileExistsError:
        # Another process won the first-start race. Read the stable value it created.
        for _ in range(20):
            try:
                existing = secret_path.read_text(encoding="utf-8").strip()
                if existing:
                    return _validate_secret(existing)
            except OSError:
                pass
            time.sleep(0.05)
        raise RuntimeError(f"cannot read generated web secret at {secret_path}")

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(secret)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            # Windows ACLs do not map cleanly to POSIX chmod; the file is still private
            # to the configured DATA_PATH and no secret is logged.
            pass
    except Exception:
        try:
            secret_path.unlink()
        except OSError:
            pass
        raise
    return secret


class LoginAttemptLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        if max_attempts < 1 or window_seconds < 1:
            raise ValueError("login limiter values must be positive")
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        failures = self._failures[key]
        cutoff = now - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            self._failures.pop(key, None)
            return deque()
        return failures

    def is_allowed(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            return len(self._prune(key, now)) < self.max_attempts

    def record_failure(self, key: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            failures = self._prune(key, now)
            if key not in self._failures:
                self._failures[key] = failures
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
