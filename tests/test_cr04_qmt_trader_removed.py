from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_unsafe_qmt_live_trader_is_removed_but_market_data_remains() -> None:
    assert not (ROOT / "src/tradingview_zy/trader/trader_qmt_stock.py").exists()
    market_data = ROOT / "src/tradingview_zy/exchange/exchange_qmt.py"
    assert market_data.exists()
    assert "class ExchangeQMT" in market_data.read_text(encoding="utf-8")


def test_runtime_tree_has_no_qmt_live_trader_entrypoint() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "QMTTraderStock" in text or "trader_qmt_stock" in text:
                offenders.append(str(path.relative_to(ROOT)))
            if "from xtquant.xttrader import" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_removed_provider_documentation_distinguishes_market_data() -> None:
    text = (ROOT / "docs/unsupported-providers.md").read_text(encoding="utf-8")
    assert "QMT live trading (`CR-04`)" in text
    assert "QMT **market data** remains" in text
    assert "must never be converted into simulated fills" in text
