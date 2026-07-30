from __future__ import annotations

import inspect
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from typing import Any


class StrategyRegistryError(ValueError):
    """Raised when a configured strategy registry entry is invalid or unavailable."""


@dataclass(frozen=True)
class RegisteredStrategy:
    strategy_id: str
    name: str
    strategy_path: str
    default_kwargs: dict[str, Any]
    allowed_kwargs: frozenset[str]
    kwargs_schema: dict[str, tuple[str, ...]]
    description: str = ""


_JSON_TYPES = {
    "any",
    "null",
    "bool",
    "int",
    "float",
    "number",
    "str",
    "list",
    "dict",
}


def _validate_dotted_path(dotted_path: str) -> tuple[str, str]:
    if not isinstance(dotted_path, str) or ":" not in dotted_path:
        raise ValueError("strategy path must use 'module:ClassName' format")
    module_name, class_name = dotted_path.split(":", 1)
    if module_name == "" or class_name == "":
        raise ValueError("strategy path must include module and class name")
    return module_name, class_name


def _load_strategy_class(dotted_path: str) -> type[Any]:
    """Load and validate a trusted, configured strategy class before constructing it."""

    module_name, class_name = _validate_dotted_path(dotted_path)
    module = import_module(module_name)
    strategy_class = getattr(module, class_name)

    # This check intentionally happens before construction. A function, callable object,
    # or class without run() must not get an opportunity to execute constructor effects.
    if not inspect.isclass(strategy_class):
        raise TypeError("strategy target must be a class")
    if not callable(getattr(strategy_class, "run", None)):
        raise TypeError("strategy class must define run(context)")
    return strategy_class


def load_strategy(dotted_path: str, **kwargs: Any) -> Any:
    """Load a strategy from a trusted server-side path.

    Request data must never be passed to this function. Web-facing code should use
    :func:`load_registered_strategy`, which resolves paths from a server-side registry.
    """

    strategy_class = _load_strategy_class(dotted_path)
    return strategy_class(**kwargs)


def _normalise_schema(schema: Any) -> dict[str, tuple[str, ...]]:
    if schema is None:
        return {}
    if not isinstance(schema, Mapping):
        raise StrategyRegistryError("strategy_kwargs_schema must be an object")

    normalised: dict[str, tuple[str, ...]] = {}
    for key, value in schema.items():
        if not isinstance(key, str) or key == "":
            raise StrategyRegistryError("strategy_kwargs_schema keys must be non-empty strings")
        if isinstance(value, str):
            types = (value,)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            types = tuple(value)
        else:
            raise StrategyRegistryError(
                f"strategy_kwargs_schema[{key!r}] must be a type name or list of type names"
            )
        if not types or any(
            not isinstance(item, str) or item not in _JSON_TYPES for item in types
        ):
            raise StrategyRegistryError(
                f"strategy_kwargs_schema[{key!r}] contains an unsupported JSON type"
            )
        normalised[key] = types
    return normalised


def get_registered_strategy(
    registry: Mapping[str, Any], strategy_id: str
) -> RegisteredStrategy:
    if not isinstance(registry, Mapping):
        raise StrategyRegistryError("strategy registry must be an object")
    if not isinstance(strategy_id, str) or strategy_id == "":
        raise StrategyRegistryError("strategy_id must be a non-empty string")
    if strategy_id not in registry:
        raise StrategyRegistryError(f"strategy {strategy_id!r} is not registered")

    raw = registry[strategy_id]
    if isinstance(raw, str):
        entry: Mapping[str, Any] = {"strategy_path": raw}
    elif isinstance(raw, Mapping):
        entry = raw
    else:
        raise StrategyRegistryError(f"strategy {strategy_id!r} registry entry must be an object")

    strategy_path = entry.get("strategy_path", "")
    _validate_dotted_path(strategy_path)

    default_kwargs = entry.get("strategy_kwargs", {})
    if not isinstance(default_kwargs, Mapping):
        raise StrategyRegistryError(
            f"strategy {strategy_id!r} strategy_kwargs must be an object"
        )
    default_kwargs = dict(default_kwargs)

    schema = _normalise_schema(entry.get("strategy_kwargs_schema"))

    raw_allowed = entry.get("allowed_kwargs")
    if raw_allowed is None:
        # Secure default: constructor defaults are server-owned. Request overrides are
        # disabled unless the operator explicitly lists a parameter or supplies a schema.
        allowed_kwargs = frozenset(schema)
    elif isinstance(raw_allowed, Sequence) and not isinstance(raw_allowed, (str, bytes)):
        if any(not isinstance(item, str) or item == "" for item in raw_allowed):
            raise StrategyRegistryError("allowed_kwargs must contain non-empty strings")
        allowed_kwargs = frozenset(raw_allowed)
    else:
        raise StrategyRegistryError("allowed_kwargs must be a list of parameter names")

    undeclared_schema = set(schema) - set(allowed_kwargs)
    if undeclared_schema:
        raise StrategyRegistryError(
            f"strategy {strategy_id!r} schema keys are not allowed: {sorted(undeclared_schema)}"
        )

    return RegisteredStrategy(
        strategy_id=strategy_id,
        name=str(entry.get("name") or strategy_id),
        strategy_path=strategy_path,
        default_kwargs=default_kwargs,
        allowed_kwargs=allowed_kwargs,
        kwargs_schema=schema,
        description=str(entry.get("description") or entry.get("task_memo") or ""),
    )


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "any":
        return True
    if expected == "null":
        return value is None
    if expected == "bool":
        return isinstance(value, bool)
    if expected == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "float":
        return isinstance(value, float)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "str":
        return isinstance(value, str)
    if expected == "list":
        return isinstance(value, list)
    if expected == "dict":
        return isinstance(value, dict)
    return False


