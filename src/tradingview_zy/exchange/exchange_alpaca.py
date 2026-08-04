from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from alpaca.data import DataFeed, StockBarsRequest, StockSnapshotRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from tradingview_zy import config, fun
from tradingview_zy.domain import InvalidRequestError, UnsupportedCapabilityError
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.provider_observability import call_provider
from tradingview_zy.exchange.tdx_quotes import calculate_change_rate
from tradingview_zy.exchange.us_history import build_us_history_frame, parse_us_history_window
from tradingview_zy.secret_store import resolve_config_secret
from tradingview_zy.trading_calendar import is_market_open

LOGGER = logging.getLogger(__name__)


@fun.singleton
class ExchangeAlpaca(Exchange):
    """US equity market-data adapter backed by Alpaca."""

    _all_stocks_cache: list[dict[str, str]] = []

    def __init__(self) -> None:
        super().__init__()
        self.client = StockHistoricalDataClient(
            api_key=resolve_config_secret(config, "ALPACA_APIKEY", required=True),
            secret_key=resolve_config_secret(config, "ALPACA_SECRET", required=True),
        )
        self.is_vip = False

    def default_code(self) -> str:
        return "AAPL"

    def support_frequencys(self) -> dict[str, str]:
        return {
            "m": "Month", "w": "Week", "d": "Day", "60m": "1H",
            "30m": "30m", "10m": "10m", "15m": "15m", "5m": "5m", "1m": "1m",
        }

    def all_stocks(self) -> list[dict[str, str]]:
        if self._all_stocks_cache:
            return [dict(stock) for stock in self._all_stocks_cache]
        symbols = pd.read_csv(Path(__file__).with_name("us_symbols.csv"))
        self._all_stocks_cache = [
            {"code": str(stock_row.code), "name": str(stock_row.name)}
            for stock_row in symbols.itertuples(index=False)
        ]
        return [dict(stock) for stock in self._all_stocks_cache]

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str | None = None,
        end_date: str | None = None,
        args: dict[str, Any] | None = None,
    ) -> pd.DataFrame | None:
        request_args = dict(args or {})
        frequency_map = {
            "m": TimeFrame.Month,
            "w": TimeFrame.Week,
            "d": TimeFrame.Day,
            "60m": TimeFrame.Hour,
            "30m": TimeFrame(30, TimeFrameUnit.Minute),
            "10m": TimeFrame(10, TimeFrameUnit.Minute),
            "15m": TimeFrame(15, TimeFrameUnit.Minute),
            "5m": TimeFrame(5, TimeFrameUnit.Minute),
            "1m": TimeFrame(1, TimeFrameUnit.Minute),
        }
        if frequency not in frequency_map:
            raise InvalidRequestError(f"Alpaca 不支持周期 {frequency!r}", provider="alpaca")

        request_start, request_end = parse_us_history_window(
            frequency,
            start_date=start_date,
            end_date=end_date,
            end_day_offset=1 if self.is_vip else -1,
        )
        request = StockBarsRequest(
            symbol_or_symbols=code.upper(),
            timeframe=frequency_map[frequency],
            start=request_start,
            end=request_end,
            limit=5000,
        )
        bars = call_provider(
            lambda: self.client.get_stock_bars(request),
            logger=LOGGER,
            provider="alpaca",
            market="us",
            code=code,
            operation_name="get_stock_bars",
            request_id=request_args.get("request_id"),
        )
        provider_rows = [
            {
                "timestamp": bar.timestamp,
                "open": bar.open,
                "close": bar.close,
                "high": bar.high,
                "low": bar.low,
                "volume": bar.volume,
            }
            for bar in bars.data.get(code.upper(), [])
        ]
        return build_us_history_frame(provider_rows, code=code, frequency=frequency)

    def stock_info(self, code: str) -> dict[str, str] | None:
        normalized_code = code.upper()
        return next(
            (stock for stock in self.all_stocks() if stock["code"].upper() == normalized_code),
            None,
        )

    def ticks(self, codes: list[str]) -> dict[str, Tick]:
        request = StockSnapshotRequest(symbol_or_symbols=codes, feed=DataFeed.IEX)

        def fetch_and_normalize() -> dict[str, Tick]:
            snapshots = self.client.get_stock_snapshot(request)
            normalized: dict[str, Tick] = {}
            for symbol_code, snapshot in snapshots.items():
                normalized[symbol_code] = Tick(
                    code=symbol_code,
                    last=snapshot.latest_trade.price,
                    buy1=snapshot.latest_quote.bid_price,
                    sell1=snapshot.latest_quote.ask_price,
                    high=snapshot.daily_bar.high,
                    low=snapshot.daily_bar.low,
                    open=snapshot.daily_bar.open,
                    volume=snapshot.daily_bar.volume,
                    rate=calculate_change_rate(
                        snapshot.daily_bar.close,
                        snapshot.previous_daily_bar.close,
                    ),
                )
            return normalized

        return call_provider(
            fetch_and_normalize,
            logger=LOGGER,
            provider="alpaca",
            market="us",
            code=",".join(codes[:5]),
            operation_name="get_stock_snapshot",
        )

    def now_trading(self, code: str | None = None, at=None) -> bool:
        return is_market_open("us", code=code, at=at)

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)
