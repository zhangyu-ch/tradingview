from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_tree_contains_no_ctp_front_address_names() -> None:
    forbidden = ("ctp_front", "md_front", "td_front", "front_md", "front_td")
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if any(token in text for token in forbidden):
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_documented_restoration_contract_handles_empty_addresses_before_sdk() -> None:
    text = (ROOT / "docs/unsupported-providers.md").read_text(encoding="utf-8")

    assert "CTP front-address restoration contract (`NX-01`)" in text
    assert "non-empty `tcp://host:port`" in text
    assert "before an OpenCTP SDK object is constructed" in text
    assert "empty string must either be rejected" in text
    assert "must not expose" in text
    assert "credentials" in text
