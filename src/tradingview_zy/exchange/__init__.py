from tradingview_zy import config
from tradingview_zy.base import Market
from tradingview_zy.exchange.exchange import Exchange

# 全局保存交易所对象，避免创建多个交易所对象
g_exchange_obj = {}


class UnsupportedProviderError(RuntimeError):
    """Configured provider was intentionally removed from the runtime package."""


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
        raise UnsupportedProviderError(message)


def get_exchange(market: Market) -> Exchange:
    """
    获取市场的交易所对象，根据config配置中设置的进行获取
    """
    global g_exchange_obj
    if market.value in g_exchange_obj.keys():
        return g_exchange_obj[market.value]

    if market == Market.A:
        # 沪深 A股 交易所
        if config.EXCHANGE_A == "tdx":
            from tradingview_zy.exchange.exchange_tdx import ExchangeTDX

            g_exchange_obj[market.value] = ExchangeTDX()
        elif config.EXCHANGE_A == "futu":
            from tradingview_zy.exchange.exchange_futu import ExchangeFutu

            g_exchange_obj[market.value] = ExchangeFutu()
        elif config.EXCHANGE_A == "baostock":
            from tradingview_zy.exchange.exchange_baostock import ExchangeBaostock

            g_exchange_obj[market.value] = ExchangeBaostock()
        elif config.EXCHANGE_A == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.A.value)
        elif config.EXCHANGE_A == "qmt":
            from tradingview_zy.exchange.exchange_qmt import ExchangeQMT

            g_exchange_obj[market.value] = ExchangeQMT()
        else:
            raise Exception(f"不支持的沪深交易所 {config.EXCHANGE_A}")

    elif market == Market.HK:
        # 港股 交易所
        if config.EXCHANGE_HK == "tdx_hk":
            from tradingview_zy.exchange.exchange_tdx_hk import ExchangeTDXHK

            g_exchange_obj[market.value] = ExchangeTDXHK()
        elif config.EXCHANGE_HK == "futu":
            from tradingview_zy.exchange.exchange_futu import ExchangeFutu

            g_exchange_obj[market.value] = ExchangeFutu()
        elif config.EXCHANGE_HK == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.HK.value)
        else:
            raise Exception(f"不支持的香港交易所 {config.EXCHANGE_HK}")

    elif market == Market.FUTURES:
        # 期货交易所；已移除的 provider 在任何惰性导入或缓存写入前 fail closed。
        _reject_removed_provider(Market.FUTURES, config.EXCHANGE_FUTURES)
        if config.EXCHANGE_FUTURES == "tq":
            from tradingview_zy.exchange.exchange_tq import ExchangeTq

            g_exchange_obj[market.value] = ExchangeTq()
        elif config.EXCHANGE_FUTURES == "tdx_futures":
            from tradingview_zy.exchange.exchange_tdx_futures import ExchangeTDXFutures

            g_exchange_obj[market.value] = ExchangeTDXFutures()
        elif config.EXCHANGE_FUTURES == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.FUTURES.value)
        else:
            raise Exception(f"不支持的期货交易所 {config.EXCHANGE_FUTURES}")
    elif market == Market.NY_FUTURES:
        # 美股期货 交易所
        if config.EXCHANGE_NY_FUTURES == "tdx_ny_futures":
            from tradingview_zy.exchange.exchange_tdx_ny_futures import ExchangeTDXNYFutures

            g_exchange_obj[market.value] = ExchangeTDXNYFutures()
        elif config.EXCHANGE_NY_FUTURES == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.NY_FUTURES.value)
    elif market == Market.FX:
        # 外汇市场行情
        if config.EXCHANGE_FX == "tdx_fx":
            from tradingview_zy.exchange.exchange_tdx_fx import ExchangeTDXFX

            g_exchange_obj[market.value] = ExchangeTDXFX()
        elif config.EXCHANGE_FX == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.FX.value)
        else:
            raise Exception(f"不支持的外汇交易所 {config.EXCHANGE_FX}")

    elif market == Market.CURRENCY:
        # 数字货币交易所；已移除 provider 在惰性导入与缓存写入前 fail closed。
        _reject_removed_provider(Market.CURRENCY, config.EXCHANGE_CURRENCY)
        if config.EXCHANGE_CURRENCY == "binance":
            from tradingview_zy.exchange.exchange_binance import ExchangeBinance

            g_exchange_obj[market.value] = ExchangeBinance()
        elif config.EXCHANGE_CURRENCY == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.CURRENCY.value)
        else:
            raise Exception(f"不支持的数字货币交易所 {config.EXCHANGE_CURRENCY}")
    elif market == Market.CURRENCY_SPOT:
        # 数字货币 交易所
        if config.EXCHANGE_CURRENCY_SPOT == "binance_spot":
            from tradingview_zy.exchange.exchange_binance_spot import ExchangeBinanceSpot

            g_exchange_obj[market.value] = ExchangeBinanceSpot()
        elif config.EXCHANGE_CURRENCY_SPOT == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.CURRENCY_SPOT.value)
        else:
            raise Exception(f"不支持的数字货币交易所 {config.EXCHANGE_CURRENCY_SPOT}")
    elif market == Market.US:
        # 美股 交易所
        if config.EXCHANGE_US == "alpaca":
            from tradingview_zy.exchange.exchange_alpaca import ExchangeAlpaca

            g_exchange_obj[market.value] = ExchangeAlpaca()
        elif config.EXCHANGE_US == "polygon":
            from tradingview_zy.exchange.exchange_polygon import ExchangePolygon

            g_exchange_obj[market.value] = ExchangePolygon()
        elif config.EXCHANGE_US == "ib":
            from tradingview_zy.exchange.exchange_ib import ExchangeIB

            g_exchange_obj[market.value] = ExchangeIB()
        elif config.EXCHANGE_US == "tdx_us":
            from tradingview_zy.exchange.exchange_tdx_us import ExchangeTDXUS

            g_exchange_obj[market.value] = ExchangeTDXUS()
        elif config.EXCHANGE_US == "db":
            from tradingview_zy.exchange.exchange_db import ExchangeDB

            g_exchange_obj[market.value] = ExchangeDB(Market.US.value)
        else:
            raise Exception(f"不支持的美股交易所 {config.EXCHANGE_US}")

    return g_exchange_obj[market.value]
