import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tradingview_zy.strategies.loader import (
    StrategyRegistryError,
    find_registered_strategy_id_by_path,
    load_registered_strategy,
    load_strategy,
    validate_registered_strategy,
)


def _install_temp_module(tmp_path: Path, name: str, source: str):
    module_path = tmp_path / f"{name}.py"
    module_path.write_text(source, encoding="utf-8")
    sys.modules.pop(name, None)
    sys.path.insert(0, str(tmp_path))
    return module_path


def _remove_temp_module(tmp_path: Path, name: str):
    sys.path.remove(str(tmp_path))
    sys.modules.pop(name, None)


def test_load_strategy_from_trusted_dotted_path(tmp_path):
    name = "temporary_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "class LocalStrategy:\n"
        "    name = 'local_strategy'\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    try:
        strategy = load_strategy(f"{name}:LocalStrategy")
    finally:
        _remove_temp_module(tmp_path, name)

    assert strategy.name == "local_strategy"


def test_load_strategy_rejects_non_class_before_calling_it(tmp_path):
    marker = tmp_path / "factory_called"
    name = "callable_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "from pathlib import Path\n"
        f"MARKER = Path({str(marker)!r})\n"
        "def factory():\n"
        "    MARKER.write_text('called')\n"
        "    return object()\n",
    )
    try:
        with pytest.raises(TypeError, match="must be a class"):
            load_strategy(f"{name}:factory")
    finally:
        _remove_temp_module(tmp_path, name)

    assert not marker.exists()


def test_load_strategy_rejects_class_without_run_before_constructor(tmp_path):
    marker = tmp_path / "constructor_called"
    name = "constructor_side_effect_module"
    _install_temp_module(
        tmp_path,
        name,
        "from pathlib import Path\n"
        f"MARKER = Path({str(marker)!r})\n"
        "class UnsafeObject:\n"
        "    def __init__(self):\n"
        "        MARKER.write_text('called')\n",
    )
    try:
        with pytest.raises(TypeError, match="run"):
            load_strategy(f"{name}:UnsafeObject")
    finally:
        _remove_temp_module(tmp_path, name)

    assert not marker.exists()


def test_registered_loader_rejects_unknown_id_without_importing_request_path():
    registry = {
        "safe": {
            "strategy_path": "tests.fake_strategy:SafeStrategy",
            "strategy_kwargs": {},
        }
    }
    with pytest.raises(StrategyRegistryError, match="not registered"):
        load_registered_strategy(registry, "os:system")


def test_registered_loader_validates_kwargs_allowlist_and_schema(tmp_path):
    name = "registered_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "class RegisteredStrategy:\n"
        "    def __init__(self, window=20, threshold=0.5):\n"
        "        self.window = window\n"
        "        self.threshold = threshold\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    registry = {
        "registered": {
            "name": "Registered",
            "strategy_path": f"{name}:RegisteredStrategy",
            "strategy_kwargs": {"window": 20, "threshold": 0.5},
            "allowed_kwargs": ["window", "threshold"],
            "strategy_kwargs_schema": {
                "window": "int",
                "threshold": "number",
            },
        }
    }
    try:
        strategy = load_registered_strategy(
            registry, "registered", {"window": 30, "threshold": 1}
        )
        assert strategy.window == 30
        assert strategy.threshold == 1

        with pytest.raises(StrategyRegistryError, match="does not allow"):
            validate_registered_strategy(registry, "registered", {"command": "id"})

        with pytest.raises(StrategyRegistryError, match="must match"):
            validate_registered_strategy(registry, "registered", {"window": "30"})
    finally:
        _remove_temp_module(tmp_path, name)


def test_legacy_path_only_resolves_when_exactly_registered():
    registry = {
        "safe": {"strategy_path": "my_package.safe:Strategy"},
    }
    assert (
        find_registered_strategy_id_by_path(
            registry, "my_package.safe:Strategy"
        )
        == "safe"
    )
    assert find_registered_strategy_id_by_path(registry, "os:system") is None


def test_registered_validation_checks_constructor_signature_without_instantiating(tmp_path):
    marker = tmp_path / "constructor_called"
    name = "signature_validation_module"
    _install_temp_module(
        tmp_path,
        name,
        "from pathlib import Path\n"
        f"MARKER = Path({str(marker)!r})\n"
        "class SignatureStrategy:\n"
        "    def __init__(self, window):\n"
        "        MARKER.write_text('called')\n"
        "        self.window = window\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    registry = {
        "signature": {
            "strategy_path": f"{name}:SignatureStrategy",
            "strategy_kwargs": {"window": 20},
            "allowed_kwargs": ["window", "extra"],
        }
    }
    try:
        validate_registered_strategy(registry, "signature", {"window": 30})
        assert not marker.exists()

        with pytest.raises(StrategyRegistryError, match="constructor does not accept"):
            validate_registered_strategy(registry, "signature", {"window": 30, "extra": 1})
    finally:
        _remove_temp_module(tmp_path, name)


def test_registered_kwargs_overrides_are_opt_in(tmp_path):
    name = "opt_in_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "class Strategy:\n"
        "    def __init__(self, path='safe'):\n"
        "        self.path = path\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    registry = {
        "safe": {
            "strategy_path": f"{name}:Strategy",
            "strategy_kwargs": {"path": "safe"},
        }
    }
    try:
        strategy = load_registered_strategy(registry, "safe")
        assert strategy.path == "safe"
        with pytest.raises(StrategyRegistryError, match="does not allow"):
            validate_registered_strategy(registry, "safe", {"path": "/tmp/other"})
    finally:
        _remove_temp_module(tmp_path, name)


def test_none_default_only_accepts_null_without_explicit_schema(tmp_path):
    name = "none_default_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "class Strategy:\n"
        "    def __init__(self, value=None):\n"
        "        self.value = value\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    registry = {
        "safe": {
            "strategy_path": f"{name}:Strategy",
            "strategy_kwargs": {"value": None},
            "allowed_kwargs": ["value"],
        }
    }
    try:
        validate_registered_strategy(registry, "safe", {"value": None})
        with pytest.raises(StrategyRegistryError, match="must match"):
            validate_registered_strategy(registry, "safe", {"value": "anything"})
    finally:
        _remove_temp_module(tmp_path, name)


def test_rich_server_default_is_not_user_overridable_without_explicit_allowlist(tmp_path):
    name = "rich_default_strategy_module"
    _install_temp_module(
        tmp_path,
        name,
        "class RichDefaultStrategy:\n"
        "    def __init__(self, callback=None):\n"
        "        self.callback = callback\n"
        "    def run(self, context):\n"
        "        return []\n",
    )
    registry = {
        "rich": {
            "strategy_path": f"{name}:RichDefaultStrategy",
            "strategy_kwargs": {"callback": object()},
        }
    }
    try:
        with pytest.raises(StrategyRegistryError, match="does not allow"):
            validate_registered_strategy(registry, "rich", {"callback": "user-value"})

        strategy = load_registered_strategy(registry, "rich")
        assert not isinstance(strategy.callback, str)
    finally:
        _remove_temp_module(tmp_path, name)


def test_web_runtime_never_calls_direct_dotted_path_loader():
    web_root = ROOT / "web" / "tradingview_zy_chart" / "cl_app"
    offenders = []
    for path in web_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "load_strategy(" in source:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
