from __future__ import annotations

import ast
import importlib
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

from tradingview_zy.base import Market
from tradingview_zy.exchange.contracted import ContractedExchange
from tradingview_zy.exchange.exchange import LiveTradingDisabledError
from tradingview_zy.domain import (
    CAPABILITY_METHODS,
    Capability,
    ProviderResponseError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)
from tradingview_zy.market_registry import MARKET_REGISTRY, ProviderSpec

ROOT = Path(__file__).resolve().parents[1]


def _provider_class(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)


def _method_is_stub(node: ast.FunctionDef) -> bool:
    body = node.body
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    if len(body) == 1 and isinstance(body[0], ast.Raise):
        return True
    if len(body) == 1 and isinstance(body[0], ast.Return):
        value = body[0].value
        if isinstance(value, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return not getattr(value, "elts", None) and not getattr(value, "keys", None)
    return False


def test_registry_covers_every_market_and_is_conservative() -> None:
    assert set(MARKET_REGISTRY) == set(Market)
    assert sum(len(spec.providers) for spec in MARKET_REGISTRY.values()) == 24
    for market, spec in MARKET_REGISTRY.items():
        assert "db" in spec.providers
        for provider in spec.providers.values():
            assert Capability.LIVE_ORDERS not in provider.capabilities
        db = spec.providers["db"]
        assert Capability.CATALOG in db.capabilities
        assert Capability.SECURITY_MASTER not in db.capabilities
        assert Capability.PLATES not in db.capabilities
        assert Capability.ACCOUNT_BALANCE not in db.capabilities
        assert Capability.POSITIONS not in db.capabilities


def test_every_declared_capability_has_a_non_stub_provider_method() -> None:
    for spec in MARKET_REGISTRY.values():
        for provider in spec.providers.values():
            path = ROOT / "src" / Path(provider.module.replace(".", "/") + ".py")
            cls = _provider_class(path, provider.attribute)
            methods = {
                node.name: node
                for node in cls.body
                if isinstance(node, ast.FunctionDef)
            }
            for capability in provider.capabilities:
                for method_name in CAPABILITY_METHODS[capability]:
                    assert method_name in methods, (provider.attribute, capability, method_name)
                    assert not _method_is_stub(methods[method_name]), (
                        provider.attribute,
                        capability,
                        method_name,
                    )


class _GoodProvider:
    def default_code(self): return "X"
    def support_frequencys(self): return {"d": "D"}
    def klines(self, *args, **kwargs):
        return pd.DataFrame([{"date": pd.Timestamp("2026-01-01", tz="UTC"), "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 3.0}])
    def ticks(self, codes): return {}
    def all_stocks(self): return [{"code": "X", "name": "Example"}]
    def stock_info(self, code): return {"code": code, "name": "Example"}
    def now_trading(self, code=None, at=None): return False


def _facade(provider=None, capabilities=None):
    capabilities = capabilities or frozenset({
        Capability.METADATA,
        Capability.MARKET_DATA,
        Capability.TICKS,
        Capability.CATALOG,
        Capability.SESSION_STATUS,
    })
    spec = ProviderSpec("tests.fake", "Fake", capabilities)
    return ContractedExchange(Market.A, "fake", provider or _GoodProvider(), spec)


def test_facade_rejects_undeclared_capability_before_call() -> None:
    class Provider(_GoodProvider):
        called = False
        def balance(self):
            self.called = True
            return {"cash": 1}
    provider = Provider()
    facade = _facade(provider)
    with pytest.raises(UnsupportedCapabilityError) as exc_info:
        facade.balance()
    assert provider.called is False
    assert exc_info.value.to_dict()["code"] == "unsupported_capability"


def test_facade_translates_errors_without_exposing_sdk_secret() -> None:
    class Provider(_GoodProvider):
        def klines(self, *args, **kwargs):
            raise RuntimeError("api_secret=SENTINEL token=SENTINEL")
    with pytest.raises(ProviderResponseError) as exc_info:
        _facade(Provider()).klines("X", "d")
    text = str(exc_info.value) + repr(exc_info.value.to_dict())
    assert "SENTINEL" not in text
    assert exc_info.value.to_dict()["retryable"] is False


def test_connection_failures_are_retryable_but_secret_safe() -> None:
    class VendorConnectionError(Exception): pass
    class Provider(_GoodProvider):
        def ticks(self, codes): raise VendorConnectionError("token=SENTINEL")
    with pytest.raises(ProviderUnavailableError) as exc_info:
        _facade(Provider()).ticks(["X"])
    assert exc_info.value.to_dict()["retryable"] is True
    assert "SENTINEL" not in str(exc_info.value)


def test_response_shape_is_validated() -> None:
    class Provider(_GoodProvider):
        def klines(self, *args, **kwargs): return [{"close": 1}]
    with pytest.raises(ProviderResponseError):
        _facade(Provider()).klines("X", "d")


def test_factory_publishes_cache_only_after_success(monkeypatch) -> None:
    import tradingview_zy.exchange as exchange
    from tradingview_zy import config

    exchange.reset_exchange_cache()
    module_name = "tests.fake_me10_provider"
    module = types.ModuleType(module_name)
    calls = {"count": 0}

    class Provider(_GoodProvider):
        def __init__(self):
            calls["count"] += 1
            if calls["count"] == 1:
                raise ConnectionError("api_secret=SENTINEL")

    module.Provider = Provider
    sys.modules[module_name] = module
    fake = ProviderSpec(
        module_name,
        "Provider",
        frozenset(
            {
                Capability.METADATA,
                Capability.MARKET_DATA,
                Capability.TICKS,
                Capability.CATALOG,
                Capability.SESSION_STATUS,
            }
        ),
    )
    monkeypatch.setattr(config, "MARKET_PROVIDERS", {"a": "tdx"})
    monkeypatch.setattr(exchange, "selected_provider", lambda market, config_module: "tdx")
    monkeypatch.setattr(exchange, "provider_spec", lambda market, provider_name=None: ("tdx", fake))
    try:
        with pytest.raises(ProviderUnavailableError):
            exchange.get_exchange(Market.A)
        assert Market.A.value not in exchange.g_exchange_obj
        facade = exchange.get_exchange(Market.A)
        assert facade.provider_name == "tdx"
        assert exchange.g_exchange_obj[Market.A.value] is facade
    finally:
        exchange.reset_exchange_cache()
        sys.modules.pop(module_name, None)


def test_facade_live_orders_remain_fail_closed_even_if_a_spec_overreports_capability() -> None:
    class Provider(_GoodProvider):
        called = False

        def order(self, *args, **kwargs):
            self.called = True
            return {"status": "filled"}

    provider = Provider()
    facade = _facade(
        provider,
        frozenset(
            {
                Capability.METADATA,
                Capability.MARKET_DATA,
                Capability.TICKS,
                Capability.CATALOG,
                Capability.SESSION_STATUS,
                Capability.LIVE_ORDERS,
            }
        ),
    )
    with pytest.raises(LiveTradingDisabledError, match="Order/Fill state machine"):
        facade.order("X", "buy", 1)
    assert provider.called is False
