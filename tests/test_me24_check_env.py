from __future__ import annotations

import builtins
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_check_env():
    spec = importlib.util.spec_from_file_location("project_check_env", ROOT / "check_env.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_python_contract_comes_from_pyproject_and_honours_both_bounds() -> None:
    module = _load_check_env()
    assert module.project_python_spec() == ">=3.11,<3.12"
    assert module._python_version_supported((3, 11, 0)) is True
    assert module._python_version_supported((3, 11, 99)) is True
    assert module._python_version_supported((3, 10, 99)) is False
    assert module._python_version_supported((3, 12, 0)) is False
    assert module._python_version_supported((3, 13, 0)) is False


def test_failed_check_returns_nonzero_and_never_prints_environment_ok(monkeypatch, capsys) -> None:
    module = _load_check_env()
    monkeypatch.setattr(
        module,
        "run_checks",
        lambda: [module.CheckResult("python", module.CheckStatus.FAILED, "bad")],
    )
    assert module.check_env() == 1
    output = capsys.readouterr().out
    assert "FAILED" in output
    assert "环境OK" not in output


def test_degraded_optional_service_is_distinct_from_failed_required_service(monkeypatch, capsys) -> None:
    module = _load_check_env()
    monkeypatch.setattr(
        module,
        "run_checks",
        lambda: [
            module.CheckResult("python", module.CheckStatus.OK, "ok"),
            module.CheckResult("redis", module.CheckStatus.DEGRADED, "optional down"),
        ],
    )
    assert module.check_env() == 0
    output = capsys.readouterr().out
    assert "DEGRADED" in output
    assert "环境检查结果：DEGRADED" in output


@pytest.mark.parametrize(
    ("python_spec", "config", "expected_code", "expected_status", "detail"),
    [
        (">=0", "DB_TYPE = 'sqlite'\n", 0, "OK", "SQLite/local database mode"),
        (">=0", "raise RuntimeError('invalid test configuration')\n", 1, "FAILED", "invalid test configuration"),
        (">=0", "DB_TYPE = 'sqlite'\nREDIS_HOST = 'test.invalid'\n", 0, "DEGRADED", "optional test service unavailable"),
        ("<0", "raise AssertionError('configuration must not be imported')\n", 1, "FAILED", "does not satisfy project requires-python <0"),
    ],
)
def test_cli_reports_required_failures_and_optional_degradation_in_isolation(
    tmp_path, python_spec, config, expected_code, expected_status, detail
) -> None:
    shutil.copyfile(ROOT / "check_env.py", tmp_path / "check_env.py")
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nrequires-python = "{python_spec}"\n', encoding="utf-8"
    )
    package = tmp_path / "src" / "tradingview_zy"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "base.py").write_text("", encoding="utf-8")
    (package / "config.py").write_text(config, encoding="utf-8")
    (package.parent / "redis.py").write_text(
        "raise OSError('optional test service unavailable')\n", encoding="utf-8"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-X", "utf8", str(tmp_path / "check_env.py")],
        cwd=tmp_path,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == expected_code, completed.stdout + completed.stderr
    assert detail in completed.stdout
    assert f"环境检查结果：{expected_status}" in completed.stdout
    assert "configuration must not be imported" not in completed.stdout + completed.stderr


@pytest.mark.parametrize("reachable", [True, False])
def test_proxy_check_works_without_telnetlib_and_closes_its_socket(monkeypatch, reachable) -> None:
    real_import = builtins.__import__

    def without_telnetlib(name, *args, **kwargs):
        if name == "telnetlib":
            raise ModuleNotFoundError("telnetlib was removed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_telnetlib)
    module = _load_check_env()
    calls = []
    # A real, unconnected socket supports both context-manager and explicit close
    # implementations without making a network request.
    connection = module.socket.socket()

    def connect(address, timeout):
        calls.append((address, timeout))
        if not reachable:
            raise OSError("test proxy refused connection")
        return connection

    monkeypatch.setattr(module.socket, "create_connection", connect)
    try:
        result = module._check_proxy(SimpleNamespace(PROXY_HOST="proxy.invalid", PROXY_PORT=8123))
        assert result.status is (module.CheckStatus.OK if reachable else module.CheckStatus.DEGRADED)
        assert "proxy.invalid:8123" in result.message
        assert len(calls) == 1
        address, timeout = calls[0]
        assert address == ("proxy.invalid", 8123)
        assert 0 < timeout < float("inf")
        assert (connection.fileno() == -1) is reachable
        assert ("is reachable" if reachable else "test proxy refused connection") in result.message
    finally:
        connection.close()
