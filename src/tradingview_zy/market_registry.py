"""Single, side-effect-free descriptor registry for every supported market."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

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
    """All static facts needed to expose one market across the stack.

    ``config_attribute`` is retained only as a compatibility reader for older
    local ``config.py`` files. New configurations use ``MARKET_PROVIDERS`` and
    otherwise inherit ``default_provider`` from this descriptor.
    """

    market: Market | str
    config_attribute: str
    default_provider: str
    ui_label: str
    tradingview_name: str
    description: str
    default_code: str
    frequencies: Mapping[str, str]
    tradingview_type: str
    tradingview_timezone: str
    tradingview_sessions: Mapping[str, str]
    default_session_profile: str
    payload_timezone: str
    has_seconds: bool
    search_by_name: bool
    providers: Mapping[str, ProviderSpec]
    db_partition: Callable[[str], str]
    is_default: bool = False
    plate_panel: bool = False
    additional_sync_frequencies: frozenset[str] = frozenset()
    kline_has_position: bool = False
    session_profile_from_calendar: bool = False


META = frozenset({Capability.METADATA, Capability.SESSION_STATUS})
DATA = META | frozenset({Capability.MARKET_DATA})
CATALOG = DATA | frozenset({Capability.CATALOG, Capability.SECURITY_MASTER})
CATALOG_TICKS = CATALOG | frozenset({Capability.TICKS})
DB_CAPABILITIES = DATA | frozenset({Capability.CATALOG, Capability.TICKS})


def _freeze(values: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(values))


def _provider(
    module: str,
    attribute: str,
    capabilities: frozenset[Capability],
    *constructor_args: Any,
) -> ProviderSpec:
    return ProviderSpec(module, attribute, capabilities, constructor_args)


def _normalise_code(code: str) -> str:
    if not isinstance(code, str):
        raise InvalidRequestError("证券代码必须是字符串")
    normalised = (
        code.strip()
        .replace(".", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("@", "_")
        .lower()
    )
    if not normalised:
        raise InvalidRequestError("证券代码不能为空")
    return normalised


def _prefix7(code: str) -> str:
    return _normalise_code(code)[:7]


def _suffix3(code: str) -> str:
    return _normalise_code(code)[-3:]


def _initial(code: str) -> str:
    return _normalise_code(code)[0]


def _full(code: str) -> str:
    return _normalise_code(code)


def market_value(value: Market | str) -> str:
    return value.value if isinstance(value, Market) else str(value).strip().lower()


_CN_FUTURES_SESSIONS = _freeze(
    {
        "commodity_day": "0900-1015,1030-1130,1330-1500:23456",
        "night_2300": "2100-2300,0900-1015,1030-1130,1330-1500:23456",
        "night_0100": "2100-0100,0900-1015,1030-1130,1330-1500:23456",
        "night_0230": "2100-0230,0900-1015,1030-1130,1330-1500:23456",
        "cffex_index": "0930-1130,1300-1500:23456",
        "cffex_treasury": "0930-1130,1300-1515:23456",
    }
)


MARKET_REGISTRY: Mapping[Market, MarketSpec] = MappingProxyType(
    {
        Market.A: MarketSpec(
            market=Market.A,
            config_attribute="EXCHANGE_A",
            default_provider="tdx",
            ui_label="沪深A股",
            tradingview_name="沪深",
            description="沪深A股",
            default_code="SH.000001",
            frequencies=_freeze(
                {
                    "y": "Y",
                    "m": "M",
                    "w": "W",
                    "d": "D",
                    "120m": "120m",
                    "60m": "60m",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "10m",
                    "5m": "5m",
                }
            ),
            tradingview_type="stock",
            tradingview_timezone="Asia/Shanghai",
            tradingview_sessions=_freeze(
                {"regular": "0930-1130,1300-1500:23456"}
            ),
            default_session_profile="regular",
            payload_timezone="Asia/Shanghai",
            has_seconds=False,
            search_by_name=True,
            is_default=True,
            plate_panel=True,
            providers=_freeze(
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
            db_partition=_prefix7,
        ),
        Market.HK: MarketSpec(
            market=Market.HK,
            config_attribute="EXCHANGE_HK",
            default_provider="tdx_hk",
            ui_label="港股",
            tradingview_name="港股",
            description="港股",
            default_code="HK.00700",
            frequencies=_freeze(
                {
                    "y": "Y",
                    "q": "Q",
                    "m": "M",
                    "w": "W",
                    "d": "D",
                    "60m": "60m",
                    "30m": "30m",
                    "15m": "15m",
                    "5m": "5m",
                }
            ),
            tradingview_type="stock",
            tradingview_timezone="Asia/Hong_Kong",
            tradingview_sessions=_freeze(
                {"regular": "0930-1200,1300-1600:23456"}
            ),
            default_session_profile="regular",
            payload_timezone="Asia/Shanghai",
            has_seconds=False,
            search_by_name=True,
            additional_sync_frequencies=frozenset({"10m"}),
            providers=_freeze(
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
            db_partition=_suffix3,
        ),
        Market.FX: MarketSpec(
            market=Market.FX,
            config_attribute="EXCHANGE_FX",
            default_provider="tdx_fx",
            ui_label="外汇",
            tradingview_name="外汇",
            description="外汇",
            default_code="USDCNH",
            frequencies=_freeze(
                {
                    "w": "W",
                    "d": "D",
                    "60m": "60m",
                    "30m": "30m",
                    "15m": "15m",
                    "5m": "5m",
                    "1m": "1m",
                }
            ),
            tradingview_type="forex",
            tradingview_timezone="America/New_York",
            tradingview_sessions=_freeze({"regular": "24x5"}),
            default_session_profile="regular",
            payload_timezone="UTC",
            has_seconds=False,
            search_by_name=True,
            providers=_freeze(
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
            db_partition=_full,
        ),
        Market.US: MarketSpec(
            market=Market.US,
            config_attribute="EXCHANGE_US",
            default_provider="tdx_us",
            ui_label="美股",
            tradingview_name="美股",
            description="美股",
            default_code="AAPL",
            frequencies=_freeze(
                {
                    "m": "Month",
                    "w": "Week",
                    "d": "Day",
                    "60m": "60m",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "10m",
                    "5m": "5m",
                    "2m": "2m",
                    "1m": "1m",
                }
            ),
            tradingview_type="stock",
            tradingview_timezone="America/New_York",
            tradingview_sessions=_freeze({"regular": "0930-1600:23456"}),
            default_session_profile="regular",
            payload_timezone="America/New_York",
            has_seconds=False,
            search_by_name=True,
            providers=_freeze(
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
            db_partition=_initial,
        ),
        Market.FUTURES: MarketSpec(
            market=Market.FUTURES,
            config_attribute="EXCHANGE_FUTURES",
            default_provider="tdx_futures",
            ui_label="国内期货",
            tradingview_name="国内期货",
            description="国内期货",
            default_code="KQ.m@SHFE.rb",
            frequencies=_freeze(
                {
                    "w": "W",
                    "d": "D",
                    "120m": "2H",
                    "60m": "1H",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "10m",
                    "5m": "5m",
                    "1m": "1m",
                }
            ),
            tradingview_type="futures",
            tradingview_timezone="Asia/Shanghai",
            tradingview_sessions=_CN_FUTURES_SESSIONS,
            default_session_profile="commodity_day",
            payload_timezone="Asia/Shanghai",
            has_seconds=True,
            search_by_name=True,
            providers=_freeze(
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
            db_partition=_full,
            kline_has_position=True,
            session_profile_from_calendar=True,
        ),
        Market.NY_FUTURES: MarketSpec(
            market=Market.NY_FUTURES,
            config_attribute="EXCHANGE_NY_FUTURES",
            default_provider="tdx_ny_futures",
            ui_label="纽约期货",
            tradingview_name="纽约期货",
            description="纽约期货",
            default_code="CO.GC00W",
            frequencies=_freeze(
                {
                    "w": "W",
                    "d": "D",
                    "120m": "2H",
                    "60m": "1H",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "10m",
                    "5m": "5m",
                    "1m": "1m",
                }
            ),
            tradingview_type="futures",
            tradingview_timezone="America/New_York",
            tradingview_sessions=_freeze({"regular": "1800-1700:23456"}),
            default_session_profile="regular",
            payload_timezone="America/New_York",
            has_seconds=True,
            search_by_name=True,
            providers=_freeze(
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
            db_partition=_full,
        ),
        Market.CURRENCY: MarketSpec(
            market=Market.CURRENCY,
            config_attribute="EXCHANGE_CURRENCY",
            default_provider="binance",
            ui_label="数字货币(合约)",
            tradingview_name="数字货币(Futures)",
            description="数字货币（合约）",
            default_code="BTC/USDT",
            frequencies=_freeze(
                {
                    "w": "Week",
                    "d": "Day",
                    "4h": "4H",
                    "60m": "1H",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "5m",
                    "5m": "5m",
                    "3m": "3m",
                    "2m": "2m",
                    "1m": "1m",
                }
            ),
            tradingview_type="crypto",
            tradingview_timezone="Etc/UTC",
            tradingview_sessions=_freeze({"regular": "24x7"}),
            default_session_profile="regular",
            payload_timezone="UTC",
            has_seconds=False,
            search_by_name=False,
            providers=_freeze(
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
            db_partition=_full,
        ),
        Market.CURRENCY_SPOT: MarketSpec(
            market=Market.CURRENCY_SPOT,
            config_attribute="EXCHANGE_CURRENCY_SPOT",
            default_provider="binance_spot",
            ui_label="数字货币(现货)",
            tradingview_name="数字货币(Spot)",
            description="数字货币（现货）",
            default_code="BTC/USDT",
            frequencies=_freeze(
                {
                    "w": "Week",
                    "d": "Day",
                    "4h": "4H",
                    "60m": "1H",
                    "30m": "30m",
                    "15m": "15m",
                    "10m": "5m",
                    "5m": "5m",
                    "3m": "3m",
                    "2m": "2m",
                    "1m": "1m",
                }
            ),
            tradingview_type="crypto",
            tradingview_timezone="Etc/UTC",
            tradingview_sessions=_freeze({"regular": "24x7"}),
            default_session_profile="regular",
            payload_timezone="UTC",
            has_seconds=False,
            search_by_name=False,
            providers=_freeze(
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
            db_partition=_full,
        ),
    }
)


def parse_market(value: Market | str) -> Market:
    if isinstance(value, Market):
        return value
    try:
        return Market(str(value).strip().lower())
    except ValueError as error:
        raise InvalidRequestError("不支持的市场") from error


def market_spec(
    value: Market | str, *, registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY
) -> MarketSpec:
    wanted = market_value(value)
    for spec in registry.values():
        if market_value(spec.market) == wanted:
            return spec
    raise InvalidRequestError("不支持的市场")


def selected_provider(
    value: Market | str,
    config_module: Any,
    *,
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> str:
    """Resolve an override without importing a provider.

    Precedence is the new mapping, an existing legacy ``EXCHANGE_*`` setting,
    then the descriptor default. This lets old local configs continue to work
    while a newly registered market requires no config-file edit.
    """

    spec = market_spec(value, registry=registry)
    key = market_value(spec.market)
    sentinel = object()
    provider: Any = sentinel
    overrides = getattr(config_module, "MARKET_PROVIDERS", None)
    if overrides is not None:
        if not isinstance(overrides, Mapping):
            raise UnsupportedProviderError("MARKET_PROVIDERS 必须是映射")
        if key in overrides:
            provider = overrides[key]
        elif spec.market in overrides:
            provider = overrides[spec.market]
    if provider is sentinel:
        legacy = getattr(config_module, spec.config_attribute, sentinel)
        if legacy is not sentinel:
            provider = legacy
    if provider is sentinel:
        provider = spec.default_provider
    if not isinstance(provider, str) or not provider.strip():
        raise UnsupportedProviderError(f"{key} 市场的数据源配置无效")
    return provider.strip()


def configured_provider(
    value: Market | str,
    config_module: Any,
    *,
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> str:
    spec = market_spec(value, registry=registry)
    provider = selected_provider(value, config_module, registry=registry)
    if provider not in spec.providers:
        supported = ", ".join(sorted(spec.providers))
        raise UnsupportedProviderError(
            f"{market_value(spec.market)} 市场的数据源不受支持；可选：{supported}"
        )
    return provider


def provider_spec(
    value: Market | str,
    provider_name: str | None = None,
    config_module: Any | None = None,
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
    value: Market | str,
    provider_name: str | None = None,
    config_module: Any | None = None,
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


def kline_table_name(
    value: Market | str,
    code: str,
    *,
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> str:
    spec = market_spec(value, registry=registry)
    return f"{market_value(spec.market)}_klines_{spec.db_partition(code)}"


def registered_market_values(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> tuple[str, ...]:
    return tuple(market_value(spec.market) for spec in registry.values())


def validate_market_registry(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
    *,
    expected_markets: frozenset[Market] = frozenset(Market),
) -> None:
    if set(registry) != set(expected_markets):
        raise RuntimeError("市场注册表不完整")
    seen_values: set[str] = set()
    defaults: list[str] = []
    for market, spec in registry.items():
        value = market_value(spec.market)
        if spec.market is not market or value in seen_values:
            raise RuntimeError(f"市场注册表键无效：{value}")
        seen_values.add(value)
        if spec.is_default:
            defaults.append(value)
        if not spec.providers or "db" not in spec.providers:
            raise RuntimeError(f"市场注册表条目无效：{value}")
        if spec.default_provider not in spec.providers:
            raise RuntimeError(f"默认数据源未注册：{value}/{spec.default_provider}")
        if (
            not spec.ui_label
            or not spec.tradingview_name
            or not spec.description
            or not spec.default_code
            or not spec.frequencies
        ):
            raise RuntimeError(f"市场 Web 元数据不完整：{value}")
        if not spec.tradingview_type or not spec.tradingview_timezone:
            raise RuntimeError(f"TradingView 元数据不完整：{value}")
        if spec.default_session_profile not in spec.tradingview_sessions:
            raise RuntimeError(f"默认交易时段不存在：{value}")
        if not spec.payload_timezone or not spec.db_partition(spec.default_code):
            raise RuntimeError(f"市场数据路由不完整：{value}")
        if not all(
            isinstance(frequency, str) and frequency.strip()
            for frequency in spec.additional_sync_frequencies
        ):
            raise RuntimeError(f"同步周期元数据无效：{value}")
        for name, provider in spec.providers.items():
            if Capability.LIVE_ORDERS in provider.capabilities:
                raise RuntimeError(f"未验收实盘能力不得声明：{value}/{name}")
            for capability in provider.capabilities:
                if capability not in CAPABILITY_METHODS:
                    raise RuntimeError(f"未知能力：{capability}")
        db = spec.providers["db"]
        if Capability.SECURITY_MASTER in db.capabilities or Capability.PLATES in db.capabilities:
            raise RuntimeError("DB provider 不得过报 security master/plates")
    if len(defaults) != 1:
        raise RuntimeError(f"市场注册表必须且只能声明一个默认市场：{defaults}")


validate_market_registry()
