"""Secret references, managed rotation, permission checks, and central redaction.

Configuration stores references rather than credential values. Supported forms:

* ``env://NAME`` - read from one environment variable.
* ``managed://namespace/version.secret`` - read from the private DATA_PATH store.
* ``file:///absolute/path`` - read a private operator-managed file.
* ``keyring://service/account`` - optional system keyring integration.

Raw values are rejected unless the explicit legacy migration switch is enabled.
"""
from __future__ import annotations

import os
import re
import secrets
import stat
import tempfile
import threading
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

MAX_SECRET_BYTES = 64 * 1024
_REFERENCE_SCHEMES = frozenset({"env", "managed", "file", "keyring"})
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SAFE_PART_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_PLACEHOLDER_RE = re.compile(r"^(?:\*{3,}|x{3,}|change[-_ ]?me|your[-_ ].*|<.*>)$", re.IGNORECASE)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|pwd|secret|token)"
)
_KEY_VALUE_RE = re.compile(
    r"(?i)(\b(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|pwd|secret|token)\b\s*[:=]\s*)([\"']?)([^\s,;\"']+)(\2)"
)
_BEARER_RE = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+")
_URL_CREDENTIAL_RE = re.compile(r"(?i)([a-z][a-z0-9+.-]*://)([^/@\s]+)@")


class SecretError(RuntimeError):
    """Base error with a stable message that never contains credential data."""


class SecretReferenceError(SecretError):
    """Raised when a secret reference is missing, malformed, or unavailable."""


class SecretPermissionError(SecretError):
    """Raised when a secret file is readable by group or other users."""


class SecretClass(StrEnum):
    """Operational sensitivity domain used for inventory and rotation ownership."""

    DATABASE = "database"
    MARKET_DATA = "market-data"
    BROKER = "broker-trading"
    MESSAGING = "messaging"
    AI = "ai"


class RotationMode(StrEnum):
    """Where a credential version is changed and old material is revoked."""

    EXTERNAL = "external-provider"
    MANAGED_VERSIONED = "managed-versioned"


@dataclass(frozen=True, slots=True)
class SecretPolicy:
    classification: SecretClass
    rotation: RotationMode


CONFIG_SECRET_POLICIES: Mapping[str, SecretPolicy] = MappingProxyType(
    {
        "DB_PWD": SecretPolicy(SecretClass.DATABASE, RotationMode.EXTERNAL),
        "GM_TOKEN": SecretPolicy(SecretClass.MARKET_DATA, RotationMode.EXTERNAL),
        "FUTU_UNLOCK_PWD": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "TQ_USER": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "TQ_PWD": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "TQ_SP_ACCOUNT": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "TQ_SP_PWD": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "BINANCE_APIKEY": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "BINANCE_SECRET": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "POLYGON_APIKEY": SecretPolicy(SecretClass.MARKET_DATA, RotationMode.EXTERNAL),
        "ALPACA_APIKEY": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "ALPACA_SECRET": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "IB_ACCOUNT": SecretPolicy(SecretClass.BROKER, RotationMode.EXTERNAL),
        "AI_TOKEN": SecretPolicy(SecretClass.AI, RotationMode.EXTERNAL),
        "OPENROUTER_AI_KEYS": SecretPolicy(SecretClass.AI, RotationMode.EXTERNAL),
    }
)
MANAGED_SECRET_POLICIES: Mapping[str, SecretPolicy] = MappingProxyType(
    {
        "feishu.web.app_secret": SecretPolicy(
            SecretClass.MESSAGING, RotationMode.MANAGED_VERSIONED
        )
    }
)


def secret_policy_for_attribute(attribute: str) -> SecretPolicy:
    try:
        return CONFIG_SECRET_POLICIES[attribute]
    except KeyError as error:
        raise SecretReferenceError("configuration field has no declared secret policy") from error


@dataclass(frozen=True, slots=True)
class SecretReference:
    scheme: str
    locator: str

    @classmethod
    def parse(cls, value: object) -> "SecretReference":
        if not isinstance(value, str):
            raise SecretReferenceError("secret reference must be a string")
        raw = value.strip()
        if not raw:
            raise SecretReferenceError("secret reference is empty")
        parsed = urllib.parse.urlsplit(raw)
        scheme = parsed.scheme.lower()
        if scheme not in _REFERENCE_SCHEMES:
            raise SecretReferenceError("secret must use env://, managed://, file://, or keyring://")
        if parsed.query or parsed.fragment:
            raise SecretReferenceError("secret reference must not contain query or fragment")
        if scheme == "env":
            locator = parsed.netloc or parsed.path.lstrip("/")
        elif scheme in {"managed", "keyring"}:
            locator = "/".join(part for part in (parsed.netloc, parsed.path.lstrip("/")) if part)
        else:
            locator = urllib.parse.unquote(parsed.path)
            if locator.replace("\\", "/").startswith("//"):
                raise SecretReferenceError("file secret reference must not contain a remote host")
            if os.name == "nt" and re.match(r"^/[A-Za-z]:/", locator):
                locator = locator[1:]
            if parsed.netloc and parsed.netloc not in {"", "localhost"}:
                raise SecretReferenceError("file secret reference must not contain a remote host")
        if not locator:
            raise SecretReferenceError("secret reference locator is empty")
        return cls(scheme=scheme, locator=locator)

    def __str__(self) -> str:
        return f"{self.scheme}://{self.locator}"


