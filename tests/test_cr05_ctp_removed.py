from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ctp_runtime_implementation_and_dependency_are_removed() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_ctp.py").exists()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8").lower()
    assert "openctp-ctp" not in pyproject
    assert "openctp-ctp" not in lock

    config_template = (ROOT / "src/tradingview_zy/config.py.demo").read_text(
        encoding="utf-8"
    )
    assert "CTP_" not in config_template


@pytest.mark.parametrize("market, removed", [("futures", "ctp"), ("currency", "zb")])
@pytest.mark.parametrize("matching_cache", [None, False, True], ids=["empty", "different", "matching"])
def test_factory_rejects_removed_provider_without_import_or_cache_mutation(
    monkeypatch, market, removed, matching_cache
) -> None:
    import tradingview_zy.exchange as exchange

    cached = Mock(provider_name=removed if matching_cache else "db")
    unrelated = Mock(provider_name="db")
    cache = {} if matching_cache is None else {market: cached, "hk": unrelated}
    original = dict(cache)
    importer = Mock(side_effect=AssertionError("removed provider must not import an SDK"))
    monkeypatch.setattr(exchange.config, "MARKET_PROVIDERS", {market: removed})
    monkeypatch.setattr(exchange, "g_exchange_obj", cache)
    monkeypatch.setattr(exchange, "import_module", importer)

    with pytest.raises(exchange.UnsupportedProviderError, match="已从运行包移除"):
        exchange.get_exchange(market)

    assert cache == original
    importer.assert_not_called()
    cached.close.assert_not_called()
    unrelated.close.assert_not_called()


def test_runtime_tree_contains_no_openctp_imports() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "openctp_ctp" in text or "exchange_ctp" in text or "trader_ctp" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
