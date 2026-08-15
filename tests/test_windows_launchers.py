from __future__ import annotations

import os
import shutil
import subprocess
import venv
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHERS = ("windows_install.bat", "windows_run.bat")


def _prepare_launcher_root(tmp_path: Path, launcher_name: str) -> Path:
    launcher = tmp_path / launcher_name
    shutil.copyfile(ROOT / launcher_name, launcher)

    if launcher_name == "windows_run.bat":
        app = tmp_path / "web" / "tradingview_zy_chart" / "app.py"
        app.parent.mkdir(parents=True)
        app.write_text("# launcher test stub\n", encoding="utf-8")
    else:
        package = tmp_path / "src" / "tradingview_zy"
        package.mkdir(parents=True)
        (package / "config.py.demo").write_text("# config stub\n", encoding="utf-8")
        (tmp_path / "check_env.py").write_text("# check stub\n", encoding="utf-8")

        venv.EnvBuilder(with_pip=False).create(tmp_path / ".venv")

    return launcher


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher contract")
@pytest.mark.parametrize("launcher_name", LAUNCHERS)
def test_launcher_accepts_exact_uv_version_with_build_metadata(
    tmp_path: Path, launcher_name: str
) -> None:
    launcher = _prepare_launcher_root(tmp_path, launcher_name)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "uv.cmd").write_text(
        """@echo off
if "%~1"=="--version" goto version
>>"%FAKE_UV_LOG%" echo %*
exit /b 0
:version
echo uv 0.10.0 ^(0ba432459 2026-02-05^)
exit /b 0
""",
        encoding="ascii",
    )

    log_path = tmp_path / "uv-invocations.log"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env["FAKE_UV_LOG"] = str(log_path)
    env["TRADINGVIEW_ZY_NO_PAUSE"] = "1"
    completed = subprocess.run(
        [env.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
        check=False,
    )

    output = completed.stdout.decode("utf-8", errors="replace")
    assert completed.returncode == 0, output
    invocations = log_path.read_text(encoding="utf-8").splitlines()
    assert invocations
    if launcher_name == "windows_install.bat":
        assert not any(line.startswith("venv ") for line in invocations)
        assert "sync --locked" in invocations
        assert any(line.startswith("run python ") for line in invocations)
    else:
        assert any(line.startswith("run python ") for line in invocations)


@pytest.mark.parametrize("launcher_name", LAUNCHERS)
def test_launcher_errors_can_pause_for_double_click_users(launcher_name: str) -> None:
    source = (ROOT / launcher_name).read_text(encoding="utf-8").lower()

    assert "tradingview_zy_no_pause" in source
    assert "pause" in source
