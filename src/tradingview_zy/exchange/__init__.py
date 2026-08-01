from tradingview_zy import config
from tradingview_zy.base import Market
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tradingview_zy.exchange.exchange import Exchange
else:
    Exchange = Any

# 全局保存交易所对象，避免创建多个交易所对象
# Keyed by market; provider configuration is validated before construction.
g_exchange_obj: dict[str, Exchange] = {}

CTP_UNAVAILABLE_MESSAGE = (
    "CTP 适配器当前不可用（CR-05 尚未修复）。"
    "请将 EXCHANGE_FUTURES 设置为 tq、tdx_futures 或 db。"
)

_PROVIDER_ERROR_LABELS = {
    Market.A: "沪深交易所",
    Market.HK: "香港交易所",
    Market.FUTURES: "期货交易所",
    Market.NY_FUTURES: "纽约期货交易所",
    Market.FX: "外汇交易所",
    Market.CURRENCY: "数字货币交易所",
    Market.CURRENCY_SPOT: "数字货币现货交易所",
    Market.US: "美股交易所",
}


def get_exchange(market: Market) -> Exchange:
    """Return the configured provider for ``market`` from the central registry.

    Provider imports are lazy. Invalid configuration fails before an object is
    cached, so a half-constructed adapter cannot poison later requests.
    """
    global g_exchange_obj
    if not isinstance(market, Market):
        market = Market(market)
    if market.value in g_exchange_obj:
        return g_exchange_obj[market.value]

    if market is Market.FUTURES and getattr(config, "EXCHANGE_FUTURES", None) == "ctp":
        # Do not import the unfinished CTP module. Fail closed with a stable,
        # user-facing explanation until CR-05 is repaired.
        raise RuntimeError(CTP_UNAVAILABLE_MESSAGE)

    from tradingview_zy.domain import InvalidRequestError
    from tradingview_zy.market_registry import configured_provider, construct_provider

    try:
        configured_provider(market, config)
        provider = construct_provider(market, config)
    except InvalidRequestError as error:
        from tradingview_zy.market_registry import descriptor_for

        spec = descriptor_for(market)
        configured = getattr(config, spec.config_attribute, None)
        labels = {
            Market.A: "沪深交易所",
            Market.HK: "香港交易所",
            Market.FUTURES: "期货交易所",
            Market.NY_FUTURES: "纽约期货交易所",
            Market.FX: "外汇交易所",
            Market.CURRENCY: "数字货币交易所",
            Market.CURRENCY_SPOT: "数字货币现货交易所",
            Market.US: "美股交易所",
        }
        raise Exception(f"不支持的{labels[market]} {configured}") from error

    g_exchange_obj[market.value] = provider
    return provider
