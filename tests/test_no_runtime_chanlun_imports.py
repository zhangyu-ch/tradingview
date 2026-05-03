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
RUNTIME_PATHS = [ROOT / "src", ROOT / "web", ROOT / "script", ROOT / "check_env.py", ROOT / "setup.py"]
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
    "tradingview_zy.cl_interface",
    "tradingview_zy.cl_utils",
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
            if any(part in SKIP_PARTS for part in py_file.parts):
                continue
            yield py_file


def is_removed_import(module: str) -> bool:
    return any(module == removed or module.startswith(f"{removed}.") for removed in REMOVED_IMPORTS)


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
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if is_removed_import(alias.name):
                        offenders.append(f"{py_file}: import {alias.name}")
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if is_removed_import(module):
                    offenders.append(f"{py_file}: from {module} import ...")
    assert attempted_files > 0, "no runtime Python files attempted"
    assert attempted_files > skipped_syntax_errors, "all runtime Python files failed to parse"
    assert offenders == [], "runtime import boundary offenders:\n" + "\n".join(offenders)
