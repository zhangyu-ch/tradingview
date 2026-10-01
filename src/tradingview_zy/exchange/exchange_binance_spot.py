from threading import RLock
from typing import Dict, List, Union

import ccxt
import pytz

from tradingview_zy import config, fun
from tradingview_zy.base import Market
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.binance_history import BinanceKlinesMixin
from tradingview_zy.exchange.exchange_db import ExchangeDB
from tradingview_zy.utils import config_get_proxy
from tradingview_zy.secret_store import resolve_config_secret
from tradingview_zy.trading_calendar import is_market_open


class ExchangeBinanceSpot(BinanceKlinesMixin, Exchange):
    """
    数字货币交易所接口(现货交易)
    """

    g_all_stocks = []

    def __init__(self):
        params = {"timeout": 4000, "maxRetriesOnFailure": 0}
        self._ohlcv_lock = RLock()

        proxy = config_get_proxy()
        # print(proxy)

        # 设置是否使用代理
        if proxy["host"] != "":
            params["proxies"] = {
                "https": f"http://{proxy['host']}:{proxy['port']}",
                "http": f"http://{proxy['host']}:{proxy['port']}",
            }

        # 设置是否设置交易 api
        api_key = resolve_config_secret(config, "BINANCE_APIKEY")
        api_secret = resolve_config_secret(config, "BINANCE_SECRET")
        if bool(api_key) != bool(api_secret):
            raise RuntimeError("Binance API key and secret must be configured together")
        if api_key:
            params["apiKey"] = api_key
            params["secret"] = api_secret

        self.exchange = ccxt.binance(params)
        # self.exchange = ccxt.htx(params)
        # self.exchange = ccxt.okx(params)

        self.db_exchange = ExchangeDB(Market.CURRENCY_SPOT.value)

        # 设置时区
        # self.tz = pytz.timezone("Asia/Shanghai")
        self.tz = pytz.UTC

    def default_code(self):
        return "BTC/USDT"

    def support_frequencys(self):
        return {
            "w": "Week",
            "d": "Day",
            "12h": "12H",
            "4h": "4H",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "10m": "10m",
            "5m": "5m",
            "1m": "1m",
        }

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('currency_spot', code=code, at=at)

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        数字货币全部返回 code 值
        """
        all_stocks = self.all_stocks()
        for _s in all_stocks:
            if _s["code"] == code:
                return _s

    def all_stocks(self):
        """
        返回所有交易对儿
        """
        if len(self.g_all_stocks) > 0:
            return self.g_all_stocks

        markets = self.exchange.load_markets(reload=True)
        __all_stocks = []
        for _, s in markets.items():
            if s["active"] and s["quote"] == "USDT":
                __all_stocks.append(
                    {
                        "code": s["base"] + "/" + s["quote"],
                        "name": s["base"] + "/" + s["quote"],
                        "precision": fun.reverse_decimal_to_power_of_ten(
                            s["precision"]["price"]
                        ),
                    }
                )
        self.g_all_stocks = __all_stocks
        return self.g_all_stocks

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        res_ticks = {}
        _ts = self.exchange.fetch_tickers(codes)
        for _s, _t in _ts.items():
            if _t["last"] is None or _t["bid"] is None or _t["ask"] is None:
                continue
            res_ticks[_s] = Tick(
                code=_s,
                last=_t["last"],
                buy1=_t["bid"],
                sell1=_t["ask"],
                high=_t["high"],
                low=_t["low"],
                open=_t["open"],
                volume=_t["quoteVolume"],
                rate=_t["percentage"],
            )

        return res_ticks

    # 撤销所有挂单
    def cancel_all_order(self, code):
        return self._raise_live_trading_disabled("cancel_all_order")

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeBinanceSpot()

    # stocks = ex.all_stocks()
    # print(len(stocks))
    # stocks = sorted(stocks, key=lambda x: x["precision"], reverse=True)
    # for _s in stocks[0:10]:
    #     print(_s)

    klines = ex.klines("BTC/USDT", "5m")
    print(klines)

    # ticks = ex.ticks(["BTC/USDT"])
    # for _c, _t in ticks.items():
    #     print(
    #         _c, _t.last, _t.buy1, _t.sell1, _t.high, _t.low, _t.open, _t.volume, _t.rate
    #     )
