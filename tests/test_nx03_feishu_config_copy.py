from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from tradingview_zy.secret_store import ManagedSecretStore, resolve_secret
from tradingview_zy.settings_security import migrate_feishu_settings

ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "src/tradingview_zy/utils.py"


class FakeDB:
    def __init__(self, value=None):
        self.value = value
        self.saved = None

    def cache_get(self, key: str):
        assert key == "fs_keys"
        return self.value

    def cache_set(self, key: str, value):
        assert key == "fs_keys"
        self.saved = dict(value)
        self.value = dict(value)
        return True


def _function():
    tree = ast.parse(UTILS.read_text(encoding="utf-8"), filename=str(UTILS))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == "config_get_feishu_keys"
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace: dict[str, object] = {}
    exec(compile(module, str(UTILS), "exec"), namespace)
    return namespace["config_get_feishu_keys"]


def _config(tmp_path: Path):
    return SimpleNamespace(
        SECRET_ALLOW_LEGACY_PLAINTEXT=False,
        get_data_path=lambda: tmp_path,
        FEISHU_KEYS={
            "default": {
                "app_id": "env://FS_DEFAULT_ID",
                "app_secret": "env://FS_DEFAULT_SECRET",
            },
            "a": {
                "app_id": "env://FS_A_ID",
                "app_secret": "env://FS_A_SECRET",
            },
            "user_id": "env://FS_USER",
        },
    )


def _bind(fn, *, db, config):
    fn.__globals__.update(
        db=db,
        config=config,
        ManagedSecretStore=ManagedSecretStore,
        migrate_feishu_settings=migrate_feishu_settings,
        resolve_secret=resolve_secret,
    )


def test_market_specific_result_is_a_copy(tmp_path, monkeypatch) -> None:
    config = _config(tmp_path)
    before = deepcopy(config.FEISHU_KEYS)
    monkeypatch.setenv("FS_A_ID", "a-id")
    monkeypatch.setenv("FS_A_SECRET", "a-secret")
    monkeypatch.setenv("FS_USER", "user-1")
    fn = _function()
    _bind(fn, db=FakeDB(), config=config)

    result = fn("a")
    result["app_id"] = "changed"
    result["user_id"] = "changed-user"

    assert config.FEISHU_KEYS == before
    assert fn("a") == {"app_id": "a-id", "app_secret": "a-secret", "user_id": "user-1"}


def test_default_result_is_a_copy_and_calls_do_not_leak_between_markets(
    tmp_path, monkeypatch
) -> None:
    config = _config(tmp_path)
    before = deepcopy(config.FEISHU_KEYS)
    monkeypatch.setenv("FS_DEFAULT_ID", "default-id")
    monkeypatch.setenv("FS_DEFAULT_SECRET", "default-secret")
    monkeypatch.setenv("FS_A_ID", "a-id")
    monkeypatch.setenv("FS_A_SECRET", "a-secret")
    monkeypatch.setenv("FS_USER", "user-1")
    fn = _function()
    _bind(fn, db=FakeDB(), config=config)

    unknown = fn("unknown")
    market = fn("a")

    assert unknown == {
        "app_id": "default-id",
        "app_secret": "default-secret",
        "user_id": "user-1",
    }
    assert market["app_id"] == "a-id"
    assert config.FEISHU_KEYS == before


def test_database_override_migrates_plaintext_and_detaches_result(tmp_path) -> None:
    cached = {
        "fs_app_id": "db-id",
        "fs_app_secret": "db-secret",
        "fs_user_id": "db-user",
    }
    fake_db = FakeDB(cached)
    fn = _function()
    _bind(fn, db=fake_db, config=_config(tmp_path))

    result = fn("a")
    result["app_id"] = "changed"

    assert cached["fs_app_secret"] == "db-secret"
    assert fake_db.saved is not None
    assert "fs_app_secret" not in fake_db.saved
    assert fake_db.saved["fs_app_secret_ref"].startswith("managed://")
    assert result["app_secret"] == "db-secret"
