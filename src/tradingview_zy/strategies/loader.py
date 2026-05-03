from __future__ import annotations

from importlib import import_module
from typing import Any


def load_strategy(dotted_path: str, **kwargs: Any) -> Any:
    if ":" not in dotted_path:
        raise ValueError("strategy path must use 'module:ClassName' format")
    module_name, class_name = dotted_path.split(":", 1)
    if module_name == "" or class_name == "":
        raise ValueError("strategy path must include module and class name")
    module = import_module(module_name)
    strategy_class = getattr(module, class_name)
    strategy = strategy_class(**kwargs)
    if not callable(getattr(strategy, "run", None)):
        raise TypeError("strategy object must define run(context)")
    return strategy