_known_secrets: set[str] = set()
_known_secrets_lock = threading.RLock()


def _validate_secret_value(value: object, *, allow_placeholder: bool = False) -> str:
    if not isinstance(value, str):
        raise SecretReferenceError("resolved secret must be a string")
    if "\x00" in value:
        raise SecretReferenceError("resolved secret contains a NUL byte")
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_SECRET_BYTES:
        raise SecretReferenceError("resolved secret exceeds 64 KiB")
    if value and not allow_placeholder and _PLACEHOLDER_RE.fullmatch(value.strip()):
        raise SecretReferenceError("resolved secret is an example placeholder")
    return value


def register_secret(value: str) -> None:
    value = _validate_secret_value(value, allow_placeholder=True)
    if len(value) < 3:
        return
    with _known_secrets_lock:
        _known_secrets.add(value)


def registered_secret_count() -> int:
    with _known_secrets_lock:
        return len(_known_secrets)


def redact_secrets(value: object, extra: tuple[str, ...] | list[str] = ()) -> str:
    """Redact registered values and common credential-bearing text shapes."""

    text = str(value).replace("\r", " ").replace("\n", " ")
    candidates = set(str(item) for item in extra if item)
    with _known_secrets_lock:
        candidates.update(_known_secrets)
    for candidate in sorted(candidates, key=len, reverse=True):
        if len(candidate) >= 3:
            text = text.replace(candidate, "[REDACTED]")
    text = _BEARER_RE.sub(lambda match: f"{match.group(1)} [REDACTED]", text)
    text = _KEY_VALUE_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]{match.group(4)}", text)
    text = _URL_CREDENTIAL_RE.sub(lambda match: f"{match.group(1)}[REDACTED]@", text)
    return text[:1000]


def _assert_private_file(path: Path) -> None:
    if not path.is_file():
        raise SecretReferenceError("secret file does not exist")
    if os.name != "nt":
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise SecretPermissionError("secret file must not be readable by group or other users")


def _file_reference_path(locator: str) -> Path:
    path = Path(locator).expanduser()
    if not path.is_absolute():
        raise SecretReferenceError("file secret reference must use an absolute path")
    return path.resolve()


def _read_private_file(path: Path) -> str:
    _assert_private_file(path)
    if path.stat().st_size > MAX_SECRET_BYTES:
        raise SecretReferenceError("secret file exceeds 64 KiB")
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SecretReferenceError("secret file could not be read") from error
    value = value.rstrip("\r\n")
    value = _validate_secret_value(value)
    register_secret(value)
    return value


class ManagedSecretStore:
    """Versioned private files under ``DATA_PATH/secrets`` with atomic rotation."""

    def __init__(self, data_path: Path | str, *, directory_name: str = "secrets") -> None:
        self.data_path = Path(data_path).expanduser().resolve()
        self.root = (self.data_path / directory_name).resolve()
        self._lock = threading.RLock()
        self._ensure_private_directory(self.root)

    @staticmethod
    def _ensure_private_directory(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            path.chmod(0o700)

    def _relative_path(self, locator: str) -> Path:
        decoded = urllib.parse.unquote(locator)
        parts = [part for part in decoded.split("/") if part]
        if not parts or any(part in {".", ".."} or not _SAFE_PART_RE.fullmatch(part) for part in parts):
            raise SecretReferenceError("managed secret locator contains unsafe path components")
        path = self.root.joinpath(*parts).resolve()
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise SecretReferenceError("managed secret escapes the private store") from error
        return path

    def rotate(self, name: str, value: str) -> str:
        value = _validate_secret_value(value)
        if not value:
            raise SecretReferenceError("cannot store an empty secret")
        namespace = self._relative_path(name)
        with self._lock:
            self._ensure_private_directory(namespace)
            version = (
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                + "-"
                + secrets.token_hex(8)
                + ".secret"
            )
            destination = namespace / version
            descriptor, temporary = tempfile.mkstemp(prefix=".rotate-", dir=namespace)
            try:
                if os.name != "nt":
                    os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
                    handle.write(value)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, destination)
                if os.name != "nt":
                    destination.chmod(0o600)
                try:
                    directory_fd = os.open(namespace, os.O_RDONLY)
                except OSError:
                    directory_fd = None
                if directory_fd is not None:
                    try:
                        os.fsync(directory_fd)
                    finally:
                        os.close(directory_fd)
            finally:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass
        register_secret(value)
        relative = destination.relative_to(self.root).as_posix()
        return f"managed://{urllib.parse.quote(relative, safe='/._-')}"

    def read(self, reference: str | SecretReference) -> str:
        parsed = reference if isinstance(reference, SecretReference) else SecretReference.parse(reference)
        if parsed.scheme != "managed":
            raise SecretReferenceError("reference does not use managed://")
        return _read_private_file(self._relative_path(parsed.locator))

    def exists(self, reference: str | SecretReference) -> bool:
        try:
            parsed = reference if isinstance(reference, SecretReference) else SecretReference.parse(reference)
            if parsed.scheme != "managed":
                return False
            path = self._relative_path(parsed.locator)
            _assert_private_file(path)
        except SecretError:
            return False
        return True

    def retire(self, reference: str | SecretReference) -> bool:
        parsed = reference if isinstance(reference, SecretReference) else SecretReference.parse(reference)
        if parsed.scheme != "managed":
            return False
        path = self._relative_path(parsed.locator)
        with self._lock:
            try:
                path.unlink()
            except FileNotFoundError:
                return False
        return True


