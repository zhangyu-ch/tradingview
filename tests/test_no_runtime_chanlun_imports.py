import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATHS = [ROOT / "src", ROOT / "web", ROOT / "script", ROOT / "check_env.py", ROOT / "setup.py"]
SKIP_PARTS = {".venv", "archive", "docs", "cookbook", "notebook", "__pycache__"}


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


def test_runtime_python_files_do_not_import_chanlun():
    offenders = []
    for py_file in iter_python_files():
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "chanlun" or alias.name.startswith("chanlun."):
                        offenders.append(f"{py_file}: import {alias.name}")
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module == "chanlun" or module.startswith("chanlun."):
                    offenders.append(f"{py_file}: from {module} import ...")
    assert offenders == []
