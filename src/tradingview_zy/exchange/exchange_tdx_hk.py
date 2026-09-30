import datetime
import time
from typing import Dict, List, Union

import akshare as ak
import pandas as pd
import pytz
from pytdx.errors import TdxConnectionError
from pytdx.exhq import TdxExHq_API

from tradingview_zy import fun
from tradingview_zy.base import Market
from tradingview_zy.domain import InvalidRequestError, ProviderUnavailableError
from tradingview_zy.config import get_data_path
from tradingview_zy.db import db
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.tdx_quotes import calculate_change_rate
from tradingview_zy.exchange.tdx_cache import refresh_tdx_window, tdx_cache_key
from tradingview_zy.file_db import FileCacheDB
from tradingview_zy.exchange.adjustment_reliability import fetch_adjustment_factors
from tradingview_zy.exchange.tdx_reliability import (
    TdxExHqLifecycleMixin,
    call_with_bounded_retry,
    remaining_request_seconds,
    tdx_kline_connection,
)
from tradingview_zy.tools import tdx_best_ip as best_ip
from tradingview_zy.tools.tdx_node_selector import NodeSelectionError
from tradingview_zy.trading_calendar import is_market_open


class ExchangeTDXHK(TdxExHqLifecycleMixin, Exchange):
    """
    通达信香港行情接口
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
            description="exchange_tdx_hk",
            market_category=2,
        )

    def default_code(self):
        return "KH.00700"

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
            "5m": "5m",
            "1m": "1m",
        }

    def all_stocks(self):
        """
        使用 通达信的方式获取所有股票代码
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
                    if _i["category"] != 2:
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
        # print(f"香港获取数量：{len(self.g_all_stocks)}")

        return self.g_all_stocks

    def to_tdx_code(self, code):
        """
        转换为 tdx 对应的代码
        """
        code_infos = code.split(".")
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
            args["pages"] = int(args.get("pages", 8))
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

        cache_key = tdx_cache_key(Market.HK.value, code, frequency)

        def fetch_klines(remaining_seconds):
            client = self._new_tdx_client()
            with tdx_kline_connection(client, self.connect_info, remaining_seconds):
                cached = self.fdb.get_tdx_klines(
                    Market.HK.value, cache_key, frequency
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

        klines_df = call_with_bounded_retry(
            fetch_klines,
            recover=lambda: self.reset_tdx_ip(
                deadline_seconds=min(3.0, remaining_request_seconds(deadline)),
            ),
            retry_on=(TdxConnectionError, OSError, NodeSelectionError),
            max_attempts=3,
            deadline_seconds=remaining_request_seconds(deadline),
            description="exchange_tdx_hk klines",
        )
        if klines_df.empty:
            return klines_df

        # 删除重复数据
        klines_df = klines_df.drop_duplicates(["date"], keep="last").sort_values(
            "date"
        )
        self.fdb.save_tdx_klines(Market.HK.value, cache_key, frequency, klines_df)

        klines_df.loc[:, "date"] = klines_df["date"].dt.tz_localize(self.tz)
        klines_df = klines_df.sort_values("date")
        klines_df.loc[:, "code"] = code
        klines_df.loc[:, "volume"] = klines_df["amount"]

        klines_df = klines_df[
            ["code", "date", "open", "close", "high", "low", "volume"]
        ]
        klines_df = self.klines_qfq(code, klines_df, deadline=deadline)
        return klines_df

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取股票名称
        """
        all_stock = self.all_stocks()
        stock = [_s for _s in all_stock if _s["code"] == code]
        if not stock:
            return None
        return {"code": stock[0]["code"], "name": stock[0]["name"]}

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        如果可以使用 富途 的接口，就用 富途的，否则就用 日线的 K线计算
        使用 富途 的接口会很快，日线则很慢
        获取日线的k线，并返回最后一根k线的数据
        """
        ticks = {}
        client = self._new_tdx_client()
        with client.connect(self.connect_info["ip"], self.connect_info["port"]):
            for _code in codes:
                _market, _tdx_code = self.to_tdx_code(_code)
                if _market is None:
                    continue
                _quote = client.get_instrument_quote(_market, _tdx_code)
                # OrderedDict(
                #     [('market', 1), ('code', '00700'), ('pre_close', 362.8000183105469), ('open', 372.20001220703125),
                #      ('high', 374.8000183105469), ('low', 364.4000244140625), ('price', 367.6000061035156),
                #      ('kaicang', 0), ('zongliang', 17784504), ('xianliang', 1189500), ('neipan', 8892299),
                #      ('waipan', 8892205), ('chicang', 0), ('bid1', 0.0), ('bid2', 0.0), ('bid3', 0.0), ('bid4', 0.0),
                #      ('bid5', 0.0), ('bid_vol1', 0), ('bid_vol2', 0), ('bid_vol3', 0), ('bid_vol4', 0), ('bid_vol5', 0),
                #      ('ask1', 0.0), ('ask2', 0.0), ('ask3', 0.0), ('ask4', 0.0), ('ask5', 0.0), ('ask_vol1', 0),
                #      ('ask_vol2', 0), ('ask_vol3', 0), ('ask_vol4', 0), ('ask_vol5', 0)])
                if len(_quote) > 0:
                    _quote = _quote[0]
                    ticks[_code] = Tick(
                        code=_code,
                        last=_quote["price"],
                        buy1=_quote["bid1"],
                        sell1=_quote["ask1"],
                        low=_quote["low"],
                        high=_quote["high"],
                        volume=_quote["zongliang"],
                        open=_quote["open"],
                        rate=(
                            calculate_change_rate(_quote["price"], _quote["pre_close"])
                        ),
                    )
        return ticks

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('hk', code=code, at=at)

    def klines_qfq(self, code: str, klines: pd.DataFrame, *, deadline=None):
        if deadline is None:
            deadline = time.monotonic() + 12.0
        try:
            xdxr_path = get_data_path() / "xdxr"
            if xdxr_path.is_dir() is False:
                xdxr_path.mkdir()
            xdxr_file = xdxr_path / f"hk_qfq_factor_{code.replace('.', '_')}.csv"
            now_day = fun.now_dt("%Y-%m-%d", tz="Asia/Shanghai")
            if (
                xdxr_file.is_file() is False
                or fun.timeint_to_str(
                int(xdxr_file.stat().st_mtime), "%Y-%m-%d", tz="Asia/Shanghai"
            )
                != now_day
            ):
                qfq_factor_df = fetch_adjustment_factors(
                    ak.stock_hk_daily, deadline=deadline, provider="tdx_hk",
                    symbol=code.split(".")[1], adjust="qfq-factor",
                )
                if qfq_factor_df is not None and len(qfq_factor_df) > 0:
                    qfq_factor_df.to_csv(xdxr_file, index=False)
            else:
                qfq_factor_df = pd.read_csv(xdxr_file)

            if qfq_factor_df is None or len(qfq_factor_df) == 0:
                return klines

            qfq_factor_df["qfq_date"] = pd.to_datetime(
                qfq_factor_df["date"]
            ).dt.tz_localize(self.tz)
            qfq_factor_df["qfq_factor"] = qfq_factor_df["qfq_factor"].astype(float)
            qfq_factor_df = qfq_factor_df.drop(columns=["date"])

            # 合并k线与复权因子，进行复权计算
            df = pd.concat([klines, qfq_factor_df], axis=0)
            df["qfq_date"].fillna(df["date"], inplace=True)
            df.sort_values(by="qfq_date", inplace=True)
            df["qfq_factor"].fillna(method="ffill", inplace=True)
            df.dropna(inplace=True)
            df.reset_index(drop=True, inplace=True)

            df["open"] = df["open"] * df["qfq_factor"]
            df["high"] = df["high"] * df["qfq_factor"]
            df["low"] = df["low"] * df["qfq_factor"]
            df["close"] = df["close"] * df["qfq_factor"]
            return df[["code", "date", "open", "high", "low", "close", "volume"]]
        except ProviderUnavailableError:
            raise
        except Exception as e:
            print(f"计算 {code} 复权异常： {e}")
            return klines

    @staticmethod
    def __convert_date(dt: datetime.datetime):
        # 通达信后对其，将日期及以上周期的时间统一设置为 16 点
        return dt.replace(hour=16, minute=0)

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeTDXHK()
    # stocks = ex.all_stocks()
    # print(len(stocks))
    # print(stocks)
    #
    # print(ex.to_tdx_code('KH.00700'))
    #
    klines = ex.klines("KH.09618", "d")
    print(klines.tail(20))

    # ticks = ex.ticks(['KH.00700'])
    # print(ticks)
