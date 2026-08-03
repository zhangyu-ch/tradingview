from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script" / "remediation" / "check_dependency_contract.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("dependency_contract", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_repository_dependency_contract_is_consistent() -> None:
    checker = _load_checker()
    assert checker.validate(ROOT) == []


def test_checker_rejects_second_dependency_source_and_unsafe_versions(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample"
requires-python = ">=3.11"
dependencies = ["chardet>=5", "websockets>=13"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "chardet\nwebsockets\n", encoding="utf-8"
    )
    (tmp_path / "uv.lock").write_text(
        """
version = 1
revision = 3
requires-python = ">=3.11"

[[package]]
name = "chardet"
version = "7.1.0"

[[package]]
name = "sample"
version = "1.0.0"
source = { virtual = "." }
dependencies = [{ name = "chardet" }, { name = "websockets" }]
[package.metadata]
requires-dist = [
  { name = "chardet", specifier = ">=5" },
  { name = "websockets", specifier = ">=13" },
]

[[package]]
name = "websockets"
version = "16.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    errors = _load_checker().validate(tmp_path)
    joined = "\n".join(errors)
    assert "requires-python" in joined
    assert "chardet" in joined
    assert "requirements.txt" in joined
    assert "websockets" in joined
