import ast
from pathlib import Path

import pytest


def repo_root():
    resolved = Path(__file__).resolve().parents[1]
    if (resolved / "src").exists():
        return resolved
    cwd = Path.cwd().resolve()
    if (cwd / "src").exists():
        return cwd
    raise AssertionError("cannot locate repository root")


ROOT = repo_root()
RUNTIME_PATHS = [
    ROOT / "src",
    ROOT / "web",
    ROOT / "script",
    ROOT / "check_env.py",
]
ACTIVE_LEGACY_ENTRIES = [
    ROOT / "joinquant",
    ROOT / "notebook/导入聚宽数据.ipynb",
    ROOT / "src/cl_myquant",
    ROOT / "src/cl_vnpy",
    ROOT / "src/cl_wtpy",
]
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
    "cl",
    "jqdata",
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
    "cl_wtpy",
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


def parse_runtime_python_file(py_file: Path) -> ast.AST:
    try:
        return ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError as error:
        raise AssertionError(
            f"runtime Python file does not parse: {py_file}: {error}"
        ) from error


def is_removed_import(module: str) -> bool:
    return any(
        module == removed or module.startswith(f"{removed}.")
        for removed in REMOVED_IMPORTS
    )


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
                        offenders.append(
                            f"{py_file}: from {module} import {alias.name}"
                        )
    return offenders


def test_iter_python_files_scans_each_runtime_root():
    scanned_files = list(iter_python_files())
    scanned_parts = {py_file.relative_to(ROOT).parts[0] for py_file in scanned_files}
    assert {"src", "web", "script"}.issubset(scanned_parts)


def test_legacy_adapter_paths_are_absent_from_active_tree():
    offenders = [
        str(path.relative_to(ROOT))
        for path in ACTIVE_LEGACY_ENTRIES
        if path.exists()
    ]
    assert offenders == [], (
        "legacy adapter paths remain active: " + ", ".join(offenders)
    )


def test_removed_import_prefixes_cover_deleted_runtime_modules():
    for module in [
        "chanlun",
        "cl",
        "jqdata",
        "cl_myquant",
        "cl_vnpy",
        "cl_wtpy",
        "tradingview_zy.cl",
        "tradingview_zy.cl_analyse",
        "tradingview_zy.kcharts",
        "tradingview_zy.monitor",
        "tradingview_zy.strategy",
        "tradingview_zy.xuangu",
    ]:
        assert is_removed_import(module)


def test_collect_removed_import_offenders_detects_deleted_import_forms(tmp_path):
    py_file = tmp_path / "sample.py"
    source = """
import chanlun
from chanlun import cl
import cl
from cl import CL
from jqdata import get_bars
import cl_myquant
from cl_vnpy import run_app
import cl_wtpy.strategy
import tradingview_zy.cl_utils
from tradingview_zy.cl_utils import helper
import tradingview_zy.monitor
from tradingview_zy.monitor import unavailable
from tradingview_zy import cl_utils, strategy, xuangu, kcharts, cl_analyse, monitor
"""
    tree = ast.parse(source, filename=str(py_file))

    offenders = collect_removed_import_offenders(py_file, tree)

    expected_fragments = [
        "import chanlun",
        "from chanlun import ...",
        "import cl",
        "from cl import ...",
        "from jqdata import ...",
        "import cl_myquant",
        "from cl_vnpy import ...",
        "import cl_wtpy.strategy",
        "import tradingview_zy.cl_utils",
        "from tradingview_zy.cl_utils import ...",
        "import tradingview_zy.monitor",
        "from tradingview_zy.monitor import ...",
        "from tradingview_zy import cl_utils",
        "from tradingview_zy import strategy",
        "from tradingview_zy import xuangu",
        "from tradingview_zy import kcharts",
        "from tradingview_zy import cl_analyse",
        "from tradingview_zy import monitor",
    ]
    for fragment in expected_fragments:
        assert any(fragment in offender for offender in offenders), fragment


def test_parse_runtime_python_file_rejects_syntax_errors(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n    pass\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="runtime Python file does not parse"):
        parse_runtime_python_file(broken)


def test_runtime_python_files_do_not_import_removed_legacy_modules():
    offenders = []
    scanned_files = list(iter_python_files())
    assert scanned_files, "no runtime Python files scanned"

    for py_file in scanned_files:
        tree = parse_runtime_python_file(py_file)
        offenders.extend(collect_removed_import_offenders(py_file, tree))

    assert offenders == [], "runtime import boundary offenders:\n" + "\n".join(offenders)
