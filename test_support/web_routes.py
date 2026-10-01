"""Locate and isolate feature blueprint route functions for contract tests."""
from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_ROOT = ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "blueprints"


def blueprint_paths() -> tuple[Path, ...]:
    return tuple(sorted(path for path in BLUEPRINT_ROOT.glob("*.py") if path.name != "__init__.py"))


def route_location(name: str) -> tuple[Path, ast.FunctionDef]:
    for path in blueprint_paths():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return path, node
    raise LookupError(f"route function not found: {name}")


def route_node(name: str) -> ast.FunctionDef:
    return copy.deepcopy(route_location(name)[1])


def route_source(name: str) -> str:
    path, node = route_location(name)
    source = path.read_text(encoding="utf-8")
    return ast.get_source_segment(source, node) or ""


def compile_route(name: str, namespace: dict[str, Any]):
    """Compile the unchanged route body with explicit dependency injection."""
    node = route_node(name)
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    path, _ = route_location(name)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[name]
