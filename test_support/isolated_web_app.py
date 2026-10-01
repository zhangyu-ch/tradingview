"""Run real Flask app contracts without importing local config or sharing a DB."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_web_app_script(tmp_path: Path, script: str, **parameters) -> None:
    bootstrap = """
import json
import sys
import types
from pathlib import Path

root = Path.cwd()
data_path = Path(sys.argv[1])
parameters = json.loads(sys.argv[2])
source = root / "src/tradingview_zy/config.py.demo"
config = types.ModuleType("tradingview_zy.config")
exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), config.__dict__)
config.DATA_PATH = str(data_path)
config.DB_TYPE = "sqlite"
config.DB_DATABASE = "udf_contract"
sys.modules[config.__name__] = config
assert config.get_data_path().resolve() == data_path.resolve()

import cl_app
assert cl_app.config is config
app_config = {
    "TESTING": True,
    "LOGIN_DISABLED": True,
    "WEB_HOST": "127.0.0.1",
    "LOGIN_PWD": "",
    "LOGIN_PWD_HASH": "",
    "WEB_SECRET_KEY": "isolated-udf-contract-session-key",
}
"""
    env = dict(os.environ)
    for name in (
        "TRADINGVIEW_ZY_LOGIN_PASSWORD",
        "TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH",
        "TRADINGVIEW_ZY_WEB_SECRET_KEY",
    ):
        env.pop(name, None)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(ROOT / "web/tradingview_zy_chart")]
    )
    completed = subprocess.run(
        [
            sys.executable, "-B", "-c", bootstrap + textwrap.dedent(script),
            str(tmp_path), json.dumps(parameters),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
