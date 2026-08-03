from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
UTILS = ROOT / "src/tradingview_zy/utils.py"


class FakeDB:
    def __init__(self, value=None):
        self.value = value

    def cache_get(self, key: str):
        assert key == "fs_keys"
        return self.value


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


def _config():
    return SimpleNamespace(
        FEISHU_KEYS={
            "default": {"app_id": "default-id", "app_secret": "default-secret"},
            "a": {"app_id": "a-id", "app_secret": "a-secret"},
            "user_id": "user-1",
        }
    )


def test_market_specific_result_is_a_copy() -> None:
    config = _config()
    before = deepcopy(config.FEISHU_KEYS)
    fn = _function()
    fn.__globals__.update(db=FakeDB(), config=config)

    result = fn("a")
    result["app_id"] = "changed"
    result["user_id"] = "changed-user"

    assert config.FEISHU_KEYS == before
    assert fn("a") == {"app_id": "a-id", "app_secret": "a-secret", "user_id": "user-1"}


def test_default_result_is_a_copy_and_calls_do_not_leak_between_markets() -> None:
    config = _config()
    before = deepcopy(config.FEISHU_KEYS)
    fn = _function()
    fn.__globals__.update(db=FakeDB(), config=config)

    unknown = fn("unknown")
    market = fn("a")

    assert unknown == {
        "app_id": "default-id",
        "app_secret": "default-secret",
        "user_id": "user-1",
    }
    assert market["app_id"] == "a-id"
    assert unknown is not config.FEISHU_KEYS["default"]
    assert market is not config.FEISHU_KEYS["a"]
    assert config.FEISHU_KEYS == before


def test_database_override_remains_detached_from_cache_input() -> None:
    cached = {
        "fs_app_id": "db-id",
        "fs_app_secret": "db-secret",
        "fs_user_id": "db-user",
    }
    fn = _function()
    fn.__globals__.update(db=FakeDB(cached), config=_config())

    result = fn("a")
    result["app_id"] = "changed"

    assert cached["fs_app_id"] == "db-id"
    assert result["app_secret"] == "db-secret"
