import ast
from pathlib import Path


def repo_root():
    resolved = Path(__file__).resolve().parents[1]
    if (resolved / "src").exists():
        return resolved
    cwd = Path.cwd().resolve()
    if (cwd / "src").exists():
        return cwd
    raise AssertionError("cannot locate repository root")


ROOT = repo_root()
RUNTIME_PATHS = [ROOT / "src", ROOT / "web", ROOT / "script", ROOT / "check_env.py"]
SKIP_PARTS = {
    ".git",
    ".venv",
    ".worktrees",
    "archive",
    "docs",
    "cookbook",
    "notebook",
    "tests",
    "__pycache__",
    ".pytest_cache",
}
REMOVED_IMPORTS = {
    "chanlun",
    "tradingview_zy.cl",
    "tradingview_zy.cl_analyse",
    "tradingview_zy.cl_interface",
    "tradingview_zy.cl_utils",
    "tradingview_zy.kcharts",
    "tradingview_zy.monitor",
    "tradingview_zy.strategy",
    "tradingview_zy.xuangu",
    "cl_myquant",
    "cl_vnpy",
}


def iter_python_files():
    for path in RUNTIME_PATHS:
        if path.is_file() and path.suffix == ".py":
            yield path
            continue
        if not path.exists():
            continue
        for py_file in path.rglob("*.py"):
            relative_parts = py_file.relative_to(ROOT).parts
            if any(part in SKIP_PARTS for part in relative_parts):
                continue
            yield py_file


def is_removed_import(module: str) -> bool:
    return any(module == removed or module.startswith(f"{removed}.") for removed in REMOVED_IMPORTS)


def collect_removed_import_offenders(py_file: Path, tree: ast.AST):
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if is_removed_import(alias.name):
                    offenders.append(f"{py_file}: import {alias.name}")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if is_removed_import(module):
                offenders.append(f"{py_file}: from {module} import ...")
            if module == "tradingview_zy":
                for alias in node.names:
                    imported_module = f"{module}.{alias.name}"
                    if is_removed_import(imported_module):
                        offenders.append(f"{py_file}: from {module} import {alias.name}")
    return offenders


def test_iter_python_files_scans_each_runtime_root():
    scanned_files = list(iter_python_files())
    scanned_parts = {py_file.relative_to(ROOT).parts[0] for py_file in scanned_files}
    assert {"src", "web", "script"}.issubset(scanned_parts)


def test_removed_import_prefixes_cover_deleted_runtime_modules():
    assert is_removed_import("tradingview_zy.cl")
    assert is_removed_import("tradingview_zy.cl_analyse")
    assert is_removed_import("tradingview_zy.kcharts")
    assert is_removed_import("tradingview_zy.monitor")
    assert is_removed_import("tradingview_zy.strategy")
    assert is_removed_import("tradingview_zy.xuangu")


def test_collect_removed_import_offenders_detects_deleted_import_forms(tmp_path):
    py_file = tmp_path / "sample.py"
    source = """
import chanlun
from chanlun import cl
import tradingview_zy.cl_utils
from tradingview_zy.cl_utils import helper
import tradingview_zy.monitor
from tradingview_zy.monitor import unavailable
from tradingview_zy import cl_utils, strategy, xuangu, kcharts, cl_analyse, monitor
"""
    tree = ast.parse(source, filename=str(py_file))

    offenders = collect_removed_import_offenders(py_file, tree)

    assert len(offenders) == 12
    assert any("import chanlun" in offender for offender in offenders)
    assert any("from chanlun import ..." in offender for offender in offenders)
    assert any("import tradingview_zy.cl_utils" in offender for offender in offenders)
    assert any("from tradingview_zy.cl_utils import ..." in offender for offender in offenders)
    assert any("import tradingview_zy.monitor" in offender for offender in offenders)
    assert any("from tradingview_zy.monitor import ..." in offender for offender in offenders)
    assert any("from tradingview_zy import cl_utils" in offender for offender in offenders)
    assert any("from tradingview_zy import strategy" in offender for offender in offenders)
    assert any("from tradingview_zy import xuangu" in offender for offender in offenders)
    assert any("from tradingview_zy import kcharts" in offender for offender in offenders)
    assert any("from tradingview_zy import cl_analyse" in offender for offender in offenders)
    assert any("from tradingview_zy import monitor" in offender for offender in offenders)


def test_runtime_python_files_do_not_import_chanlun():
    offenders = []
    scanned_files = list(iter_python_files())
    assert scanned_files != [], "no runtime Python files scanned"
    attempted_files = 0
    skipped_syntax_errors = 0

    for py_file in scanned_files:
        attempted_files += 1
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError:
            skipped_syntax_errors += 1
            continue
        offenders.extend(collect_removed_import_offenders(py_file, tree))
    assert attempted_files > 0, "no runtime Python files attempted"
    assert attempted_files > skipped_syntax_errors, "all runtime Python files failed to parse"
    assert offenders == [], "runtime import boundary offenders:\n" + "\n".join(offenders)
