"""
US Polygon 行情接口
"""

import os
from typing import Union

from polygon.rest import RESTClient
from tenacity import retry_if_result, wait_random, stop_after_attempt, retry

from tradingview_zy import config
from tradingview_zy import fun
from tradingview_zy.secret_store import resolve_config_secret
from tradingview_zy.exchange.exchange import *
from tradingview_zy.exchange.us_history import (
    build_us_history_frame,
    parse_us_history_window,
)
from tradingview_zy.trading_calendar import is_market_open


@fun.singleton
class ExchangePolygon(Exchange):
    """
    美股 Polygon 行情服务
    """

    g_all_stocks = []

    def __init__(self):
        super().__init__()

        self.client = RESTClient(resolve_config_secret(config, "POLYGON_APIKEY", required=True))

        self.trade_days = None

        # 设置时区
        self.tz = pytz.timezone("US/Eastern")

    def default_code(self):
        return "AAPL"

    def support_frequencys(self):
        return {
            "y": "Year",
            "q": "Quarter",
            "m": "Month",
            "w": "Week",
            "d": "Day",
            "120m": "2H",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "5m": "5m",
            "1m": "1m",
        }

    def all_stocks(self):
        """
        使用 Polygono 的方式获取所有股票代码
        美股获取所有标的时间比较长，直接从 json 文件中获取
        """
        if len(self.g_all_stocks) > 0:
            return self.g_all_stocks
        stocks = pd.read_csv(
            os.path.split(os.path.realpath(__file__))[0] + "/us_symbols.csv"
        )
        __all_stocks = []
        for s in stocks.iterrows():
            __all_stocks.append({"code": s[1]["code"], "name": s[1]["name"]})
        self.g_all_stocks = __all_stocks
        return self.g_all_stocks

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random(min=1, max=5),
        retry=retry_if_result(lambda _r: _r is None),
    )
    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        if args is None:
            args = {}
        frequency_map = {
            "y": "year",
            "q": "quarter",
            "m": "month",
            "w": "week",
            "d": "day",
            "120m": "hour",
            "60m": "hour",
            "30m": "minute",
            "15m": "minute",
            "5m": "minute",
            "1m": "minute",
        }
        frequency_mult = {
            "y": 1,
            "q": 1,
            "m": 1,
            "w": 1,
            "d": 1,
            "120m": 2,
            "60m": 1,
            "30m": 30,
            "15m": 15,
            "5m": 5,
            "1m": 1,
        }

        try:
            request_start, request_end = parse_us_history_window(
                frequency,
                start_date=start_date,
                end_date=end_date,
                end_day_offset=1,
            )
            response = self.client.get_aggs(
                code.upper(),
                frequency_mult[frequency],
                frequency_map[frequency],
                request_start,
                request_end,
                limit=50000,
            )
            provider_rows = [
                {
                    "timestamp": row.timestamp,
                    "open": row.open,
                    "close": row.close,
                    "high": row.high,
                    "low": row.low,
                    "volume": row.volume,
                }
                for row in response
            ]
            return build_us_history_frame(
                provider_rows,
                code=code,
                frequency=frequency,
                timestamp_unit="ms",
            )
        except Exception as exc:
            print("polygon.io 获取行情异常 %s Exception ：%s" % (code, str(exc)))
            return None

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取股票名称
        """
        all_stocks = self.all_stocks()
        for s in all_stocks:
            if s["code"].upper() == code.upper():
                return s
        return None

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        使用富途的接口获取行情Tick数据
        """
        # ticks = {}
        # for _c in codes:
        #     _t = self.client.get_daily_open_close_agg(_c)
        #     ticks[_c] = Tick(
        #         code=_c, last=_t.close, buy1=_t.close, sell1=_t.close,
        #         high=_t.high, low=_t.low, open=_t.open, volume=_t.volume,
        #         rate=_t.
        #     )
        raise Exception("交易所不支持")

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('us', code=code, at=at)

    def stock_owner_plate(self, code: str):
        raise Exception("交易所不支持")

    def plate_stocks(self, code: str):
        raise Exception("交易所不支持")

    def balance(self):
        raise Exception("交易所不支持")

    def positions(self, code: str = ""):
        raise Exception("交易所不支持")

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangePolygon()

    # is_trading = ex.now_trading(ex.default_code())
    # print(is_trading)

    # klines = ex.klines(ex.default_code(), "30m")
    # print(klines.tail(50))

    # ticks = ex.ticks([ex.default_code()])
    # print(ticks)

    tickers = ex.client.list_tickers(
        type="CS", market="stocks", active=True, limit=1000
    )
    stocks = []
    for t in tickers:
        stocks.append(
            {
                "ticker": t.ticker,
                "exchange": t.primary_exchange,
                "name": t.name,
                "currency": t.currency_name,
                "last_updated": t.last_updated_utc,
            }
        )

    print(stocks)
    print(len(stocks))
