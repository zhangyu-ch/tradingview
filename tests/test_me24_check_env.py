from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

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


def test_real_script_reports_current_python_against_project_contract() -> None:
    module = _load_check_env()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "check_env.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    supported = module._python_version_supported(tuple(sys.version_info[:3]))
    expected_message = "does not satisfy project requires-python >=3.11,<3.12"

    assert completed.returncode == (0 if supported else 1)
    if supported:
        assert expected_message not in completed.stdout
    else:
        assert expected_message in completed.stdout
        assert "环境OK" not in completed.stdout


def test_check_env_does_not_import_removed_telnetlib() -> None:
    source = (ROOT / "check_env.py").read_text(encoding="utf-8")
    assert "telnetlib" not in source
    assert "socket.create_connection" in source
    assert "raise SystemExit(check_env())" in source
