from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_runtime_has_no_ctp_front_consumer_or_configuration() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_ctp.py").exists()
    assert not (ROOT / "src/tradingview_zy/trader/trader_ctp.py").exists()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8").lower()
    template = (ROOT / "src/tradingview_zy/config.py.demo").read_text(encoding="utf-8")

    assert "openctp-ctp" not in pyproject
    assert "openctp-ctp" not in lock
    assert "CTP_" not in template


def test_removed_ctp_is_rejected_before_provider_import_or_cache_write() -> None:
    path = ROOT / "src/tradingview_zy/exchange/__init__.py"
    source = path.read_text(encoding="utf-8")
    method_start = source.index("def get_exchange")
    segment = source[method_start:]
    reject_offset = segment.index("_reject_removed_provider(market, provider_name)")
    registry_offset = segment.index("selected_provider(market, config)")
    import_offset = segment.index("import_module(spec.module)")
    cache_offset = segment.index("g_exchange_obj[market.value] = facade")
    assert registry_offset < reject_offset < import_offset < cache_offset
    assert "exchange_ctp" not in segment

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
