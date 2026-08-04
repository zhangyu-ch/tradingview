from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_zb_runtime_and_configuration_are_absent() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_zb.py").exists()
    template = (ROOT / "src/tradingview_zy/config.py.demo").read_text(
        encoding="utf-8"
    ).lower()
    assert " / zb" not in template
    assert "zb_apikey" not in template
    assert "zb_secret" not in template


def test_runtime_python_has_no_tls_verification_bypass() -> None:
    patterns = {
        "verify_false": re.compile(r"\bverify\s*=\s*False\b"),
        "cert_none": re.compile(r"\bCERT_NONE\b"),
        "check_hostname_false": re.compile(r"\bcheck_hostname\s*=\s*False\b"),
        "websocket_sslopt": re.compile(r"\bsslopt\s*="),
    }
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in patterns.items():
                if pattern.search(text):
                    offenders.append(f"{path.relative_to(ROOT)}:{name}")
    assert offenders == []


def test_factory_rejects_zb_before_import_and_cache_mutation() -> None:
    path = ROOT / "src/tradingview_zy/exchange/__init__.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    get_exchange = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "get_exchange"
    )
    currency_branch = next(
        node
        for node in ast.walk(get_exchange)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and ast.get_source_segment(source, node.test) == "market == Market.CURRENCY"
    )
    segment = ast.get_source_segment(source, currency_branch) or ""

    reject_offset = segment.index("_reject_removed_provider(")
    import_offsets = [
        segment.index("from tradingview_zy.exchange.exchange_binance import"),
        segment.index("from tradingview_zy.exchange.exchange_db import"),
    ]
    cache_offset = segment.index("g_exchange_obj[market.value]")

    assert reject_offset < min(import_offsets)
    assert reject_offset < cache_offset
    assert "exchange_zb" not in segment


def test_runtime_tree_has_no_direct_zb_adapter_reference() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "exchange_zb" in text or "ccxt.zb" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_documented_tls_restoration_contract_is_fail_closed() -> None:
    text = (ROOT / "docs/unsupported-providers.md").read_text(encoding="utf-8")

    assert "ZB TLS restoration contract (`NX-25`)" in text
    assert "certificate-chain" in text
    assert "hostname verification enabled" in text
    assert "system trust store" in text
    assert "CA bundle" in text
    assert "verification failure must abort" in text
    for forbidden in ("verify=False", "ssl.CERT_NONE", "check_hostname=False", "sslopt"):
        assert forbidden in text
