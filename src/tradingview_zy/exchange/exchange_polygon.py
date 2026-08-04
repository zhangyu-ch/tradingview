"""US equity market data backed by Polygon."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from polygon.rest import RESTClient

from tradingview_zy import config, fun
from tradingview_zy.domain import InvalidRequestError, UnsupportedCapabilityError
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.provider_observability import call_provider
from tradingview_zy.exchange.us_history import build_us_history_frame, parse_us_history_window
from tradingview_zy.secret_store import resolve_config_secret
from tradingview_zy.trading_calendar import is_market_open

LOGGER = logging.getLogger(__name__)


@fun.singleton
class ExchangePolygon(Exchange):
    """US equity market-data adapter backed by Polygon."""

    _all_stocks_cache: list[dict[str, str]] = []

    def __init__(self) -> None:
        super().__init__()
        self.client = RESTClient(
            resolve_config_secret(config, "POLYGON_APIKEY", required=True)
        )

    def default_code(self) -> str:
        return "AAPL"

    def support_frequencys(self) -> dict[str, str]:
        return {
            "y": "Year", "q": "Quarter", "m": "Month", "w": "Week", "d": "Day",
            "120m": "2H", "60m": "1H", "30m": "30m", "15m": "15m", "5m": "5m", "1m": "1m",
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
        frequency_units = {
            "y": (1, "year"), "q": (1, "quarter"), "m": (1, "month"),
            "w": (1, "week"), "d": (1, "day"), "120m": (2, "hour"),
            "60m": (1, "hour"), "30m": (30, "minute"), "15m": (15, "minute"),
            "5m": (5, "minute"), "1m": (1, "minute"),
        }
        if frequency not in frequency_units:
            raise InvalidRequestError(f"Polygon 不支持周期 {frequency!r}", provider="polygon")

        request_start, request_end = parse_us_history_window(
            frequency,
            start_date=start_date,
            end_date=end_date,
            end_day_offset=1,
        )
        multiplier, timespan = frequency_units[frequency]
        response = call_provider(
            lambda: self.client.get_aggs(
                code.upper(),
                multiplier,
                timespan,
                request_start,
                request_end,
                limit=50000,
            ),
            logger=LOGGER,
            provider="polygon",
            market="us",
            code=code,
            operation_name="get_aggs",
            request_id=request_args.get("request_id"),
        )
        provider_rows = [
            {
                "timestamp": aggregate.timestamp,
                "open": aggregate.open,
                "close": aggregate.close,
                "high": aggregate.high,
                "low": aggregate.low,
                "volume": aggregate.volume,
            }
            for aggregate in response
        ]
        return build_us_history_frame(
            provider_rows,
            code=code,
            frequency=frequency,
            timestamp_unit="ms",
        )

    def stock_info(self, code: str) -> dict[str, str] | None:
        normalized_code = code.upper()
        return next(
            (stock for stock in self.all_stocks() if stock["code"].upper() == normalized_code),
            None,
        )

    def now_trading(self, code: str | None = None, at=None) -> bool:
        return is_market_open("us", code=code, at=at)

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)
