from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_importing_db_preserves_caller_warning_policy(tmp_path: Path) -> None:
    code = r'''
import sys
import types
import warnings
from pathlib import Path

config = types.ModuleType("tradingview_zy.config")
config.DB_TYPE = "sqlite"
config.DB_DATABASE = "warnings"
config.get_data_path = lambda: Path(sys.argv[1])
sys.modules["tradingview_zy.config"] = config

warnings.resetwarnings()
warnings.simplefilter("error")
from tradingview_zy.db import db

try:
    assert Path(db.engine.url.database) == Path(sys.argv[1]) / "db/warnings.sqlite"
    for category in (UserWarning, DeprecationWarning, FutureWarning, RuntimeWarning, ResourceWarning):
        try:
            warnings.warn("caller-policy-sentinel", category)
        except category:
            pass
        else:
            raise AssertionError("database import suppressed " + category.__name__)
finally:
    db.engine.dispose()
'''
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout
