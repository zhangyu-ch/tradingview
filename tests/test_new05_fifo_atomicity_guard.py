from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "script" / "remediation" / "check_fifo_atomicity.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("fifo_guard", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_repository_has_no_mutation_before_validation() -> None:
    assert _load_checker().validate(ROOT) == []


def test_guard_rejects_original_half_commit_order(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.py"
    source.write_text(
        """
def close(pos):
    consumed = consume_fifo_lots(pos.lots, 5)
    result = close_settlement(symbol_size=0)
    return consumed, result
""".lstrip(),
        encoding="utf-8",
    )
    errors = _load_checker().scan_file(source)
    assert len(errors) == 1
    assert "consumes FIFO lots before" in errors[0]


def test_guard_accepts_validation_before_commit(tmp_path: Path) -> None:
    source = tmp_path / "safe.py"
    source.write_text(
        """
def close(pos):
    result = close_settlement(symbol_size=10)
    consumed = consume_fifo_lots(pos.lots, 5)
    return consumed, result
""".lstrip(),
        encoding="utf-8",
    )
    assert _load_checker().scan_file(source) == []
