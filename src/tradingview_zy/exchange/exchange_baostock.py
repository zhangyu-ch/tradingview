from typing import Union

import baostock as bs
from tradingview_zy import fun
from tradingview_zy.exchange.baostock_reliability import (
    BaostockQueryError,
    BaostockUnavailableError,
    call_baostock_query,
    parse_baostock_datetime,
    recent_weekdays,
    require_successful_login,
)

from tradingview_zy.exchange.exchange import *
from tradingview_zy.trading_calendar import is_market_open


def market_date(tz) -> datetime.date:
    """Return the current market-local date; split out for deterministic tests."""

    return datetime.datetime.now(tz).date()


@fun.singleton
class ExchangeBaostock(Exchange):
    """
    Baostock 行情接口服务，非实时
    使用 baostock API 实现 : http://baostock.com/baostock/index.php/%E9%A6%96%E9%A1%B5
    """

    QUERY_MAX_ATTEMPTS = 3
    QUERY_DEADLINE_SECONDS = 8.0
    CATALOG_LOOKBACK_DAYS = 20

    def __init__(self):
        require_successful_login(bs.login())

        # 设置时区
        self.tz = pytz.timezone("Asia/Shanghai")
        self.g_all_stocks: list[dict] = []
        self._catalog_checked_on: datetime.date | None = None
        self._catalog_source_day: datetime.date | None = None

    def _query(self, query, *, operation: str):
        return call_baostock_query(
            query,
            bs.login,
            operation=operation,
            max_attempts=self.QUERY_MAX_ATTEMPTS,
            deadline_seconds=self.QUERY_DEADLINE_SECONDS,
        )

    @staticmethod
    def _result_rows(result) -> list[list[str]]:
        rows: list[list[str]] = []
        while result.error_code == "0" and result.next():
            rows.append(result.get_row_data())
        return rows

    def _catalog_days(self, as_of: datetime.date) -> list[datetime.date]:
        """Get newest trading days, with a finite weekday fallback."""

        start = as_of - datetime.timedelta(days=self.CATALOG_LOOKBACK_DAYS)
        try:
            result = self._query(
                lambda: bs.query_trade_dates(
                    start_date=start.isoformat(), end_date=as_of.isoformat()
                ),
                operation="query_trade_dates",
            )
            fields = [str(field) for field in result.fields]
            date_index = fields.index("calendar_date") if "calendar_date" in fields else 0
            trading_index = (
                fields.index("is_trading_day") if "is_trading_day" in fields else 1
            )
            days: set[datetime.date] = set()
            for row in self._result_rows(result):
                if len(row) <= max(date_index, trading_index):
                    continue
                if str(row[trading_index]).strip() != "1":
                    continue
                try:
                    candidate = datetime.date.fromisoformat(str(row[date_index]).strip())
                except ValueError:
                    continue
                if candidate <= as_of:
                    days.add(candidate)
            if days:
                return sorted(days, reverse=True)
        except (AttributeError, BaostockQueryError):
            # Older SDKs or a temporarily unavailable calendar endpoint still get
            # a finite, auditable fallback instead of a fixed historical date.
            pass

        return recent_weekdays(as_of, lookback_days=self.CATALOG_LOOKBACK_DAYS)

    @staticmethod
    def _catalog_rows_to_stocks(result) -> list[dict]:
        fields = [str(field) for field in result.fields]
        code_index = fields.index("code") if "code" in fields else 0
        name_index = fields.index("code_name") if "code_name" in fields else 2
        stocks: list[dict] = []
        for row in ExchangeBaostock._result_rows(result):
            if len(row) <= max(code_index, name_index):
                continue
            code = str(row[code_index]).strip()
            name = str(row[name_index]).strip()
            if not code or code[:6] in ["sz.399", "sh.000"]:
                continue
            stocks.append({"code": code, "name": name or code})
        return stocks

    def default_code(self):
        return "SH.000001"

    def support_frequencys(self):
        return {
            "m": "Month",
            "w": "Week",
            "d": "Day",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "5m": "5m",
        }

    def all_stocks(self):
        """
        获取支持的所有股票列表。

        目录按上海市场自然日每日刷新；先查询最近交易日，再在数据尚未
        发布时有限回看更早交易日。成功目录带来源日期缓存，不再永久固定
        在某个历史日期。
        """
        today = market_date(self.tz)
        if self._catalog_checked_on == today and self.g_all_stocks:
            return list(self.g_all_stocks)

        for day in self._catalog_days(today):
            result = self._query(
                lambda day=day: bs.query_all_stock(day=day.isoformat()),
                operation=f"query_all_stock[{day.isoformat()}]",
            )
            stocks = self._catalog_rows_to_stocks(result)
            if not stocks:
                continue
            self.g_all_stocks = stocks
            self._catalog_checked_on = today
            self._catalog_source_day = day
            return list(self.g_all_stocks)

        raise BaostockUnavailableError(
            "BaoStock did not return a stock catalog within the bounded lookback"
        )

    def now_trading(self, code: str | None = None, at=None) -> bool:
        """Return a strict instrument-aware state from the shared calendar."""
        return is_market_open('a', code=code, at=at)

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        """
        获取 Kline 线
        :param code:
        :param frequency:
        :param start_date:
        :param end_date:
        :param args:
        :return:
        """
        args = dict(args or {})
        args.setdefault("fq", "qfq")

        fq_map = {"qfq": "2", "hfq": "1"}
        frequency_map = {
            "m": "m",
            "w": "w",
            "d": "d",
            "60m": "60",
            "30m": "30",
            "15m": "15",
            "5m": "5",
        }
        default_start_day_map = {
            "m": 5000,
            "w": 5000,
            "d": 1000,
            "60m": 200,
            "30m": 100,
            "15m": 60,
            "5m": 20,
        }
        if frequency not in frequency_map:
            raise ValueError("不支持的周期 : " + frequency)
        if args["fq"] not in fq_map:
            raise ValueError("不支持的复权方式 : " + str(args["fq"]))

        minute_frequency = frequency in {"60m", "30m", "15m", "5m"}
        fields = (
            "date,time,code,open,high,low,close,volume"
            if minute_frequency
            else "date,code,open,high,low,close,volume"
        )

        if start_date is None:
            start = market_date(self.tz) - datetime.timedelta(
                days=default_start_day_map[frequency]
            )
            start_date = start.isoformat()

        try:
            result = self._query(
                lambda: bs.query_history_k_data_plus(
                    code,
                    fields,
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency_map[frequency],
                    adjustflag=fq_map[args["fq"]],
                ),
                operation=f"query_history_k_data_plus[{code},{frequency}]",
            )
        except BaostockQueryError as exc:
            print(str(exc))
            return None

        rows = self._result_rows(result)
        if not rows:
            return pd.DataFrame(
                {
                    "code": pd.Series(dtype="object"),
                    "date": pd.Series(pd.DatetimeIndex([], tz=self.tz)),
                    "open": pd.Series(dtype="float64"),
                    "close": pd.Series(dtype="float64"),
                    "high": pd.Series(dtype="float64"),
                    "low": pd.Series(dtype="float64"),
                    "volume": pd.Series(dtype="float64"),
                }
            )

        kline = pd.DataFrame(rows, columns=result.fields)
        if minute_frequency and "time" not in kline.columns:
            raise ValueError("BaoStock minute response is missing the time field")

        if minute_frequency:
            parsed_dates = [
                parse_baostock_datetime(date_value, time_value)
                for date_value, time_value in zip(kline["date"], kline["time"])
            ]
        else:
            parsed_dates = [
                parse_baostock_datetime(date_value) for date_value in kline["date"]
            ]
        kline["date"] = pd.Series(
            pd.DatetimeIndex(parsed_dates).tz_localize(self.tz), index=kline.index
        )

        for field in ["open", "close", "high", "low", "volume"]:
            kline[field] = pd.to_numeric(kline[field], errors="coerce").fillna(0)

        kline = kline.sort_values("date", kind="stable").reset_index(drop=True)
        return kline[["code", "date", "open", "close", "high", "low", "volume"]]

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        获取股票列表的 Tick 信息
        :param codes:
        :return:
        """
        raise Exception("交易所不支持 tick 获取")

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取股票的基本信息
        :param code:
        :return:
        """
        try:
            result = self._query(
                lambda: bs.query_stock_basic(code=code),
                operation=f"query_stock_basic[{code}]",
            )
        except BaostockQueryError:
            return None
        rows = self._result_rows(result)
        if rows:
            return {"code": rows[0][0], "name": rows[0][1]}
        return None

    def stock_owner_plate(self, code: str):
        """
        股票所属板块信息
        :param code:
        :return:
        """
        raise Exception("当前交易所接口不支持")

    def plate_stocks(self, code: str):
        """
        获取板块股票列表信息
        :param code: 板块代码
        :return:
        """
        raise Exception("当前交易所接口不支持")

    def balance(self):
        """
        账户资产信息
        :return:
        """
        raise Exception("账户资产接口不支持")

    def positions(self, code: str = ""):
        """
        当前账户持仓信息
        :param code:
        :return:
        """
        raise Exception("账户资产接口不支持")

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)


if __name__ == "__main__":
    ex = ExchangeBaostock()
    klines = ex.klines("SZ.000001", "d")
    print(klines.tail())