def _inferred_json_types(value: Any) -> tuple[str, ...] | None:
    if value is None:
        # A None default does not imply that every JSON type is safe. Operators can
        # declare a broader union explicitly in strategy_kwargs_schema when needed.
        return ("null",)
    if isinstance(value, bool):
        return ("bool",)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return ("number",)
    if isinstance(value, str):
        return ("str",)
    if isinstance(value, list):
        return ("list",)
    if isinstance(value, dict):
        return ("dict",)
    # Trusted server-side defaults may be richer Python objects. They remain usable,
    # but cannot be meaningfully type-checked against JSON form overrides without an
    # explicit strategy_kwargs_schema entry.
    return None


def prepare_registered_strategy(
    registry: Mapping[str, Any],
    strategy_id: str,
    overrides: Mapping[str, Any] | None = None,
) -> tuple[RegisteredStrategy, dict[str, Any], type[Any]]:
    definition = get_registered_strategy(registry, strategy_id)
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, Mapping):
        raise StrategyRegistryError("strategy kwargs overrides must be an object")

    unknown = set(overrides) - set(definition.allowed_kwargs)
    if unknown:
        raise StrategyRegistryError(
            f"strategy {strategy_id!r} does not allow kwargs: {sorted(unknown)}"
        )

    merged = dict(definition.default_kwargs)
    merged.update(overrides)
    for key, value in merged.items():
        expected = definition.kwargs_schema.get(key)
        if expected is None and key in definition.default_kwargs:
            expected = _inferred_json_types(definition.default_kwargs[key])
        if expected is not None and not any(_json_type_matches(value, item) for item in expected):
            raise StrategyRegistryError(
                f"strategy {strategy_id!r} kwarg {key!r} must match {list(expected)}"
            )

    strategy_class = _load_strategy_class(definition.strategy_path)
    try:
        inspect.signature(strategy_class).bind(**merged)
    except (TypeError, ValueError) as error:
        raise StrategyRegistryError(
            f"strategy {strategy_id!r} constructor does not accept the configured kwargs: {error}"
        ) from error
    return definition, merged, strategy_class


def validate_registered_strategy(
    registry: Mapping[str, Any],
    strategy_id: str,
    overrides: Mapping[str, Any] | None = None,
) -> RegisteredStrategy:
    """Validate a registry entry and request overrides without running its constructor."""

    definition, _, _ = prepare_registered_strategy(registry, strategy_id, overrides)
    return definition


def load_registered_strategy(
    registry: Mapping[str, Any],
    strategy_id: str,
    overrides: Mapping[str, Any] | None = None,
) -> Any:
    definition, kwargs, strategy_class = prepare_registered_strategy(
        registry, strategy_id, overrides
    )
    try:
        return strategy_class(**kwargs)
    except TypeError as exc:
        raise StrategyRegistryError(
            f"strategy {definition.strategy_id!r} constructor rejected configured kwargs: {exc}"
        ) from exc


def find_registered_strategy_id_by_path(
    registry: Mapping[str, Any], dotted_path: str
) -> str | None:
    """Resolve a legacy stored path to a registered id without accepting new paths."""

    if not isinstance(registry, Mapping) or not isinstance(dotted_path, str):
        return None
    for strategy_id in registry:
        try:
            definition = get_registered_strategy(registry, str(strategy_id))
        except (StrategyRegistryError, ValueError):
            continue
        if definition.strategy_path == dotted_path:
            return definition.strategy_id
    return None


def registered_strategy_choices(registry: Mapping[str, Any]) -> list[RegisteredStrategy]:
    if not isinstance(registry, Mapping):
        return []
    return [get_registered_strategy(registry, str(strategy_id)) for strategy_id in registry]
