"""Side-effect-free registry for supported markets and provider capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from tradingview_zy.base import Market
from tradingview_zy.domain import (
    CAPABILITY_METHODS,
    Capability,
    InvalidRequestError,
    UnsupportedCapabilityError,
    UnsupportedProviderError,
)


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    module: str
    attribute: str
    capabilities: frozenset[Capability]
    constructor_args: tuple[Any, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketSpec:
    market: Market
    config_attribute: str
    providers: Mapping[str, ProviderSpec]


META = frozenset({Capability.METADATA, Capability.SESSION_STATUS})
DATA = META | frozenset({Capability.MARKET_DATA})
CATALOG = DATA | frozenset({Capability.CATALOG, Capability.SECURITY_MASTER})
CATALOG_TICKS = CATALOG | frozenset({Capability.TICKS})
DB_CAPABILITIES = DATA | frozenset({Capability.CATALOG, Capability.TICKS})


def _provider(
    module: str,
    attribute: str,
    capabilities: frozenset[Capability],
    *constructor_args: Any,
) -> ProviderSpec:
    return ProviderSpec(module, attribute, capabilities, constructor_args)


MARKET_REGISTRY: Mapping[Market, MarketSpec] = MappingProxyType(
    {
        Market.A: MarketSpec(
            Market.A,
            "EXCHANGE_A",
            MappingProxyType(
                {
                    "tdx": _provider(
                        "tradingview_zy.exchange.exchange_tdx",
                        "ExchangeTDX",
                        CATALOG_TICKS | frozenset({Capability.PLATES}),
                    ),
                    "futu": _provider(
                        "tradingview_zy.exchange.exchange_futu",
                        "ExchangeFutu",
                        CATALOG_TICKS
                        | frozenset(
                            {
                                Capability.PLATES,
                                Capability.ACCOUNT_BALANCE,
                                Capability.POSITIONS,
                            }
                        ),
                    ),
                    "baostock": _provider(
                        "tradingview_zy.exchange.exchange_baostock",
                        "ExchangeBaostock",
                        CATALOG,
                    ),
                    "qmt": _provider(
                        "tradingview_zy.exchange.exchange_qmt",
                        "ExchangeQMT",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.A.value,
                    ),
                }
            ),
        ),
        Market.HK: MarketSpec(
            Market.HK,
            "EXCHANGE_HK",
            MappingProxyType(
                {
                    "tdx_hk": _provider(
                        "tradingview_zy.exchange.exchange_tdx_hk",
                        "ExchangeTDXHK",
                        CATALOG_TICKS,
                    ),
                    "futu": _provider(
                        "tradingview_zy.exchange.exchange_futu",
                        "ExchangeFutu",
                        CATALOG_TICKS
                        | frozenset(
                            {
                                Capability.PLATES,
                                Capability.ACCOUNT_BALANCE,
                                Capability.POSITIONS,
                            }
                        ),
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.HK.value,
                    ),
                }
            ),
        ),
        Market.FUTURES: MarketSpec(
            Market.FUTURES,
            "EXCHANGE_FUTURES",
            MappingProxyType(
                {
                    "tq": _provider(
                        "tradingview_zy.exchange.exchange_tq",
                        "ExchangeTq",
                        CATALOG_TICKS
                        | frozenset(
                            {Capability.ACCOUNT_BALANCE, Capability.POSITIONS}
                        ),
                    ),
                    "tdx_futures": _provider(
                        "tradingview_zy.exchange.exchange_tdx_futures",
                        "ExchangeTDXFutures",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.FUTURES.value,
                    ),
                }
            ),
        ),
        Market.NY_FUTURES: MarketSpec(
            Market.NY_FUTURES,
            "EXCHANGE_NY_FUTURES",
            MappingProxyType(
                {
                    "tdx_ny_futures": _provider(
                        "tradingview_zy.exchange.exchange_tdx_ny_futures",
                        "ExchangeTDXNYFutures",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.NY_FUTURES.value,
                    ),
                }
            ),
        ),
        Market.FX: MarketSpec(
            Market.FX,
            "EXCHANGE_FX",
            MappingProxyType(
                {
                    "tdx_fx": _provider(
                        "tradingview_zy.exchange.exchange_tdx_fx",
                        "ExchangeTDXFX",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.FX.value,
                    ),
                }
            ),
        ),
        Market.CURRENCY: MarketSpec(
            Market.CURRENCY,
            "EXCHANGE_CURRENCY",
            MappingProxyType(
                {
                    "binance": _provider(
                        "tradingview_zy.exchange.exchange_binance",
                        "ExchangeBinance",
                        CATALOG_TICKS
                        | frozenset(
                            {Capability.ACCOUNT_BALANCE, Capability.POSITIONS}
                        ),
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.CURRENCY.value,
                    ),
                }
            ),
        ),
        Market.CURRENCY_SPOT: MarketSpec(
            Market.CURRENCY_SPOT,
            "EXCHANGE_CURRENCY_SPOT",
            MappingProxyType(
                {
                    "binance_spot": _provider(
                        "tradingview_zy.exchange.exchange_binance_spot",
                        "ExchangeBinanceSpot",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.CURRENCY_SPOT.value,
                    ),
                }
            ),
        ),
        Market.US: MarketSpec(
            Market.US,
            "EXCHANGE_US",
            MappingProxyType(
                {
                    "alpaca": _provider(
                        "tradingview_zy.exchange.exchange_alpaca",
                        "ExchangeAlpaca",
                        CATALOG_TICKS,
                    ),
                    "polygon": _provider(
                        "tradingview_zy.exchange.exchange_polygon",
                        "ExchangePolygon",
                        CATALOG,
                    ),
                    "ib": _provider(
                        "tradingview_zy.exchange.exchange_ib",
                        "ExchangeIB",
                        CATALOG_TICKS
                        | frozenset(
                            {Capability.ACCOUNT_BALANCE, Capability.POSITIONS}
                        ),
                    ),
                    "tdx_us": _provider(
                        "tradingview_zy.exchange.exchange_tdx_us",
                        "ExchangeTDXUS",
                        CATALOG_TICKS,
                    ),
                    "db": _provider(
                        "tradingview_zy.exchange.exchange_db",
                        "ExchangeDB",
                        DB_CAPABILITIES,
                        Market.US.value,
                    ),
                }
            ),
        ),
    }
)


def parse_market(value: Market | str) -> Market:
    if isinstance(value, Market):
        return value
    try:
        return Market(str(value))
    except ValueError as error:
        raise InvalidRequestError("不支持的市场") from error


def market_spec(value: Market | str) -> MarketSpec:
    return MARKET_REGISTRY[parse_market(value)]


def configured_provider(value: Market | str, config_module: Any) -> str:
    spec = market_spec(value)
    provider = getattr(config_module, spec.config_attribute, None)
    if not isinstance(provider, str) or provider not in spec.providers:
        supported = ", ".join(sorted(spec.providers))
        raise UnsupportedProviderError(
            f"{spec.market.value} 市场的数据源不受支持；可选：{supported}"
        )
    return provider


def provider_spec(
    value: Market | str, provider_name: str | None = None, config_module: Any | None = None
) -> tuple[str, ProviderSpec]:
    spec = market_spec(value)
    if provider_name is None:
        if config_module is None:
            raise InvalidRequestError("缺少数据源配置")
        provider_name = configured_provider(spec.market, config_module)
    try:
        return provider_name, spec.providers[provider_name]
    except KeyError as error:
        raise UnsupportedProviderError("配置的数据源不受支持") from error


def provider_capabilities(
    value: Market | str, provider_name: str | None = None, config_module: Any | None = None
) -> frozenset[Capability]:
    return provider_spec(value, provider_name, config_module)[1].capabilities


def require_capability(
    value: Market | str,
    capability: Capability,
    *,
    provider_name: str | None = None,
    config_module: Any | None = None,
) -> None:
    name, spec = provider_spec(value, provider_name, config_module)
    if capability not in spec.capabilities:
        raise UnsupportedCapabilityError(
            f"{parse_market(value).value}/{name} 不支持能力 {capability.value}",
            provider=name,
        )


def validate_market_registry() -> None:
    if set(MARKET_REGISTRY) != set(Market):
        raise RuntimeError("市场注册表不完整")
    for market, spec in MARKET_REGISTRY.items():
        if spec.market is not market or not spec.providers or "db" not in spec.providers:
            raise RuntimeError(f"市场注册表条目无效：{market.value}")
        for name, provider in spec.providers.items():
            if Capability.LIVE_ORDERS in provider.capabilities:
                raise RuntimeError(f"未验收实盘能力不得声明：{market.value}/{name}")
            for capability in provider.capabilities:
                if capability not in CAPABILITY_METHODS:
                    raise RuntimeError(f"未知能力：{capability}")
    for market in Market:
        db = MARKET_REGISTRY[market].providers["db"]
        if Capability.SECURITY_MASTER in db.capabilities or Capability.PLATES in db.capabilities:
            raise RuntimeError("DB provider 不得过报 security master/plates")


validate_market_registry()