def _resolve_keyring(locator: str, getter: Callable[[str, str], str | None] | None) -> str:
    service, separator, account = locator.partition("/")
    if not separator or not service or not account:
        raise SecretReferenceError("keyring reference must be keyring://service/account")
    if getter is None:
        try:
            import keyring  # type: ignore[import-not-found]
        except (ImportError, ModuleNotFoundError) as error:
            raise SecretReferenceError("system keyring support is not installed") from error
        getter = keyring.get_password
    try:
        value = getter(service, account)
    except Exception as error:  # noqa: BLE001 - public error must be stable and secret-free
        raise SecretReferenceError("system keyring lookup failed") from error
    if value is None:
        raise SecretReferenceError("system keyring entry is missing")
    return value


def resolve_secret(
    reference: object,
    *,
    data_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
    required: bool = False,
    allow_legacy_plaintext: bool = False,
    keyring_getter: Callable[[str, str], str | None] | None = None,
) -> str:
    """Resolve one configured reference without exposing it in an error message."""

    raw = "" if reference is None else str(reference).strip()
    if not raw:
        if required:
            raise SecretReferenceError("required secret reference is not configured")
        return ""
    parsed_url = urllib.parse.urlsplit(raw)
    if not parsed_url.scheme:
        if not allow_legacy_plaintext:
            raise SecretReferenceError("plaintext secret configuration is disabled")
        value = _validate_secret_value(raw)
        register_secret(value)
        return value

    parsed = SecretReference.parse(raw)
    env = os.environ if environ is None else environ
    if parsed.scheme == "env":
        if not _ENV_NAME_RE.fullmatch(parsed.locator):
            raise SecretReferenceError("environment secret reference has an invalid variable name")
        value = str(env.get(parsed.locator, ""))
    elif parsed.scheme == "managed":
        if data_path is None:
            raise SecretReferenceError("managed secret requires a data path")
        value = ManagedSecretStore(data_path).read(parsed)
    elif parsed.scheme == "file":
        value = _read_private_file(_file_reference_path(parsed.locator))
    else:
        value = _resolve_keyring(parsed.locator, keyring_getter)

    value = _validate_secret_value(value)
    if not value and required:
        raise SecretReferenceError("required secret is unavailable")
    if value:
        register_secret(value)
    return value


def resolve_config_secret(
    settings: Any,
    attribute: str,
    *,
    required: bool = False,
    data_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
    keyring_getter: Callable[[str, str], str | None] | None = None,
) -> str:
    reference = getattr(settings, attribute, "")
    if data_path is None and isinstance(reference, str) and reference.startswith("managed://"):
        get_data_path = getattr(settings, "get_data_path", None)
        if callable(get_data_path):
            data_path = get_data_path()
    return resolve_secret(
        reference,
        data_path=data_path,
        environ=environ,
        required=required,
        allow_legacy_plaintext=bool(
            getattr(settings, "SECRET_ALLOW_LEGACY_PLAINTEXT", False)
        ),
        keyring_getter=keyring_getter,
    )


def reference_is_configured(
    reference: object,
    *,
    data_path: Path | str | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    raw = "" if reference is None else str(reference).strip()
    if not raw:
        return False
    try:
        parsed = SecretReference.parse(raw)
    except SecretError:
        return False
    if parsed.scheme == "env":
        env = os.environ if environ is None else environ
        return bool(str(env.get(parsed.locator, "")))
    if parsed.scheme == "managed":
        return data_path is not None and ManagedSecretStore(data_path).exists(parsed)
    if parsed.scheme == "file":
        try:
            _assert_private_file(_file_reference_path(parsed.locator))
        except SecretError:
            return False
        return True
    return True


def contains_sensitive_key(value: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(value))
