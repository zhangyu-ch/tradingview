import datetime
import json
import uuid
from enum import Enum
from typing import Dict, List, Union

import pandas as pd
import pytz
from tenacity import retry, stop_after_attempt, wait_random, retry_if_result

from tradingview_zy import config, fun, rd
from tradingview_zy.exchange.exchange import Exchange, Tick, convert_us_kline_frequency
from tradingview_zy.exchange.ib_rpc import redis_rpc
from tradingview_zy.trading_calendar import is_market_open

ib_res_hkey = "ib_data_results"


class CmdEnum(Enum):
    SEARCH_STOCKS = "ib_search_stocks"
    KLINES = "ib_klines"
    TICKS = "ib_ticks"
    STOCK_INFO = "ib_stock_info"
    BALANCE = "ib_balance"
    POSITIONS = "ib_positions"


@fun.singleton
class ExchangeIB(Exchange):
    def __init__(self):
        self.tz = pytz.timezone("US/Eastern")

        # 缓存，避免重复调用接口
        self.cache = {}
        self.rpc_timeout = float(
            getattr(config, "IB_RPC_TIMEOUT_SECONDS", 30)
        )

    @staticmethod
    def uid():
        return f"{ib_res_hkey}_{str(uuid.uuid4())}"

    def _rpc(self, command: CmdEnum, payload: dict, timeout: float | None = None):
        payload = dict(payload)
        payload.setdefault("key", self.uid())
        return redis_rpc(
            rd.Robj(),
            command.value,
            payload,
            self.rpc_timeout if timeout is None else float(timeout),
        )

    def default_code(self) -> str:
        return "AAPL"

    def support_frequencys(self) -> dict:
        return {
            "m": "Month",
            "w": "Week",
            "d": "Day",
            "60m": "60m",
            "30m": "30m",
            "10m": "10m",
            "15m": "15m",
            "5m": "5m",
            "2m": "2m",
            "1m": "1m",
        }

    def search_stocks(self, search: str):
        """
        补充 获取所有 股票的代码，IB 提供按照关键字进行搜索的接口
        """
        if f"search_stock_{search}" in self.cache.keys():
            return self.cache[f"search_stock_{search}"]

        res = self._rpc(CmdEnum.SEARCH_STOCKS, {"search": search})
        self.cache[f"search_stock_{search}"] = res
        return res

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('us', code=code, at=at)

    @retry(
        stop=stop_after_attempt(2),
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
            "m": "1 month",
            "w": "1 week",
            "d": "1 day",
            "60m": "1 hour",
            "30m": "30 mins",
            "10m": "10 mins",
            "15m": "15 mins",
            "5m": "5 mins",
            "2m": "1 min",
            "1m": "1 min",
        }

        # 控制获取的数量
        duration_map = {
            "m": "30 Y",
            "w": "20 Y",
            "d": "10 Y",
            "60m": "360 D",
            "30m": "100 D",
            "10m": "30 D",
            "15m": "30 D",
            "5m": "15 D",
            "2m": "6 D",
            "1m": "3 D",
        }

        duration = (
            duration_map[frequency]
            if "duration" not in args.keys()
            else args["duration"]
        )
        timeout = 60 if "timeout" not in args.keys() else args["timeout"]

        bars = self._rpc(
            CmdEnum.KLINES,
            {
                "code": code,
                "durationStr": duration,
                "barSizeSetting": frequency_map[frequency],
                "timeout": timeout,
            },
            timeout=timeout,
        )
        klines_df = pd.DataFrame(bars)
        if len(klines_df) > 0:
            klines_df["date"] = pd.to_datetime(klines_df["date"]).dt.tz_localize(
                self.tz
            )

        if len(klines_df) > 0 and frequency in ["2m"]:
            klines_df = convert_us_kline_frequency(klines_df, "2m")

        if len(klines_df) == 0:
            return None

        klines_df["date"] = klines_df["date"].apply(self.__convert_date)

        return klines_df

    @staticmethod
    def __convert_date(dt: datetime.datetime):
        if dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            return dt.replace(hour=9, minute=30)
        return dt

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        ticks = {}
        tks = self._rpc(CmdEnum.TICKS, {"codes": codes})
        for tk in tks:
            if tk is None:
                continue
            ticks[tk["code"]] = Tick(
                code=tk["code"],
                last=tk["last"],
                buy1=tk["buy1"],
                sell1=tk["sell1"],
                open=tk["open"],
                high=tk["high"],
                low=tk["low"],
                volume=tk["volume"],
                rate=tk["rate"],
            )
        return ticks

    def stock_info(self, code: str) -> Union[Dict, None]:
        if f"stock_info_{code}" in self.cache.keys():
            return self.cache[f"stock_info_{code}"]

        res = self._rpc(CmdEnum.STOCK_INFO, {"code": code})
        self.cache[f"stock_info_{code}"] = res
        return res

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random(min=1, max=5),
        retry=retry_if_result(lambda _r: _r is None),
    )
    def balance(self):
        # 获取当前资产
        balance = self._rpc(CmdEnum.BALANCE, {})

        # Demo
        # {
        # 'AccruedCash': 792.27, 'AvailableFunds': 1000694.26, 'BuyingPower': 4002777.02,
        # 'EquityWithLoanValue': 1000784.36, 'ExcessLiquidity': 1000702.45,
        # 'FullAvailableFunds': 1000694.26, 'FullExcessLiquidity': 1000702.45,
        # 'FullInitMarginReq': 90.1, 'FullMaintMarginReq': 81.91, 'GrossPositionValue': 267.7,
        # 'InitMarginReq': 90.1, 'LookAheadAvailableFunds': 1000694.26,
        # 'LookAheadExcessLiquidity': 1000702.45, 'LookAheadInitMarginReq': 90.1,
        # 'LookAheadMaintMarginReq': 81.91, 'MaintMarginReq': 81.91, 'NetLiquidation': 1000784.36,
        # 'SMA': 1000650.51, 'TotalCashValue': 999724.39
        # }
        return balance

    def positions(self, code: str = ""):
        """
        获取当前持仓

        DEMO:
        [{'code': 'NVDA', 'account': '<configured-account>', 'avgCost': 273.93, 'position': 1.0}]
        """
        return self._rpc(CmdEnum.POSITIONS, {"code": code})

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeIB()

    # stock_list = ex.search_stocks("UTHR")
    # print(stock_list)
    #
    # ticks = ex.ticks(["JAPAY"])
    # print(ticks)
    #
    # stock_info = ex.stock_info('DOCU')
    # print(stock_info)
    #
    # klines = ex.klines("NVDA", "60m")
    # print(klines.tail(20))

    # balance = ex.balance()
    # print(balance)

    # #
    # position = ex.positions()
    # print(position)
    # print(len(position))

    # order = ex.order('MSFT', 'buy', 1)
    # print(order)

    stock_info = ex.stock_info('META')
    print(stock_info)

    # res = ex.ib.reqSmartComponents('NASDAQ')
    # print(res)
