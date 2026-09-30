from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradingview_zy.base import Market
from tradingview_zy.exchange.contracted import ContractedExchange
from tradingview_zy.domain import Capability, ProviderUnavailableError
from tradingview_zy.market_registry import ProviderSpec

ROOT = Path(__file__).resolve().parents[1]


def test_provider_classes_do_not_own_a_second_singleton_cache():
    for path in (ROOT / "src/tradingview_zy/exchange").glob("exchange_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                assert all("singleton" not in ast.unparse(decorator) for decorator in node.decorator_list), path


def test_factory_reset_reconstructs_and_cross_market_switch_does_not_close_peer(monkeypatch):
    import tradingview_zy.exchange as factory

    class Provider:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

        def default_code(self):
            return "TEST"

        def support_frequencys(self):
            return {"d": "D"}

    spec = ProviderSpec("tests.fake_b19", "Provider", frozenset({Capability.METADATA}))
    selected = {Market.A: "futu", Market.HK: "futu"}
    monkeypatch.setattr(factory, "g_exchange_obj", {})
    monkeypatch.setattr(factory, "selected_provider", lambda market, config: selected[market])
    monkeypatch.setattr(factory, "provider_spec", lambda *args, **kwargs: ("futu", spec))
    monkeypatch.setattr(factory, "import_module", lambda name: SimpleNamespace(Provider=Provider))

    a = factory.get_exchange(Market.A)
    hk = factory.get_exchange(Market.HK)
    assert a.raw_provider is not hk.raw_provider
    assert factory.get_exchange(Market.A) is a
    selected[Market.A] = "tdx"
    new_a = factory.get_exchange(Market.A)
    assert a.raw_provider.closed
    assert not hk.raw_provider.closed
    assert new_a.raw_provider is not a.raw_provider
    factory.reset_exchange_cache()
    assert new_a.raw_provider.closed and hk.raw_provider.closed
    fresh_hk = factory.get_exchange(Market.HK)
    assert fresh_hk.raw_provider is not hk.raw_provider
    assert not fresh_hk.raw_provider.closed
    factory.reset_exchange_cache()


def test_real_futu_instances_have_independent_terminal_context_owners(monkeypatch):
    pytest.importorskip("futu")
    from tradingview_zy.exchange import exchange_futu

    monkeypatch.setattr(exchange_futu.config, "FUTU_HOST", "", raising=False)
    first = exchange_futu.ExchangeFutu()
    second = exchange_futu.ExchangeFutu()
    assert first is not second
    assert first._contexts is not second._contexts
    first.close()
    assert first._contexts.health()["state"] == "closed"
    assert second._contexts.health()["state"] != "closed"
    second.close()


def test_transport_exhaustion_retains_retryable_facade_classification():
    from tradingview_zy.exchange.tdx_reliability import call_with_bounded_retry

    root_error = TimeoutError("credential-must-stay-private")

    class Provider:
        def default_code(self):
            return "TEST"

        def support_frequencys(self):
            return {"d": "D"}

        def klines(self, *args, **kwargs):
            def fail(remaining):
                raise root_error
            return call_with_bounded_retry(fail, retry_on=(TimeoutError,), max_attempts=1)

    spec = ProviderSpec("tests.fake_b19", "Provider", frozenset({Capability.METADATA, Capability.MARKET_DATA}))
    facade = ContractedExchange(Market.A, "tdx", Provider(), spec)
    with pytest.raises(ProviderUnavailableError) as error:
        facade.klines("TEST", "d")
    assert error.value.retryable is True
    assert error.value.__cause__.__cause__ is root_error
    assert "credential-must-stay-private" not in str(error.value.to_dict())
