from threading import RLock
from typing import Dict, List, Union

import ccxt
import pytz

from tradingview_zy import config, fun
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.binance_history import BinanceKlinesMixin
from tradingview_zy.exchange.exchange_db import ExchangeDB
from tradingview_zy.utils import config_get_proxy
from tradingview_zy.secret_store import resolve_config_secret
from tradingview_zy.trading_calendar import is_market_open


class ExchangeBinance(BinanceKlinesMixin, Exchange):
    """
    数字货币交易所接口
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

        self.exchange = ccxt.binanceusdm(params)

        self.db_exchange = ExchangeDB("currency")

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
            "8h": "8H",
            "6h": "6H",
            "4h": "4H",
            "3h": "3H",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "10m": "10m",
            "5m": "5m",
            "3m": "3m",
            "2m": "2m",
            "1m": "1m",
        }

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('currency', code=code, at=at)

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
            if _t["last"] is None:
                continue
            _c = _s.split(":")[0]
            res_ticks[_c] = Tick(
                code=_c,
                last=_t["last"],
                buy1=_t["last"],
                sell1=_t["last"],
                high=_t["high"],
                low=_t["low"],
                open=_t["open"],
                volume=_t["quoteVolume"],
                rate=_t["percentage"],
            )

        return res_ticks

    def balance(self):
        b = self.exchange.fetch_balance()
        balances = {
            "total": b["USDT"]["total"],
            "free": b["USDT"]["free"],
            "used": b["USDT"]["used"],
            "profit": b["info"]["totalUnrealizedProfit"],
        }
        for asset in b["info"]["assets"]:
            balances[asset["asset"]] = {
                "total": asset["availableBalance"],
                "profit": asset["unrealizedProfit"],
            }
        return balances

    def positions(self, code: str = ""):
        try:
            position = self.exchange.fetch_positions(
                symbols=[code] if code != "" else None
            )
        except Exception as e:
            if "precision" in str(e):
                self.__init__()
                position = self.exchange.fetch_positions(
                    symbols=[code] if code != "" else None
                )
            else:
                raise e
        """
        symbol 标的
        entryPrice 价格
        contracts 持仓数量
        side 方向 long short
        leverage 杠杠倍数
        unrealizedPnl 未实现盈亏
        initialMargin 占用保证金
        percentage 盈亏百分比
        """
        # 替换其中的 symbol ，去除后面的 :USDT
        res_poss = []
        for p in position:
            if p["entryPrice"] != 0.0:
                p["symbol"] = p["symbol"].replace(":USDT", "")
                res_poss.append(p)
        return res_poss

    # 撤销所有挂单
    def cancel_all_order(self, code):
        return self._raise_live_trading_disabled("cancel_all_order")

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeBinance()

    # stocks = ex.all_stocks()
    # print(len(stocks))
    # print(stocks[0])

    klines = ex.klines("BTC/USDT", "d")
    print(klines)

    # ticks = ex.ticks(["BTC/USDT", "ETH/USDT"])
    # for _c, _t in ticks.items():
    #     print(
    #         _c, _t.last, _t.buy1, _t.sell1, _t.high, _t.low, _t.open, _t.volume, _t.rate
    #     )

    # zx = zixuan.ZiXuan("currency")
    # zx_group = "选股"
    # run_codes = zx.zx_stocks("策略代码")
    # run_codes = [_s["code"] for _s in run_codes]
    # error_codes = []
    # for code in run_codes:
    #     try:
    #         klines = ex.klines(code, "60m")
    #         print(code)
    #         print(klines.tail())
    #         print(len(klines))
    #     except Exception as e:
    #         print(f"ERROR {code}")
    #         error_codes.append(code)

    # print("Error codes : ", error_codes)

    # balance = ex.balance()
    # print(balance)
