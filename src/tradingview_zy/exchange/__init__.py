from __future__ import annotations

from importlib import import_module
from threading import RLock

from tradingview_zy import config
from tradingview_zy.base import Market
from tradingview_zy.exchange.contracted import ContractedExchange
from tradingview_zy.domain import (
    Capability,
    ExchangeError,
    ProviderResponseError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
    UnsupportedProviderError,
)
from tradingview_zy.exchange.exchange import Exchange
from tradingview_zy.market_registry import (
    configured_provider,
    provider_capabilities,
    provider_spec,
    require_capability,
)

# Global cache remains for migration compatibility, but only fully constructed
# capability-bound facades are published.
g_exchange_obj: dict[str, ContractedExchange] = {}
_exchange_lock = RLock()

_REMOVED_PROVIDERS = {
    (Market.FUTURES, "ctp"): (
        "CTP provider 已从运行包移除（CR-05）：原实现不满足行情、订单状态、"
        "重连与资源释放契约。请选择 tq、tdx_futures 或 db。"
    ),
    (Market.CURRENCY, "zb"): (
        "ZB provider 已从运行包移除（MX-02）：配置曾宣称支持，但标准工厂从未"
        "注册该适配器，且遗留实现关闭 TLS 校验。请选择 binance 或 db。"
    ),
}


def _reject_removed_provider(market: Market, provider: str) -> None:
    message = _REMOVED_PROVIDERS.get((market, provider))
    if message is not None:
        raise UnsupportedProviderError(message, provider=provider)


def _translate_constructor_error(provider_name: str, error: BaseException) -> ExchangeError:
    name = type(error).__name__.lower()
    if isinstance(error, (TimeoutError, ConnectionError, OSError)) or any(
        token in name for token in ("timeout", "connection", "unavailable", "network")
    ):
        return ProviderUnavailableError(provider=provider_name)
    return ProviderResponseError("数据源构造失败", provider=provider_name)


def get_exchange(market: Market | str) -> ContractedExchange:
    """Return a lazily constructed, capability-bound provider facade."""
    market = market if isinstance(market, Market) else Market(str(market))
    provider_name = getattr(config, {
        Market.A: "EXCHANGE_A",
        Market.HK: "EXCHANGE_HK",
        Market.FUTURES: "EXCHANGE_FUTURES",
        Market.NY_FUTURES: "EXCHANGE_NY_FUTURES",
        Market.FX: "EXCHANGE_FX",
        Market.CURRENCY: "EXCHANGE_CURRENCY",
        Market.CURRENCY_SPOT: "EXCHANGE_CURRENCY_SPOT",
        Market.US: "EXCHANGE_US",
    }[market], None)

    # Tombstones must run before registry resolution, provider import or cache mutation.
    if isinstance(provider_name, str):
        _reject_removed_provider(market, provider_name)

    with _exchange_lock:
        cached = g_exchange_obj.get(market.value)
        if cached is not None and cached.provider_name == provider_name:
            return cached
        if cached is not None:
            cached.close()
            g_exchange_obj.pop(market.value, None)

        provider_name = configured_provider(market, config)
        _reject_removed_provider(market, provider_name)
        _, spec = provider_spec(market, provider_name=provider_name)
        try:
            module = import_module(spec.module)
            constructor = getattr(module, spec.attribute)
            raw_provider = constructor(*spec.constructor_args)
            facade = ContractedExchange(market, provider_name, raw_provider, spec)
        except ExchangeError:
            raise
        except Exception as error:
            raise _translate_constructor_error(provider_name, error) from error

        g_exchange_obj[market.value] = facade
        return facade


def reset_exchange_cache() -> None:
    """Close and clear all standard-factory provider facades."""
    with _exchange_lock:
        providers = list(g_exchange_obj.values())
        g_exchange_obj.clear()
    for provider in providers:
        provider.close()
