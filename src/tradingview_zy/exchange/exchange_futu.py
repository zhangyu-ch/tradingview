from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

import pandas as pd
from futu import (
    AuType,
    KLType,
    OpenQuoteContext,
    OpenSecTradeContext,
    OrderType,
    RET_OK,
    SecurityFirm,
    SecurityType,
    SortField,
    SubType,
    SysConfig,
    TradeDateMarket,
    TrdMarket,
)

from tradingview_zy import config, fun
from tradingview_zy.exchange.exchange import (
    Exchange,
    Tick,
    convert_stock_kline_frequency,
)
from tradingview_zy.exchange.tdx_quotes import calculate_change_rate
from tradingview_zy.futu_context import (
    FutuContextError,
    FutuContextManager,
    FutuOperationError,
)
from tradingview_zy.trading_calendar import is_market_open


LOGGER = logging.getLogger(__name__)


def _expect_sdk_success(result: Any, operation: str, *, values: int = 1) -> tuple[Any, ...]:
    """Convert every Futu RET_ERROR result into the manager failure boundary."""

    if not isinstance(result, tuple) or len(result) < values + 1:
        raise FutuOperationError(f"{operation} returned an invalid response")
    if result[0] != RET_OK:
        raise FutuOperationError(f"{operation} was rejected by Futu OpenD")
    return tuple(result[1 : values + 1])


