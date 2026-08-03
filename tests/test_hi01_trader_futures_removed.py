from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_broken_trader_futures_module_is_not_in_the_runtime_package() -> None:
    assert not (ROOT / "src/tradingview_zy/trader/trader_futures.py").exists()


def test_no_runtime_code_uses_the_removed_exchange_tq_keyword_or_trader() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "TraderFutures" in text or "trader_futures" in text:
                offenders.append(str(path.relative_to(ROOT)))
            if "ExchangeTq(use_account=" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_live_trading_documentation_requires_a_new_verified_implementation() -> None:
    text = (ROOT / "docs/live-trading-disabled.md").read_text(encoding="utf-8")
    assert "persisted `client_order_id`" in text
    assert "partially-filled" in text
    assert "crash-safe reconciliation" in text
