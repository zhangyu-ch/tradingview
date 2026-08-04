from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "src/tradingview_zy/backtesting/base.py"
CODE_ROOTS = [ROOT / "src", ROOT / "script", ROOT / "web"]


def _python_trees():
    for root in CODE_ROOTS:
        for path in root.rglob("*.py"):
            yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _load_base_module():
    spec = importlib.util.spec_from_file_location("nx09_backtesting_base", BASE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unimplemented_fee_us_function_is_removed_from_runtime_code() -> None:
    definitions: list[str] = []
    references: list[str] = []
    for path, tree in _python_trees():
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "fee_us":
                definitions.append(str(path.relative_to(ROOT)))
            if isinstance(node, ast.Name) and node.id == "fee_us":
                references.append(str(path.relative_to(ROOT)))

    assert definitions == []
    assert references == []


def test_public_base_module_no_longer_advertises_fee_us() -> None:
    module = _load_base_module()
    assert not hasattr(module, "fee_us")


def test_existing_a_share_fee_calculation_is_unchanged() -> None:
    module = _load_base_module()
    assert module.fee_a("buy", 100.0, 100.0) == pytest.approx(32.0)
    assert module.fee_a("sell", 100.0, 100.0) == pytest.approx(42.0)
