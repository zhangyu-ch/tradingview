"""Single source of truth for supported markets and provider capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from types import MappingProxyType
from typing import Any, Callable, Mapping

from tradingview_zy.base import Market
from tradingview_zy.domain import (
    Capability,
    InvalidRequestError,
    UnsupportedCapabilityError,
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
    timezone: str
    tradingview_type: str
    tradingview_session: str
    default_code: str
    providers: Mapping[str, ProviderSpec]
    db_partition: Callable[[str], str]


def _normalise_code(code: str) -> str:
    return (
        code.replace(".", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("@", "_")
        .lower()
    )


def _suffix3(code: str) -> str:
    return _normalise_code(code)[-3:]


def _a_prefix(code: str) -> str:
    return _normalise_code(code)[:7]


def _us_initial(code: str) -> str:
    normalised = _normalise_code(code)
    if not normalised:
        raise InvalidRequestError("证券代码不能为空")
    return normalised[0]


def _full(code: str) -> str:
    normalised = _normalise_code(code)
    if not normalised:
        raise InvalidRequestError("证券代码不能为空")
    return normalised


MD = frozenset({Capability.MARKET_DATA, Capability.TICKS, Capability.SECURITY_MASTER})
MD_PLATES = MD | frozenset({Capability.PLATES})
MD_ACCOUNT = MD | frozenset({Capability.ACCOUNT_BALANCE, Capability.POSITIONS})
DB_CAPABILITIES = MD_PLATES


def _provider(
    module: str,
    attribute: str,
    capabilities: frozenset[Capability] = MD,
    *constructor_args: Any,
) -> ProviderSpec:
    return ProviderSpec(module, attribute, capabilities, constructor_args)


MARKET_REGISTRY: Mapping[Market, MarketSpec] = MappingProxyType(
    {
        Market.A: MarketSpec(
            Market.A,
            "EXCHANGE_A",
            "Asia/Shanghai",
            "stock",
            "0930-1130,1300-1500:23456",
            "SH.000001",
            MappingProxyType(
                {
                    "tdx": _provider("tradingview_zy.exchange.exchange_tdx", "ExchangeTDX", MD_PLATES),
                    "futu": _provider("tradingview_zy.exchange.exchange_futu", "ExchangeFutu", MD_ACCOUNT),
                    "baostock": _provider("tradingview_zy.exchange.exchange_baostock", "ExchangeBaostock"),
                    "qmt": _provider("tradingview_zy.exchange.exchange_qmt", "ExchangeQMT", MD_ACCOUNT),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.A.value),
                }
            ),
            _a_prefix,
        ),
        Market.HK: MarketSpec(
            Market.HK,
            "EXCHANGE_HK",
            "Asia/Hong_Kong",
            "stock",
            "0930-1200,1300-1600:23456",
            "HK.00700",
            MappingProxyType(
                {
                    "tdx_hk": _provider("tradingview_zy.exchange.exchange_tdx_hk", "ExchangeTDXHK", MD_PLATES),
                    "futu": _provider("tradingview_zy.exchange.exchange_futu", "ExchangeFutu", MD_ACCOUNT),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.HK.value),
                }
            ),
            _suffix3,
        ),
        Market.FUTURES: MarketSpec(
            Market.FUTURES,
            "EXCHANGE_FUTURES",
            "Asia/Shanghai",
            "futures",
            "0900-1015,1030-1130,1330-1500,2100-2359:23456",
            "KQ.m@SHFE.rb",
            MappingProxyType(
                {
                    "tq": _provider("tradingview_zy.exchange.exchange_tq", "ExchangeTq", MD_ACCOUNT),
                    "tdx_futures": _provider("tradingview_zy.exchange.exchange_tdx_futures", "ExchangeTDXFutures", MD),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.FUTURES.value),
                }
            ),
            _full,
        ),
        Market.NY_FUTURES: MarketSpec(
            Market.NY_FUTURES,
            "EXCHANGE_NY_FUTURES",
            "America/New_York",
            "futures",
            "0000-2359:1234567",
            "CO.GC00W",
            MappingProxyType(
                {
                    "tdx_ny_futures": _provider("tradingview_zy.exchange.exchange_tdx_ny_futures", "ExchangeTDXNYFutures", MD),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.NY_FUTURES.value),
                }
            ),
            _full,
        ),
        Market.CURRENCY: MarketSpec(
            Market.CURRENCY,
            "EXCHANGE_CURRENCY",
            "Etc/UTC",
            "crypto",
            "24x7",
            "BTC/USDT",
            MappingProxyType(
                {
                    "binance": _provider("tradingview_zy.exchange.exchange_binance", "ExchangeBinance", MD_ACCOUNT),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.CURRENCY.value),
                }
            ),
            _full,
        ),
        Market.CURRENCY_SPOT: MarketSpec(
            Market.CURRENCY_SPOT,
            "EXCHANGE_CURRENCY_SPOT",
            "Etc/UTC",
            "crypto",
            "24x7",
            "BTC/USDT",
            MappingProxyType(
                {
                    "binance_spot": _provider("tradingview_zy.exchange.exchange_binance_spot", "ExchangeBinanceSpot", MD_ACCOUNT),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.CURRENCY_SPOT.value),
                }
            ),
            _full,
        ),
        Market.US: MarketSpec(
            Market.US,
            "EXCHANGE_US",
            "America/New_York",
            "stock",
            "0930-1600:23456",
            "AAPL",
            MappingProxyType(
                {
                    "alpaca": _provider("tradingview_zy.exchange.exchange_alpaca", "ExchangeAlpaca", MD_ACCOUNT),
                    "polygon": _provider("tradingview_zy.exchange.exchange_polygon", "ExchangePolygon", MD),
                    "ib": _provider("tradingview_zy.exchange.exchange_ib", "ExchangeIB", MD_ACCOUNT),
                    "tdx_us": _provider("tradingview_zy.exchange.exchange_tdx_us", "ExchangeTDXUS", MD),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.US.value),
                }
            ),
            _us_initial,
        ),
        Market.FX: MarketSpec(
            Market.FX,
            "EXCHANGE_FX",
            "Etc/UTC",
            "forex",
            "24x5",
            "EURUSD",
            MappingProxyType(
                {
                    "tdx_fx": _provider("tradingview_zy.exchange.exchange_tdx_fx", "ExchangeTDXFX", MD),
                    "db": _provider("tradingview_zy.exchange.exchange_db", "ExchangeDB", DB_CAPABILITIES, Market.FX.value),
                }
            ),
            _full,
        ),
    }
)


def parse_market(value: Market | str) -> Market:
    if isinstance(value, Market):
        return value
    try:
        return Market(str(value))
    except ValueError as error:
        raise InvalidRequestError(f"不支持的市场：{value!r}") from error


def descriptor_for(value: Market | str) -> MarketSpec:
    return MARKET_REGISTRY[parse_market(value)]


def configured_provider(value: Market | str, config_module: Any) -> str:
    spec = descriptor_for(value)
    provider = getattr(config_module, spec.config_attribute, None)
    if not isinstance(provider, str) or provider not in spec.providers:
        supported = ", ".join(sorted(spec.providers))
        raise InvalidRequestError(
            f"{spec.market.value} 市场 provider {provider!r} 不受支持；可选：{supported}"
        )
    return provider


def construct_provider(value: Market | str, config_module: Any):
    spec = descriptor_for(value)
    provider_name = configured_provider(spec.market, config_module)
    provider = spec.providers[provider_name]
    module = import_module(provider.module)
    constructor = getattr(module, provider.attribute)
    return constructor(*provider.constructor_args)


def provider_capabilities(
    value: Market | str, provider_name: str | None = None, config_module: Any | None = None
) -> frozenset[Capability]:
    spec = descriptor_for(value)
    if provider_name is None:
        if config_module is None:
            raise InvalidRequestError("provider_name 与 config_module 至少提供一个")
        provider_name = configured_provider(spec.market, config_module)
    try:
        return spec.providers[provider_name].capabilities
    except KeyError as error:
        raise InvalidRequestError(
            f"{spec.market.value} 市场没有 provider {provider_name!r}"
        ) from error


def require_capability(
    value: Market | str,
    capability: Capability,
    *,
    provider_name: str | None = None,
    config_module: Any | None = None,
) -> None:
    if capability not in provider_capabilities(value, provider_name, config_module):
        market = parse_market(value)
        raise UnsupportedCapabilityError(
            f"{market.value} 的 provider 未声明能力 {capability.value}；请求已安全拒绝"
        )


def kline_table_name(value: Market | str, code: str) -> str:
    spec = descriptor_for(value)
    return f"{spec.market.value}_klines_{spec.db_partition(code)}"


def validate_market_registry() -> None:
    if set(MARKET_REGISTRY) != set(Market):
        missing = set(Market) - set(MARKET_REGISTRY)
        extra = set(MARKET_REGISTRY) - set(Market)
        raise RuntimeError(f"市场注册表不完整：missing={missing}, extra={extra}")
    for market, spec in MARKET_REGISTRY.items():
        if market is not spec.market or not spec.providers:
            raise RuntimeError(f"市场注册表条目无效：{market}")
        if "db" not in spec.providers:
            raise RuntimeError(f"{market.value} 缺少 db provider")


validate_market_registry()
