from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_capability_documentation_is_explicit_about_db_limitations() -> None:
    text = (ROOT / "docs/provider-capabilities.md").read_text(encoding="utf-8")
    assert "does **not** provide an authoritative security master" in text
    assert "Declaring `SECURITY_MASTER` or `PLATES`" in text
