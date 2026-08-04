from __future__ import annotations

import importlib.util
import os
import stat
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "script/remediation"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from check_secret_references import validate as validate_reference_contract  # noqa: E402
from tradingview_zy.secret_store import (  # noqa: E402
    CONFIG_SECRET_POLICIES,
    MANAGED_SECRET_POLICIES,
    ManagedSecretStore,
    RotationMode,
    SecretClass,
    SecretPermissionError,
    SecretReferenceError,
    redact_secrets,
    resolve_config_secret,
    resolve_secret,
)
from tradingview_zy.settings_security import (  # noqa: E402
    merge_feishu_settings,
    migrate_feishu_settings,
    retire_superseded_feishu_secret,
)


def test_environment_reference_resolves_and_plaintext_is_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("ME27_SECRET", "correct-horse-battery-staple")
    assert resolve_secret("env://ME27_SECRET", required=True) == "correct-horse-battery-staple"
    with pytest.raises(SecretReferenceError, match="plaintext"):
        resolve_secret("raw-secret")
    assert resolve_secret("raw-secret", allow_legacy_plaintext=True) == "raw-secret"
    with pytest.raises(SecretReferenceError, match="placeholder"):
        resolve_secret("******", allow_legacy_plaintext=True)
    with pytest.raises(SecretReferenceError, match="required"):
        resolve_secret("env://MISSING_ME27", environ={}, required=True)


def test_managed_store_rotation_is_atomic_private_versioned_and_retires_old(tmp_path) -> None:
    store = ManagedSecretStore(tmp_path)
    first = store.rotate("broker/binance", "first-secret")
    second = store.rotate("broker/binance", "second-secret")
    assert first != second
    assert store.read(first) == "first-secret"
    assert store.read(second) == "second-secret"
    if os.name != "nt":
        assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
        first_path = store._relative_path(first.removeprefix("managed://"))
        assert stat.S_IMODE(first_path.stat().st_mode) == 0o600
    assert store.retire(first) is True
    assert store.exists(first) is False
    assert store.read(second) == "second-secret"


def test_file_reference_requires_absolute_private_file(tmp_path) -> None:
    secret_file = tmp_path / "credential"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    if os.name != "nt":
        secret_file.chmod(0o644)
        with pytest.raises(SecretPermissionError):
            resolve_secret(secret_file.as_uri(), required=True)
        secret_file.chmod(0o600)
    assert resolve_secret(secret_file.as_uri(), required=True) == "file-secret"
    with pytest.raises(SecretReferenceError, match="absolute|remote host"):
        resolve_secret("file://relative/path")


def test_keyring_reference_uses_explicit_getter_without_importing_backend() -> None:
    calls = []

    def getter(service: str, account: str):
        calls.append((service, account))
        return "keyring-secret"

    assert resolve_secret("keyring://tradingview/binance", keyring_getter=getter) == "keyring-secret"
    assert calls == [("tradingview", "binance")]


def test_config_resolver_requires_explicit_legacy_switch(monkeypatch) -> None:
    settings = SimpleNamespace(API="plaintext", SECRET_ALLOW_LEGACY_PLAINTEXT=False)
    with pytest.raises(SecretReferenceError, match="plaintext"):
        resolve_config_secret(settings, "API")
    settings.SECRET_ALLOW_LEGACY_PLAINTEXT = True
    assert resolve_config_secret(settings, "API") == "plaintext"
    settings.API = "env://ME27_CONFIG"
    monkeypatch.setenv("ME27_CONFIG", "resolved")
    settings.SECRET_ALLOW_LEGACY_PLAINTEXT = False
    assert resolve_config_secret(settings, "API", required=True) == "resolved"


def test_feishu_cache_migrates_and_rotation_never_returns_plaintext(tmp_path) -> None:
    store = ManagedSecretStore(tmp_path)
    migrated, changed = migrate_feishu_settings(
        {
            "fs_app_id": "app-id",
            "fs_app_secret": "legacy-secret",
            "fs_user_id": "user-id",
        },
        store=store,
    )
    assert changed is True
    assert "fs_app_secret" not in migrated
    assert store.read(migrated["fs_app_secret_ref"]) == "legacy-secret"

    preserved, old = merge_feishu_settings(
        migrated,
        app_id="app-id-2",
        app_secret="",
        user_id="user-id-2",
        store=store,
    )
    assert preserved["fs_app_secret_ref"] == migrated["fs_app_secret_ref"]
    assert old is None

    rotated, old = merge_feishu_settings(
        migrated,
        app_id="app-id-2",
        app_secret="new-secret",
        user_id="user-id-2",
        store=store,
    )
    assert old == migrated["fs_app_secret_ref"]
    assert store.read(rotated["fs_app_secret_ref"]) == "new-secret"
    assert "new-secret" not in repr(rotated)
    retire_superseded_feishu_secret(store, old)
    assert store.exists(old) is False


def test_central_redactor_removes_registered_and_structured_credentials(monkeypatch) -> None:
    monkeypatch.setenv("ME27_LOG_SECRET", "registered-secret-value")
    resolve_secret("env://ME27_LOG_SECRET", required=True)
    text = redact_secrets(
        "Authorization: Bearer abc.def password=hunter2 "
        "https://user:pass@example.invalid/path registered-secret-value"
    )
    assert "abc.def" not in text
    assert "hunter2" not in text
    assert "user:pass" not in text
    assert "registered-secret-value" not in text
    assert text.count("[REDACTED]") >= 4


def test_config_template_and_consumers_are_reference_only() -> None:
    assert validate_reference_contract(ROOT) == []
    source = (ROOT / "src/tradingview_zy/config.py.demo").read_text(encoding="utf-8")
    assert "DB_PWD = 'env://" in source
    assert "IB_ACCOUNT = 'DU" not in source
    assert "TlQXy9Y7" not in source


def test_hygiene_workflow_enforces_secret_reference_contract() -> None:
    workflow = (ROOT / ".github/workflows/repository-hygiene.yml").read_text(
        encoding="utf-8"
    )
    assert "python script/remediation/check_secret_references.py" in workflow


def test_secret_inventory_declares_classification_and_rotation_owner() -> None:
    assert CONFIG_SECRET_POLICIES["DB_PWD"].classification is SecretClass.DATABASE
    assert CONFIG_SECRET_POLICIES["BINANCE_SECRET"].classification is SecretClass.BROKER
    assert CONFIG_SECRET_POLICIES["AI_TOKEN"].classification is SecretClass.AI
    assert all(
        policy.rotation is RotationMode.EXTERNAL
        for policy in CONFIG_SECRET_POLICIES.values()
    )
    feishu = MANAGED_SECRET_POLICIES["feishu.web.app_secret"]
    assert feishu.classification is SecretClass.MESSAGING
    assert feishu.rotation is RotationMode.MANAGED_VERSIONED


def test_database_check_redacts_and_fails_cleanly_when_driver_import_fails(monkeypatch) -> None:
    module_path = ROOT / "check_env.py"
    spec = importlib.util.spec_from_file_location("me27_check_env", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    real_import = module.importlib.import_module

    def fake_import(name: str):
        if name == "pymysql":
            raise ModuleNotFoundError("pymysql driver missing token=should-not-leak")
        return real_import(name)

    monkeypatch.setattr(module.importlib, "import_module", fake_import)
    config = SimpleNamespace(DB_TYPE="mysql")
    result = module._check_database(config)
    assert result.status is module.CheckStatus.FAILED
    assert "UnboundLocalError" not in result.message
    assert "should-not-leak" not in result.message
    assert "[REDACTED]" in result.message
