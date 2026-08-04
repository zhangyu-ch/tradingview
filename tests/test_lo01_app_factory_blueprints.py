from __future__ import annotations

import ast
import importlib.util
import sys
import types
from dataclasses import fields
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web/tradingview_zy_chart/cl_app"
FACTORY = WEB_ROOT / "__init__.py"
SERVICES = WEB_ROOT / "web_services.py"
BLUEPRINT_ROOT = WEB_ROOT / "blueprints"

EXPECTED_ROUTES = {
    "auth.py": {"login_opt", "logout_opt"},
    "pages.py": {"index_show"},
    "udf.py": {
        "tv_config",
        "tv_symbol_info",
        "tv_symbols",
        "tv_search",
        "tv_history",
        "tv_footprint",
        "tv_timescale_marks",
        "tv_marks",
        "tv_del_marks",
        "tv_time",
        "ticks",
    },
    "storage.py": {"tv_charts", "tv_study_templates", "tv_drawings"},
    "watchlist.py": {
        "get_zixuan_groups",
        "get_zixuan_stocks",
        "get_stock_zixuan",
        "zixuan_group_view",
        "opt_zixuan_group",
        "opt_zixuan_export",
        "opt_zixuan_import",
        "set_stock_zixuan",
    },
    "tasks.py": {
        "alert_list",
        "alert_edit",
        "alert_save",
        "alert_del",
        "alert_records",
        "jobs",
        "xuangu_task_list",
        "xuangu_task_add",
    },
    "settings.py": {"setting", "setting_save", "a_bkgn_list", "a_bkgn_codes"},
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _decorator_calls(function: ast.FunctionDef) -> list[ast.Call]:
    return [decorator for decorator in function.decorator_list if isinstance(decorator, ast.Call)]


def _route_functions(path: Path) -> dict[str, ast.FunctionDef]:
    result: dict[str, ast.FunctionDef] = {}
    for node in _tree(path).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if any(
            isinstance(call.func, ast.Attribute) and call.func.attr == "route"
            for call in _decorator_calls(node)
        ):
            result[node.name] = node
    return result


def test_factory_only_composes_services_and_blueprints() -> None:
    source = FACTORY.read_text(encoding="utf-8")
    tree = _tree(FACTORY)
    create_app = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "create_app"
    )

    assert create_app.end_lineno - create_app.lineno + 1 <= 400
    assert len(source.splitlines()) <= 450
    nested_functions = {
        node.name for node in create_app.body if isinstance(node, ast.FunctionDef)
    }
    assert nested_functions == set()
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"route", "before_request", "errorhandler", "context_processor"}
        for node in ast.walk(create_app)
    )
    assert source.count("WebAppServices.create(") == 1
    assert source.count("install_web_services(app, services)") == 1
    assert source.count("register_blueprints(app)") == 1
    assert "render_template" not in source
    assert "jsonify" not in source


def test_all_public_routes_are_owned_by_feature_blueprints() -> None:
    discovered: set[str] = set()
    for filename, expected in EXPECTED_ROUTES.items():
        path = BLUEPRINT_ROOT / filename
        functions = _route_functions(path)
        assert set(functions) == expected, filename
        discovered.update(functions)
    assert len(discovered) == 37

    core = _tree(BLUEPRINT_ROOT / "core.py")
    core_hooks = {
        node.name
        for node in core.body
        if isinstance(node, ast.FunctionDef) and node.decorator_list
    }
    assert core_hooks == {
        "request_too_large",
        "inject_csrf_token",
        "protect_unsafe_requests",
    }


