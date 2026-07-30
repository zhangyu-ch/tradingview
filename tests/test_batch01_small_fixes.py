from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _compile_function(path: Path, function_name: str, namespace: dict):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    function = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    )
    module = ast.Module(body=[function], type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function_name]


def _load_check_env_module():
    path = ROOT / "check_env.py"
    spec = importlib.util.spec_from_file_location("batch01_check_env", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mx08_bkgn_click_uses_layui_table_namespace():
    source = (
        ROOT / "web/tradingview_zy_chart/cl_app/static/js/bkgn.js"
    ).read_text(encoding="utf-8")

    assert source.count('layui.table.setRowChecked("bkgn_table"') == 2
    assert "\n      table.setRowChecked(" not in source


def test_mx03_invalid_ny_futures_provider_has_descriptive_error():
    from tradingview_zy.base import Market

    namespace = {
        "config": SimpleNamespace(EXCHANGE_NY_FUTURES="invalid-provider"),
        "Market": Market,
        "Exchange": object,
        "g_exchange_obj": {},
        "CTP_UNAVAILABLE_MESSAGE": "unused",
    }
    get_exchange = _compile_function(
        ROOT / "src/tradingview_zy/exchange/__init__.py",
        "get_exchange",
        namespace,
    )

    with pytest.raises(Exception, match="不支持的纽约期货交易所 invalid-provider"):
        get_exchange(Market.NY_FUTURES)
    assert namespace["g_exchange_obj"] == {}


def test_me24_python_support_matches_pyproject_lower_bound():
    module = _load_check_env_module()

    assert module._python_version_supported((3, 10, 99)) is False
    assert module._python_version_supported((3, 11, 0)) is True
    assert module._python_version_supported((3, 12, 0)) is True
    assert module._python_version_supported((3, 13, 0)) is True


def test_me24_required_failure_returns_nonzero_exit(monkeypatch, capsys):
    module = _load_check_env_module()
    fake_config = SimpleNamespace(
        PROXY_HOST="",
        REDIS_HOST="",
        DB_TYPE="mysql",
    )
    monkeypatch.setattr(module, "_python_version_supported", lambda: True)
    monkeypatch.setattr(module, "_load_project_config", lambda: fake_config)
    monkeypatch.setattr(module, "_check_proxy", lambda config: True)
    monkeypatch.setattr(module, "_check_redis", lambda config: True)
    monkeypatch.setattr(module, "_check_mysql", lambda config: False)

    assert module.main() == 1
    output = capsys.readouterr().out
    assert "环境检查失败" in output
    assert "环境OK" not in output


def test_me24_optional_failure_is_degraded_not_false_ok(monkeypatch, capsys):
    module = _load_check_env_module()
    fake_config = SimpleNamespace(
        PROXY_HOST="proxy.local",
        REDIS_HOST="",
        DB_TYPE="sqlite",
    )
    monkeypatch.setattr(module, "_python_version_supported", lambda: True)
    monkeypatch.setattr(module, "_load_project_config", lambda: fake_config)
    calls = []
    monkeypatch.setattr(module, "_check_proxy", lambda config: calls.append("proxy") or False)
    monkeypatch.setattr(module, "_check_redis", lambda config: calls.append("redis") or True)
    monkeypatch.setattr(module, "_check_mysql", lambda config: calls.append("mysql") or True)

    assert module.main() == 0
    assert calls == ["proxy", "redis", "mysql"]
    output = capsys.readouterr().out
    assert "环境可运行，但存在不可用的可选服务" in output
    assert "环境OK" not in output


def test_mx14_removed_monitor_stub_is_absent():
    assert not (ROOT / "src/tradingview_zy/monitor.py").exists()