@fun.singleton
class ExchangeFutu(Exchange):
    """Futu provider with explicit quote/trade context ownership."""

    def __init__(self) -> None:
        SysConfig.set_all_thread_daemon(True)
        self.tz = ZoneInfo("Asia/Shanghai")
        self._cache_lock = threading.RLock()
        self._all_stocks: list[dict[str, Any]] = []
        self._trade_days: dict[str, Any] = {}

        host = str(getattr(config, "FUTU_HOST", "") or "").strip()
        port = int(getattr(config, "FUTU_PORT", 11111))

        def quote_factory() -> OpenQuoteContext:
            return OpenQuoteContext(host=host, port=port, is_encrypt=False)

        def trade_factory() -> OpenSecTradeContext:
            return OpenSecTradeContext(
                filter_trdmarket=TrdMarket.HK,
                host=host,
                port=port,
                security_firm=SecurityFirm.FUTUSECURITIES,
            )

        self._contexts = FutuContextManager(
            enabled=bool(host),
            quote_factory=quote_factory,
            trade_factory=trade_factory,
            max_attempts=2,
        )

    def default_code(self) -> str:
        return "HK.00700"

    def support_frequencys(self) -> dict[str, str]:
        return {
            "y": "Year",
            "m": "Month",
            "w": "Week",
            "d": "Day",
            "120m": "2H",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "10m": "10m",
            "5m": "5m",
            "1m": "1m",
        }

    def all_stocks(self) -> list[dict[str, Any]]:
        with self._cache_lock:
            if self._all_stocks:
                return [dict(stock) for stock in self._all_stocks]

        try:
            data = self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_plate_stock("HK.BK1910"), "get_plate_stock"
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu all_stocks unavailable: %s", type(error).__name__)
            return []

        stocks = [
            {"code": row[1]["code"], "name": row[1]["stock_name"]}
            for row in data.iterrows()
        ]
        with self._cache_lock:
            self._all_stocks = [dict(stock) for stock in stocks]
            return [dict(stock) for stock in self._all_stocks]

    @staticmethod
    def _frequency_map() -> dict[str, dict[str, Any]]:
        return {
            "1m": {"ktype": KLType.K_1M, "subtype": SubType.K_1M},
            "5m": {"ktype": KLType.K_5M, "subtype": SubType.K_5M},
            "10m": {"ktype": KLType.K_5M, "subtype": SubType.K_5M},
            "15m": {"ktype": KLType.K_15M, "subtype": SubType.K_15M},
            "30m": {"ktype": KLType.K_30M, "subtype": SubType.K_30M},
            "60m": {"ktype": KLType.K_60M, "subtype": SubType.K_60M},
            "120m": {"ktype": KLType.K_60M, "subtype": SubType.K_60M},
            "d": {"ktype": KLType.K_DAY, "subtype": SubType.K_DAY},
            "w": {"ktype": KLType.K_WEEK, "subtype": SubType.K_WEEK},
            "m": {"ktype": KLType.K_MON, "subtype": SubType.K_MON},
            "y": {"ktype": KLType.K_YEAR, "subtype": SubType.K_YEAR},
        }

    @staticmethod
    def _derive_start_date(frequency: str, end_date: str) -> str | None:
        time_format = "%Y-%m-%d" if len(end_date) == 10 else "%Y-%m-%d %H:%M:%S"
        end_datetime = dt.datetime(*time.strptime(end_date, time_format)[:6])
        lookback_days = {
            "1m": 5,
            "5m": 25,
            "10m": 25,
            "15m": 75,
            "30m": 150,
            "60m": 300,
            "120m": 600,
            "d": 1500,
            "w": 2500,
            "m": 5000,
            "y": 8000,
        }.get(frequency)
        if lookback_days is None:
            return None
        return (end_datetime - dt.timedelta(days=lookback_days)).strftime(time_format)

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> pd.DataFrame | None:
        frequency_map = self._frequency_map()
        if frequency not in frequency_map:
            raise ValueError(f"unsupported Futu frequency: {frequency!r}")
        options = dict(args or {})
        is_history = bool(options.get("is_history", False))
        autype = options.get("fq", AuType.QFQ)
        if start_date is None and end_date is not None:
            start_date = self._derive_start_date(frequency, end_date)

        def request(context: OpenQuoteContext) -> pd.DataFrame:
            if start_date is None and end_date is None and not is_history:
                _expect_sdk_success(
                    context.subscribe(
                        [code],
                        [frequency_map[frequency]["subtype"]],
                        is_first_push=False,
                        subscribe_push=False,
                    ),
                    "subscribe",
                )
                return _expect_sdk_success(
                    context.get_cur_kline(
                        code, 1000, frequency_map[frequency]["subtype"], autype
                    ),
                    "get_cur_kline",
                )[0]

            return _expect_sdk_success(
                context.request_history_kline(
                    code=code,
                    start=start_date,
                    end=end_date,
                    max_count=None,
                    ktype=frequency_map[frequency]["ktype"],
                    autype=autype,
                ),
                "request_history_kline",
                values=2,
            )[0]

        try:
            kline = self._contexts.run_quote(request)
            if not isinstance(kline, pd.DataFrame):
                raise FutuOperationError("Futu kline payload is not a DataFrame")
            required = {"code", "time_key", "open", "close", "high", "low", "volume"}
            missing = sorted(required - set(kline.columns))
            if missing:
                raise FutuOperationError(
                    f"Futu kline payload is missing required fields: {', '.join(missing)}"
                )
            kline = kline.copy(deep=True)
            kline["date"] = pd.to_datetime(kline["time_key"], errors="raise").dt.tz_localize(
                self.tz
            )
            kline["date"] = kline["date"].apply(self._convert_date)
            kline = kline[["code", "date", "open", "close", "high", "low", "volume"]]
            if frequency in {"120m", "10m"} and not kline.empty:
                kline = convert_stock_kline_frequency(kline, frequency)
            return kline
        except (FutuContextError, KeyError, TypeError, ValueError) as error:
            LOGGER.warning(
                "Futu kline request unavailable for %s/%s: %s",
                code,
                frequency,
                type(error).__name__,
            )
            return None

    @staticmethod
    def _convert_date(value: pd.Timestamp) -> pd.Timestamp:
        if value.hour == 0 and value.minute == 0 and value.second == 0:
            return value.replace(hour=16, minute=0)
        return value

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        try:
            data = self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_market_snapshot(list(codes)), "get_market_snapshot"
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu ticks unavailable: %s", type(error).__name__)
            return {}

        return {
            row[1]["code"]: Tick(
                code=row[1]["code"],
                last=row[1]["last_price"],
                high=row[1]["high_price"],
                low=row[1]["low_price"],
                open=row[1]["open_price"],
                volume=row[1]["volume"],
                buy1=row[1]["bid_price"],
                sell1=row[1]["ask_price"],
                rate=calculate_change_rate(
                    row[1]["last_price"], row[1]["prev_close_price"]
                ),
            )
            for row in data.iterrows()
        }

    def stock_info(self, code: str) -> Dict[str, Any] | None:
        try:
            data = self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_stock_basicinfo(None, SecurityType.STOCK, [code]),
                    "get_stock_basicinfo",
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu stock_info unavailable: %s", type(error).__name__)
            return None
        if data.empty:
            return None
        return {
            "code": data.iloc[0]["code"],
            "name": data.iloc[0]["name"],
            "lot_size": data.iloc[0]["lot_size"],
            "stock_type": data.iloc[0]["stock_type"],
        }

    def market_trade_days(self, market: str):
        market_map = {"hk": TradeDateMarket.HK, "cn": TradeDateMarket.CN}
        if market not in market_map:
            raise ValueError(f"unsupported Futu market: {market!r}")
        try:
            return self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.request_trading_days(
                        market=market_map[market], start=time.strftime("%Y-%m-%d")
                    ),
                    "request_trading_days",
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu trading days unavailable: %s", type(error).__name__)
            return None

    @staticmethod
    def _calendar_market_for_code(code: str | None) -> str | None:
        if not isinstance(code, str) or not code.strip():
            return None
        prefix = code.strip().split(".", 1)[0].upper()
        if prefix in {"SH", "SZ", "BJ"}:
            return "a"
        if prefix == "HK":
            return "hk"
        return None

    def now_trading(self, code: str | None = None, at=None) -> bool:
        market = self._calendar_market_for_code(code)
        if market is None:
            return False
        return is_market_open(market, code=code, at=at)

    def query_kline_edu(self):
        try:
            return self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_history_kl_quota(get_detail=False),
                    "get_history_kl_quota",
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu kline quota unavailable: %s", type(error).__name__)
            return None

    def stock_owner_plate(self, code: str):
        plate_infos = {"HY": [], "GN": []}
        try:
            data = self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_owner_plate([code]), "get_owner_plate"
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu owner plates unavailable: %s", type(error).__name__)
            return plate_infos

        for row in data.iterrows():
            if row[1]["plate_type"] == "INDUSTRY":
                plate_infos["HY"].append(
                    {"code": row[1]["plate_code"], "name": row[1]["plate_name"]}
                )
            elif row[1]["plate_type"] == "CONCEPT":
                plate_infos["GN"].append(
                    {"code": row[1]["plate_code"], "name": row[1]["plate_name"]}
                )
        return plate_infos

    def plate_stocks(self, code: str):
        try:
            data = self._contexts.run_quote(
                lambda context: _expect_sdk_success(
                    context.get_plate_stock(
                        code, sort_field=SortField.CHANGE_RATE, ascend=False
                    ),
                    "get_plate_stock",
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu plate stocks unavailable: %s", type(error).__name__)
            return []
        return [
            {"code": row[1]["code"], "name": row[1]["stock_name"]}
            for row in data.iterrows()
        ]

    def balance(self):
        try:
            account = self._contexts.run_trade(
                lambda context: _expect_sdk_success(
                    context.accinfo_query(), "accinfo_query"
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu balance unavailable: %s", type(error).__name__)
            return None
        if account.empty:
            return None
        return {
            "power": account.iloc[0]["power"],
            "max_power_short": account.iloc[0]["max_power_short"],
            "net_cash_power": account.iloc[0]["net_cash_power"],
            "total_assets": account.iloc[0]["total_assets"],
            "cash": account.iloc[0]["cash"],
            "market_val": account.iloc[0]["market_val"],
            "long_mv": account.iloc[0]["long_mv"],
            "short_mv": account.iloc[0]["short_mv"],
        }

    def positions(self, code: str = ""):
        try:
            positions = self._contexts.run_trade(
                lambda context: _expect_sdk_success(
                    context.position_list_query(code=code), "position_list_query"
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu positions unavailable: %s", type(error).__name__)
            return []
        return [
            {
                "code": row[1]["code"],
                "name": row[1]["stock_name"],
                "type": row[1]["position_side"],
                "amount": row[1]["qty"],
                "can_sell_amount": row[1]["can_sell_qty"],
                "price": row[1]["cost_price"],
                "profit": row[1]["pl_ratio"],
                "profit_val": row[1]["pl_val"],
            }
            for row in positions.iterrows()
            if row[1]["qty"] != 0.0
        ]

    def can_trade_val(self, code: str):
        try:
            data = self._contexts.run_trade(
                lambda context: _expect_sdk_success(
                    context.acctradinginfo_query(
                        order_type=OrderType.MARKET, code=code, price=0
                    ),
                    "acctradinginfo_query",
                )[0]
            )
        except FutuContextError as error:
            LOGGER.warning("Futu trading capacity unavailable: %s", type(error).__name__)
            return None
        if data.empty:
            return None
        return {
            "max_cash_buy": data.iloc[0]["max_cash_buy"],
            "max_margin_buy": data.iloc[0]["max_cash_and_margin_buy"],
            "max_position_sell": data.iloc[0]["max_position_sell"],
            "max_margin_short": data.iloc[0]["max_sell_short"],
            "max_buy_back": data.iloc[0]["max_buy_back"],
        }

    def close(self) -> None:
        self._contexts.close()
        with self._cache_lock:
            self._all_stocks.clear()
            self._trade_days.clear()

    def health(self) -> dict[str, Any]:
        return self._contexts.health()

    def order(self, code, o_type, amount, args=None):
        return super().order(code, o_type, amount, args=args)
