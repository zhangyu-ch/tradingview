"""Binance OHLCV workflow only; clients, markets and account APIs stay in providers."""

import datetime
import time
from typing import Union

import pandas as pd

from tradingview_zy.crypto_time import as_utc
from tradingview_zy.domain import InvalidRequestError
from tradingview_zy.exchange.binance_pagination import latest_cached_datetime, paginate_ohlcv
from tradingview_zy.exchange.binance_reliability import fetch_ohlcv_with_retry
from tradingview_zy.exchange.exchange import convert_currency_kline_frequency


_FREQUENCY_MAP = {
    "w": "1w",
    "d": "1d",
    "12h": "12h",
    "8h": "8h",
    "6h": "6h",
    "4h": "4h",
    "3h": "1h",
    "60m": "1h",
    "30m": "30m",
    "15m": "15m",
    "10m": "5m",
    "5m": "5m",
    "3m": "3m",
    "2m": "1m",
    "1m": "1m",
}


def _ohlcv_frame(rows, code, frequency):
    frame = pd.DataFrame(
        rows, columns=["date", "open", "high", "low", "close", "volume"]
    )
    frame["code"] = code
    frame["date"] = frame["date"].apply(
        lambda value: datetime.datetime.fromtimestamp(value / 1e3, datetime.timezone.utc)
    )
    frame = frame[["code", "date", "open", "close", "high", "low", "volume"]]
    if frequency in ["10m", "2m", "3h"] and len(frame) > 0:
        frame = convert_currency_kline_frequency(frame, frequency)
    return frame


class BinanceKlinesMixin:
    """Share history using the provider's own exchange, lock and db_exchange."""

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        """Refresh the database tail, or bypass persistence for use_online."""
        if args is None:
            args = {}

        if "use_online" in args.keys() and args["use_online"]:
            return self.online_klines(code, frequency, start_date, end_date, args)

        db_klines = self.db_exchange.klines(code, frequency, args={"limit": 10000})
        if len(db_klines) == 0:
            online_klines = self.increment_klines_by_online(
                code, frequency, start_date=None
            )
            if online_klines is not None and len(online_klines) > 0:
                self.db_exchange.insert_klines(code, frequency, online_klines)
            return online_klines
        else:
            last_datetime = latest_cached_datetime(db_klines)
            online_klines = self.increment_klines_by_online(
                code, frequency, start_date=last_datetime
            )
            if online_klines is not None and len(online_klines) > 0:
                self.db_exchange.insert_klines(code, frequency, online_klines)
            else:
                return db_klines[-10000::]
        klines = pd.concat([db_klines, online_klines], ignore_index=True)
        # Cache overlap is separate from pagination: online corrections win.
        klines.drop_duplicates(subset=["date"], keep="last", inplace=True)
        klines = klines.sort_values(by="date", ascending=True)
        return klines[-10000::]

    def increment_klines_by_online(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        """Fetch incremental OHLCV data with a strictly advancing cursor."""
        if args is None:
            args = {}
        if frequency not in _FREQUENCY_MAP:
            raise InvalidRequestError(f"不支持的周期: {frequency}")

        start_timestamp = None
        if start_date is not None:
            start_timestamp = int(as_utc(start_date).timestamp() * 1000)

        deadline = time.monotonic() + 12.0

        def fetch_page(params):
            return fetch_ohlcv_with_retry(
                self.exchange, self._ohlcv_lock, deadline=deadline,
                symbol=code,
                timeframe=_FREQUENCY_MAP[frequency],
                limit=1000,
                params=params,
            )

        rows = paginate_ohlcv(
            fetch_page,
            start_ms=start_timestamp,
            page_limit=1000,
            target_count=10000,
            max_pages=int(args.get("max_pages", 100)),
        )
        if not rows:
            return pd.DataFrame([])
        # paginate_ohlcv already sorts and deduplicates timestamps.
        return _ohlcv_frame(rows, code, frequency)

    def online_klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        """Fetch one API window, retaining the optional UTC time bounds."""
        if frequency not in _FREQUENCY_MAP:
            raise InvalidRequestError(f"不支持的周期: {frequency}")

        params = {}
        if start_date is not None:
            params["startTime"] = int(as_utc(start_date).timestamp() * 1000)
        if end_date is not None:
            params["endTime"] = int(as_utc(end_date).timestamp() * 1000)

        rows = fetch_ohlcv_with_retry(
            self.exchange, self._ohlcv_lock, deadline=time.monotonic() + 12.0,
            symbol=code,
            timeframe=_FREQUENCY_MAP[frequency],
            limit=1000,
            params=params,
        )
        return _ohlcv_frame(rows, code, frequency)
