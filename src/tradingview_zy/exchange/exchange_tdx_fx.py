import time
from typing import Dict, List, Union

import pandas as pd
import pytz
from pytdx.errors import TdxConnectionError
from pytdx.exhq import TdxExHq_API

from tradingview_zy.base import Market
from tradingview_zy.domain import InvalidRequestError
from tradingview_zy.db import db
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.tdx_quotes import fetch_exhq_ticks
from tradingview_zy.exchange.tdx_cache import refresh_tdx_window, tdx_cache_key
from tradingview_zy.file_db import FileCacheDB
from tradingview_zy.exchange.tdx_reliability import (
    TdxExHqLifecycleMixin,
    call_with_bounded_retry,
    remaining_request_seconds,
    tdx_kline_connection,
)
from tradingview_zy.tools import tdx_best_ip as best_ip
from tradingview_zy.tools.tdx_node_selector import NodeSelectionError
from tradingview_zy.trading_calendar import is_market_open


class ExchangeTDXFX(TdxExHqLifecycleMixin, Exchange):
    """
    通达信外汇行情接口
    """

    g_all_stocks = []

    def __init__(self):
        # 设置时区
        self.tz = pytz.timezone("Asia/Shanghai")

        # 文件缓存
        self.fdb = FileCacheDB()

        self._initialize_tdx_exhq(
            cache_backend=db,
            selector=best_ip,
            client_factory=TdxExHq_API,
            connection_errors=(TdxConnectionError,),
            description="exchange_tdx_fx",
            market_category=4,
            client_kwargs={"multithread": True},
        )

    def default_code(self):
        return "FX.USDEUR"

    def support_frequencys(self):
        return {
            "y": "Y",
            "q": "Q",
            "m": "M",
            "w": "W",
            "d": "D",
            "60m": "60m",
            "30m": "30m",
            "15m": "15m",
            "10m": "10m",
            "5m": "5m",
            "1m": "1m",
        }

    def all_stocks(self):
        """
        使用 通达信的方式获取所有外汇代码
        """
        if len(self.g_all_stocks) > 0:
            return self.g_all_stocks

        __all_stocks = []
        client = self._new_tdx_client()
        with client.connect(self.connect_info["ip"], self.connect_info["port"]):
            start_i = 0
            count = 1000
            market_map_short_names = {
                _m_i["market"]: _m_s for _m_s, _m_i in self.market_maps.items()
            }
            while True:
                instruments = client.get_instrument_info(start_i, count)
                for _i in instruments:
                    if (
                        _i["category"] != 4
                        or _i["market"] not in market_map_short_names.keys()
                    ):
                        continue

                    __all_stocks.append(
                        {
                            "code": f"{market_map_short_names[_i['market']]}.{_i['code']}",
                            "name": _i["name"],
                        }
                    )
                start_i += count
                if len(instruments) < count:
                    break

        self.g_all_stocks = __all_stocks
        # print(f"获取数量：{len(self.g_all_stocks)}")

        return self.g_all_stocks

    def to_tdx_code(self, code):
        """
        转换为 tdx 对应的代码
        """
        code_str = str(code)
        code_infos = code_str.split(".")
        market_info = self.market_maps[code_infos[0]]
        return market_info["market"], code_infos[1]

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> pd.DataFrame:
        """
        通达信，不支持按照时间查找
        """
        deadline = time.monotonic() + 12.0
        args = dict(args or {})
        try:
            args["pages"] = int(args.get("pages", 10))
        except (TypeError, ValueError) as error:
            raise InvalidRequestError("TDX pages 必须是正整数") from error
        if args["pages"] < 1:
            raise InvalidRequestError("TDX pages 必须是正整数")

        frequency_map = {
            "y": 11,
            "q": 10,
            "m": 6,
            "w": 5,
            "d": 9,
            "60m": 3,
            "30m": 2,
            "15m": 1,
            "10m": 0,
            "5m": 0,
            "1m": 8,
        }
        if frequency not in frequency_map:
            raise InvalidRequestError(f"TDX 不支持周期 {frequency!r}")
        if start_date is not None or end_date is not None:
            raise InvalidRequestError("TDX 不支持按起止时间查询")
        if not isinstance(code, str) or not code.strip():
            raise InvalidRequestError("TDX 代码不能为空")
        if "." not in code or not all(code.split(".", 1)):
            raise InvalidRequestError("TDX 代码应为 市场.合约")
        try:
            market, tdx_code = self.to_tdx_code(code)
        except KeyError:
            return pd.DataFrame([])
        if market is None:
            return pd.DataFrame([])

        cache_key = tdx_cache_key(Market.FX.value, code, frequency)

        def fetch_klines(remaining_seconds):
            client = self._new_tdx_client()
            with tdx_kline_connection(client, self.connect_info, remaining_seconds):
                cached = self.fdb.get_tdx_klines(
                    Market.FX.value, cache_key, frequency
                )

                def normalize_page(page):
                    page["date"] = pd.to_datetime(page["datetime"])
                    return page

                return refresh_tdx_window(
                    cached,
                    lambda page_index: client.to_df(
                        client.get_instrument_bars(
                            frequency_map[frequency], market, tdx_code,
                            page_index * 700, 700,
                        )
                    ),
                    normalize_page,
                    args["pages"],
                )

        klines = call_with_bounded_retry(
            fetch_klines,
            recover=lambda: self.reset_tdx_ip(
                deadline_seconds=min(3.0, remaining_request_seconds(deadline)),
            ),
            retry_on=(TdxConnectionError, OSError, NodeSelectionError),
            max_attempts=3,
            deadline_seconds=remaining_request_seconds(deadline),
            description="exchange_tdx_fx klines",
        )
        if klines.empty:
            return klines

        self.fdb.save_tdx_klines(Market.FX.value, cache_key, frequency, klines)

        klines.loc[:, "code"] = code
        klines.loc[:, "volume"] = klines["trade"]
        klines.loc[:, "date"] = pd.to_datetime(klines["datetime"]).dt.tz_localize(
            self.tz
        )

        # 将 volume 转换成 float类型
        klines[["volume"]] = klines[["volume"]].astype(float)

        return klines[["code", "date", "open", "close", "high", "low", "volume"]]

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取标的名称
        """
        all_stock = self.all_stocks()
        stock = [_s for _s in all_stock if _s["code"] == code]
        if not stock:
            return None
        return {"code": stock[0]["code"], "name": stock[0]["name"]}

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        return fetch_exhq_ticks(
            self._new_tdx_client(), self.connect_info, self.to_tdx_code, codes
        )

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('fx', code=code, at=at)

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeTDXFX()
    stocks = ex.all_stocks()
    print(len(stocks))
    print(stocks)
    # print(ex.market_maps)

    klines = ex.klines("FX.GBPEUR", "1m", args={"pages": 10})
    print(len(klines))
    print(klines)
