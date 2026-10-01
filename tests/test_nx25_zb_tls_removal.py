from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