def test_blueprints_consume_app_services_instead_of_constructing_runtime_dependencies() -> None:
    forbidden_modules = {
        "tradingview_zy.db",
        "tradingview_zy.config",
        "tradingview_zy.fun",
        "tradingview_zy.zixuan",
    }
    for path in sorted(BLUEPRINT_ROOT.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = _tree(path)
        imported_modules: set[str] = set()
        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
        assert not (imported_modules & forbidden_modules), path.name
        assert "get_exchange" not in imported_names, path.name
        assert "ZiXuan" not in imported_names, path.name
        assert "StocksBKGN" not in imported_names, path.name

        route_functions = _route_functions(path)
        for name, function in route_functions.items():
            if name in {"tv_time", "logout_opt"}:
                continue
            calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
            assert any(
                isinstance(call.func, ast.Name) and call.func.id == "get_web_services"
                for call in calls
            ), f"{path.name}:{name} bypasses the app service container"


def _load_services_module(monkeypatch):
    flask = types.ModuleType("flask")
    flask.current_app = SimpleNamespace(extensions={})
    monkeypatch.setitem(sys.modules, "flask", flask)
    module_name = "test_lo01_web_services"
    spec = importlib.util.spec_from_file_location(module_name, SERVICES)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _service_values(service_type) -> dict:
    mappings = {
        "frequency_maps": {"d": "1D"},
        "resolution_maps": {"1D": "d"},
        "market_frequencies": {"a": ["d"]},
        "market_default_codes": {"a": "SH.000001"},
        "security_overrides": {"TESTING": True},
    }
    values = {field.name: object() for field in fields(service_type)}
    values.update(
        web_host="127.0.0.1",
        login_password="",
        login_password_hash="",
        remember_days=30,
        auto_login=True,
        csrf_trusted_origins=(),
        storage_principal="principal",
        max_upload_bytes=1024,
        max_watchlist_lines=10,
        max_watchlist_line_bytes=128,
        frequency_maps=mappings["frequency_maps"],
        resolution_maps=mappings["resolution_maps"],
        market_frequencies=mappings["market_frequencies"],
        market_default_codes=mappings["market_default_codes"],
        market_catalog=[{"value": "a", "label": "A股"}],
        default_market="a",
        security_overrides=mappings["security_overrides"],
        get_exchange=lambda market: market,
        zixuan_factory=lambda market: market,
        stocks_bkgn_factory=lambda market: market,
        secret_store_factory=lambda root: root,
        get_data_path=lambda: ROOT,
    )
    return values


def test_service_container_is_per_app_and_deeply_freezes_shared_metadata(monkeypatch) -> None:
    module = _load_services_module(monkeypatch)
    first_input = _service_values(module.WebAppServices)
    second_input = _service_values(module.WebAppServices)
    first = module.WebAppServices.create(**first_input)
    second = module.WebAppServices.create(**second_input)

    assert first is not second
    assert isinstance(first.frequency_maps, MappingProxyType)
    assert isinstance(first.market_frequencies, MappingProxyType)
    assert first.market_frequencies["a"] == ("d",)
    assert isinstance(first.market_catalog[0], MappingProxyType)
    with pytest.raises(TypeError):
        first.frequency_maps["w"] = "1W"
    with pytest.raises(TypeError):
        first.market_catalog[0]["label"] = "changed"

    first_input["frequency_maps"]["w"] = "1W"
    first_input["market_frequencies"]["a"].append("w")
    first_input["market_catalog"][0]["label"] = "changed"
    assert dict(first.frequency_maps) == {"d": "1D"}
    assert first.market_frequencies["a"] == ("d",)
    assert first.market_catalog[0]["label"] == "A股"
    assert dict(second.frequency_maps) == {"d": "1D"}


def test_installation_is_explicit_and_rejects_duplicate_service_publication(monkeypatch) -> None:
    module = _load_services_module(monkeypatch)
    services = module.WebAppServices.create(**_service_values(module.WebAppServices))
    app = SimpleNamespace(extensions={})
    module.install_web_services(app, services)
    assert app.extensions[module.WEB_SERVICES_EXTENSION] is services
    with pytest.raises(RuntimeError, match="already installed"):
        module.install_web_services(app, services)
