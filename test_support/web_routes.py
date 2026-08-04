"""Locate and isolate feature blueprint route functions for contract tests."""
from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_ROOT = ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "blueprints"

SERVICE_ATTRIBUTE_NAMES = {
    "auto_login": "auto_login",
    "csrf_trusted_origins": "csrf_trusted_origins",
    "login_limiter": "login_limiter",
    "login_password": "login_password",
    "login_password_hash": "login_password_hash",
    "remember_days": "remember_days",
    "default_market": "default_market_key",
    "market_catalog": "market_catalog_items",
    "market_default_codes": "market_default_codes",
    "market_frequencies": "market_frequencys",
    "frequency_maps": "frequency_maps",
    "resolution_maps": "resolution_maps",
    "history_request_tracker": "history_request_tracker",
    "footprint_cache": "__footprint_cache",
    "logger": "__log",
    "tick_provider_caller": "tick_provider_caller",
    "tick_rate_limiter": "tick_rate_limiter",
    "security_overrides": "security_overrides",
    "max_upload_bytes": "max_upload_bytes",
    "max_watchlist_lines": "max_watchlist_lines",
    "max_watchlist_line_bytes": "max_watchlist_line_bytes",
    "alert_tasks": "_alert_tasks",
    "xuangu_tasks": "_xuangu_tasks",
    "scheduler_status_store": "scheduler_status_store",
    "storage_principal": "storage_principal",
    "database": "db",
    "get_exchange": "get_exchange",
    "config": "config",
    "fun": "fun",
    "zixuan_factory": "ZiXuan",
    "stocks_bkgn_factory": "StocksBKGN",
    "secret_store_factory": "ManagedSecretStore",
    "get_data_path": "get_data_path",
    "web_host": "web_host",
}


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


class _LegacyServiceNames(ast.NodeTransformer):
    def visit_Assign(self, node: ast.Assign):
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "services"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "get_web_services"
        ):
            return None
        return self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "services":
            replacement = SERVICE_ATTRIBUTE_NAMES.get(node.attr, f"service_{node.attr}")
            return ast.copy_location(ast.Name(id=replacement, ctx=node.ctx), node)
        return node


def compile_route(name: str, namespace: dict[str, Any]):
    node = route_node(name)
    node.decorator_list = []
    node = _LegacyServiceNames().visit(node)
    assert isinstance(node, ast.FunctionDef)
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    path, _ = route_location(name)
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[name]
