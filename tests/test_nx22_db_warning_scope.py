from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_SOURCE = ROOT / "src/tradingview_zy/db.py"


def test_db_module_has_no_process_wide_warning_suppression() -> None:
    source = DB_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(DB_SOURCE))

    assert not any(
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "filterwarnings"
        for node in tree.body
    )
    assert not any(
        isinstance(node, ast.Import)
        and any(alias.name == "warnings" for alias in node.names)
        for node in tree.body
    )


def test_importing_db_preserves_caller_warning_policy(tmp_path: Path) -> None:
    code = r'''
import sys
import types
import warnings

# The execution image lacks tzlocal. Stub only its pure timezone lookup so the
# actual tradingview_zy.db module and all database dependencies are still imported.
tzlocal = types.ModuleType("tzlocal")
tzlocal.get_localzone = lambda: "UTC"
sys.modules["tzlocal"] = tzlocal

warnings.resetwarnings()
warnings.simplefilter("error", UserWarning)
import tradingview_zy.db  # noqa: F401
try:
    warnings.warn("sentinel", UserWarning)
except UserWarning:
    pass
else:
    raise SystemExit("database import suppressed the caller's warning policy")
'''
    # The container intentionally lacks the optional tzlocal dependency.  A
    # tiny import-compatible stub keeps this test focused on warning policy
    # while the real db module and its SQLAlchemy/SQLite initialization run.
    (tmp_path / "tzlocal.py").write_text(
        "def get_localzone():\n    return 'UTC'\n", encoding="utf-8"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(ROOT / "src")))
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
