"""Isolated SQLite database imports with deterministic cleanup for tests."""
from __future__ import annotations

import importlib
import sys
from contextlib import ExitStack, contextmanager
from types import ModuleType

import pytest


@contextmanager
def isolated_sqlite_db(data_path, **config_overrides):
    package = importlib.import_module("tradingview_zy")
    config = ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "test"
    config.get_data_path = lambda: data_path
    for name, value in config_overrides.items():
        setattr(config, name, value)

    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, "tradingview_zy.config", config)
        patch.setattr(package, "config", config, raising=False)
        for name in ("db", "fun"):
            # Record absent entries too: import mutates both module surfaces.
            qualified_name = f"tradingview_zy.{name}"
            patch.setitem(sys.modules, qualified_name, None)
            patch.delitem(sys.modules, qualified_name)
            patch.setattr(package, name, None, raising=False)
            patch.delattr(package, name)
        module = importlib.import_module("tradingview_zy.db")
        try:
            yield module
        finally:
            module.db.engine.dispose()


@pytest.fixture
def sqlite_db(tmp_path):
    with ExitStack() as databases:
        def load(data_path=None, **config_overrides):
            return databases.enter_context(
                isolated_sqlite_db(
                    tmp_path if data_path is None else data_path,
                    **config_overrides,
                )
            )

        yield load
