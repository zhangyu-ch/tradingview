from types import SimpleNamespace

import pytest

from tradingview_zy.base import Market
from tradingview_zy.domain import Capability, InvalidRequestError, UnsupportedCapabilityError
from tradingview_zy.market_registry import (
    MARKET_REGISTRY,
    configured_provider,
    descriptor_for,
    kline_table_name,
    provider_capabilities,
    require_capability,
)


def test_registry_exhaustively_covers_market_enum_and_has_db_provider():
    assert set(MARKET_REGISTRY) == set(Market)
    for market, spec in MARKET_REGISTRY.items():
        assert spec.market is market
        assert spec.timezone
        assert spec.tradingview_type
        assert "db" in spec.providers


def test_configured_provider_rejects_unknown_value_with_supported_list():
    config = SimpleNamespace(EXCHANGE_A="unknown")
    with pytest.raises(InvalidRequestError, match="unknown"):
        configured_provider(Market.A, config)


def test_provider_capabilities_fail_closed_for_live_execution():
    assert Capability.MARKET_DATA in provider_capabilities(Market.A, "tdx")
    with pytest.raises(UnsupportedCapabilityError, match="安全拒绝"):
        require_capability(Market.A, Capability.TRADING_EXECUTION, provider_name="tdx")


def test_kline_table_partition_is_stable_for_every_market():
    examples = {
        Market.A: "SH.600000",
        Market.HK: "HK.00700",
        Market.US: "AAPL",
        Market.FUTURES: "KQ.m@SHFE.rb",
        Market.NY_FUTURES: "CO.GC00W",
        Market.CURRENCY: "BTC/USDT",
        Market.CURRENCY_SPOT: "ETH/USDT",
        Market.FX: "EURUSD",
    }
    names = {market: kline_table_name(market, code) for market, code in examples.items()}
    assert names[Market.A] == "a_klines_sh_6000"
    assert names[Market.HK] == "hk_klines_700"
    assert names[Market.US] == "us_klines_a"
    assert names[Market.NY_FUTURES].startswith("ny_futures_klines_")
    assert len(set(names.values())) == len(names)


def test_descriptor_parses_string_market_and_rejects_unknown():
    assert descriptor_for("us").market is Market.US
    with pytest.raises(InvalidRequestError):
        descriptor_for("moon")
