from __future__ import annotations

import datetime
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any, Dict, List, Union
from zoneinfo import ZoneInfo

import pandas as pd

from tradingview_zy import fun
from tradingview_zy.exchange.exchange import Exchange, Tick, convert_stock_kline_frequency
from tradingview_zy.exchange.tdx_quotes import calculate_change_rate
from xtquant import xtdata

"""QMT 沪深行情适配器。"""


class QMTError(RuntimeError):
    """Base class for QMT request and provider failures."""


class QMTRequestError(QMTError, ValueError):
    """Raised before any SDK side effect for an invalid request."""


class QMTDataUnavailableError(QMTError):
    """Raised when the SDK returns no response for a requested resource."""


class QMTDataSchemaError(QMTError):
    """Raised when the SDK response violates the documented data contract."""


class ExchangeQMT(Exchange):
    _TIMEZONE = ZoneInfo("Asia/Shanghai")
    _PROJECT_CODE_RE = re.compile(r"^(?P<exchange>SH|SZ|BJ)\.(?P<code>[A-Za-z0-9_@-]{1,32})$")
    _QMT_CODE_RE = re.compile(r"^(?P<code>[A-Za-z0-9_@-]{1,32})\.(?P<exchange>SH|SZ|BJ)$")
    _BASE_PERIODS = {
        "y": "1d",
        "m": "1d",
        "w": "1d",
        "d": "1d",
        "60m": "5m",
        "30m": "5m",
        "15m": "5m",
        "5m": "5m",
        "3m": "1m",
        "1m": "1m",
    }
    _DEFAULT_COUNTS = {
        "y": -1,
        "m": 8000 * 20,
        "w": 8000 * 5,
        "d": 8000,
        "60m": 8000 * 12,
        "30m": 8000 * 6,
        "15m": 8000 * 3,
        "5m": 8000,
        "3m": 8000 * 3,
        "1m": 8000,
    }
    _DIVIDEND_TYPES = {
        "none",
        "front",
        "back",
        "front_ratio",
        "back_ratio",
    }
    _KLINE_COLUMNS = ["code", "date", "open", "high", "low", "close", "volume"]

    def __init__(self):
        xtdata.enable_hello = False
        self.tz = self._TIMEZONE
        self._all_stocks: list[dict[str, Any]] = []

    @classmethod
    def code_to_tdx(cls, code: str) -> str:
        """Normalize either QMT or project code to ``EXCHANGE.CODE``."""
        if not isinstance(code, str):
            raise QMTRequestError("code must be a string")
        value = code.strip().upper()
        project = cls._PROJECT_CODE_RE.fullmatch(value)
        if project:
            return value
        qmt = cls._QMT_CODE_RE.fullmatch(value)
        if qmt:
            return f"{qmt.group('exchange')}.{qmt.group('code')}"
        raise QMTRequestError("code must be SH.CODE/SZ.CODE/BJ.CODE or CODE.SH/CODE.SZ/CODE.BJ")

    @classmethod
    def code_to_qmt(cls, code: str) -> str:
        """Normalize either QMT or project code to ``CODE.EXCHANGE``."""
        project = cls.code_to_tdx(code)
        exchange, instrument = project.split(".", 1)
        return f"{instrument}.{exchange}"

    @staticmethod
    def _copy_catalog(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [dict(item) for item in items]

    @classmethod
    def _validate_frequency(cls, frequency: str) -> str:
        if not isinstance(frequency, str) or frequency not in cls._BASE_PERIODS:
            raise QMTRequestError(f"unsupported QMT frequency: {frequency!r}")
        return cls._BASE_PERIODS[frequency]

    @classmethod
    def _parse_bound(
        cls, value: str | datetime.date | datetime.datetime | pd.Timestamp | None, *, is_end: bool
    ) -> tuple[pd.Timestamp | None, str]:
        if value is None or value == "":
            return None, ""
        if isinstance(value, bool):
            raise QMTRequestError("date boundary must not be boolean")

        date_only = False
        try:
            if isinstance(value, datetime.datetime):
                timestamp = pd.Timestamp(value)
            elif isinstance(value, datetime.date):
                timestamp = pd.Timestamp(value)
                date_only = True
            elif isinstance(value, pd.Timestamp):
                timestamp = value
            elif isinstance(value, str):
                text = value.strip()
                if not text:
                    return None, ""
                date_only = bool(
                    re.fullmatch(r"\d{8}", text)
                    or re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)
                )
                timestamp = pd.Timestamp(text)
            else:
                raise TypeError
        except (TypeError, ValueError, OverflowError) as exc:
            raise QMTRequestError(f"invalid date boundary: {value!r}") from exc

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(cls._TIMEZONE)
        else:
            timestamp = timestamp.tz_convert(cls._TIMEZONE)
        if date_only:
            timestamp = timestamp.normalize()
            if is_end:
                timestamp += pd.Timedelta(hours=23, minutes=59, seconds=59)
        return timestamp, timestamp.strftime("%Y%m%d%H%M%S")

    @classmethod
    def _request_contract(
        cls,
        code: str,
        frequency: str,
        start_date: str | datetime.date | datetime.datetime | pd.Timestamp | None,
        end_date: str | datetime.date | datetime.datetime | pd.Timestamp | None,
        args: dict[str, Any] | None,
    ) -> dict[str, Any]:
        qmt_code = cls.code_to_qmt(code)
        project_code = cls.code_to_tdx(code)
        period = cls._validate_frequency(frequency)
        if args is None:
            options: dict[str, Any] = {}
        elif isinstance(args, dict):
            options = dict(args)
        else:
            raise QMTRequestError("args must be a mapping")

        if start_date in (None, "") and options.get("download_start_date") not in (None, ""):
            start_date = options["download_start_date"]
        if end_date in (None, "") and options.get("download_end_date") not in (None, ""):
            end_date = options["download_end_date"]

        start, start_text = cls._parse_bound(start_date, is_end=False)
        end, end_text = cls._parse_bound(end_date, is_end=True)
        if start is not None and end is not None and start > end:
            raise QMTRequestError("start_date must be before or equal to end_date")

        dividend_type = options.get("dividend_type", "front")
        if not isinstance(dividend_type, str) or dividend_type not in cls._DIVIDEND_TYPES:
            raise QMTRequestError(f"unsupported dividend_type: {dividend_type!r}")

        count = options.get("req_counts", cls._DEFAULT_COUNTS[frequency])
        if isinstance(count, bool) or not isinstance(count, int) or count == 0 or count < -1:
            raise QMTRequestError("req_counts must be -1 or a positive integer")
        if start is not None or end is not None:
            count = -1

        download = options.get("download", False)
        if not isinstance(download, bool):
            raise QMTRequestError("download must be a boolean")
        incrementally = options.get("incrementally", True)
        if not isinstance(incrementally, bool):
            raise QMTRequestError("incrementally must be a boolean")

        return {
            "project_code": project_code,
            "qmt_code": qmt_code,
            "frequency": frequency,
            "period": period,
            "start": start,
            "end": end,
            "start_text": start_text,
            "end_text": end_text,
            "dividend_type": dividend_type,
            "count": count,
            "download": download,
            "incrementally": incrementally,
        }

    @classmethod
    def _empty_klines(cls) -> pd.DataFrame:
        return pd.DataFrame(columns=cls._KLINE_COLUMNS)

    @staticmethod
    def _finite_number(value: Any, field: str, *, nonnegative: bool = False) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise QMTDataSchemaError(f"QMT field {field!r} must be numeric") from exc
        if not math.isfinite(number):
            raise QMTDataSchemaError(f"QMT field {field!r} must be finite")
        if nonnegative and number < 0:
            raise QMTDataSchemaError(f"QMT field {field!r} must be non-negative")
        return number

    @classmethod
    def _normalize_kline_frame(
        cls,
        response: Any,
        request: Mapping[str, Any],
    ) -> pd.DataFrame:
        if response is None:
            raise QMTDataUnavailableError("QMT returned no K-line response")
        if not isinstance(response, Mapping):
            raise QMTDataSchemaError("QMT K-line response must be a code-to-DataFrame mapping")
        qmt_code = request["qmt_code"]
        if qmt_code not in response:
            raise QMTDataUnavailableError(f"QMT response has no data for {qmt_code}")
        source = response[qmt_code]
        if not isinstance(source, pd.DataFrame):
            raise QMTDataSchemaError("QMT K-line value must be a pandas DataFrame")
        if source.empty:
            return cls._empty_klines()

        required = {"time", "open", "high", "low", "close", "volume"}
        missing = sorted(required - set(source.columns))
        if missing:
            raise QMTDataSchemaError(f"QMT K-line response is missing columns: {missing}")

        frame = source.loc[:, ["time", "open", "high", "low", "close", "volume"]].copy()
        for column in ["time", "open", "high", "low", "close", "volume"]:
            try:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
            except (TypeError, ValueError) as exc:
                raise QMTDataSchemaError(f"QMT K-line column {column!r} must be numeric") from exc
        numeric = frame[["time", "open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
        if not math.isfinite(float(numeric.max())) or not math.isfinite(float(numeric.min())):
            raise QMTDataSchemaError("QMT K-line response contains non-finite values")
        if (frame["volume"] < 0).any():
            raise QMTDataSchemaError("QMT K-line volume must be non-negative")
        if (
            (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any()
            or (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any()
        ):
            raise QMTDataSchemaError("QMT K-line OHLC values are inconsistent")

        frame["date"] = pd.to_datetime(frame["time"], unit="ms", utc=True).dt.tz_convert(
            cls._TIMEZONE
        )
        if frame["date"].duplicated().any():
            raise QMTDataSchemaError("QMT K-line response contains duplicate timestamps")
        frame["code"] = request["project_code"]
        frame = frame.loc[:, cls._KLINE_COLUMNS].sort_values("date").reset_index(drop=True)

        start = request["start"]
        end = request["end"]
        if start is not None:
            frame = frame.loc[frame["date"] >= start]
        if end is not None:
            frame = frame.loc[frame["date"] <= end]
        return frame.reset_index(drop=True)

    @classmethod
    def _convert_frequency(cls, frame: pd.DataFrame, frequency: str) -> pd.DataFrame:
        if frame.empty:
            return frame
        if frequency in {"d", "5m", "1m"}:
            result = frame.copy()
        elif frequency == "y":
            indexed = frame.set_index("date")
            grouped = indexed.groupby(indexed.index.year, sort=True)
            rows = []
            for _, group in grouped:
                rows.append(
                    {
                        "code": group["code"].iloc[0],
                        "date": group.index[0].replace(month=1, day=1, hour=15, minute=0, second=0),
                        "open": group["open"].iloc[0],
                        "high": group["high"].max(),
                        "low": group["low"].min(),
                        "close": group["close"].iloc[-1],
                        "volume": group["volume"].sum(),
                    }
                )
            result = pd.DataFrame(rows, columns=cls._KLINE_COLUMNS)
        else:
            result = convert_stock_kline_frequency(frame.copy(), frequency)
            result = result.loc[:, cls._KLINE_COLUMNS]

        if frequency in {"d", "w", "m", "y"} and not result.empty:
            result = result.copy()
            result["date"] = result["date"].dt.normalize() + pd.Timedelta(hours=15)
        return result.sort_values("date").reset_index(drop=True)

    def default_code(self) -> str:
        return "SH.000001"

    def support_frequencys(self) -> dict:
        return {
            "y": "1y",
            "m": "1mon",
            "w": "1w",
            "d": "1d",
            "60m": "1h",
            "30m": "30m",
            "15m": "15m",
            "5m": "5m",
            "1m": "1m",
        }

    def all_stocks(self) -> list[dict[str, Any]]:
        if self._all_stocks:
            return self._copy_catalog(self._all_stocks)
        response = xtdata.get_full_tick(["SH", "SZ", "BJ"])
        if not isinstance(response, Mapping):
            raise QMTDataUnavailableError("QMT returned no security catalogue")

        black_codes = {
            "SZ.399290", "SZ.399289", "SZ.399302", "SZ.399298", "SZ.399481",
            "SZ.399299", "SZ.399301", "SH.000013", "SH.000022", "SH.000116",
            "SH.000061", "SH.000101", "SH.000012", "SZ.988201", "SZ.980068",
            "SZ.980001", "SZ.980023",
        }
        result: list[dict[str, Any]] = []
        for qmt_code in response:
            project_code = self.code_to_tdx(qmt_code)
            instrument_type = xtdata.get_instrument_type(qmt_code)
            if not isinstance(instrument_type, Mapping):
                raise QMTDataSchemaError("QMT instrument type must be a mapping")
            if not any(instrument_type.get(kind) for kind in ("stock", "etf", "index")):
                continue
            if project_code in black_codes:
                continue
            result.append(self.stock_info(project_code))
        self._all_stocks = self._copy_catalog(result)
        return self._copy_catalog(self._all_stocks)

    def download_klines(
        self,
        code: str,
        frequency: str,
        start_date: str | datetime.date | datetime.datetime | pd.Timestamp | None = None,
        end_date: str | datetime.date | datetime.datetime | pd.Timestamp | None = None,
        args: dict[str, Any] | None = None,
    ) -> bool:
        request = self._request_contract(code, frequency, start_date, end_date, args)
        xtdata.download_history_data(
            request["qmt_code"],
            request["period"],
            start_time=request["start_text"],
            end_time=request["end_text"],
            incrementally=request["incrementally"],
        )
        return True

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        request = self._request_contract(code, frequency, start_date, end_date, args)
        if request["download"]:
            self.download_klines(code, frequency, start_date, end_date, args)

        response = xtdata.get_market_data_ex(
            field_list=[],
            stock_list=[request["qmt_code"]],
            period=request["period"],
            start_time=request["start_text"],
            end_time=request["end_text"],
            count=request["count"],
            dividend_type=request["dividend_type"],
            fill_data=False,
        )
        frame = self._normalize_kline_frame(response, request)
        frame = self._convert_frequency(frame, frequency)

        start = request["start"]
        end = request["end"]
        if start is not None:
            frame = frame.loc[frame["date"] >= start]
        if end is not None:
            frame = frame.loc[frame["date"] <= end]
        if request["count"] > 0:
            frame = frame.iloc[-request["count"] :]
        return frame.reset_index(drop=True)

    def stock_info(self, code: str) -> Union[Dict, None]:
        project_code = self.code_to_tdx(code)
        detail = xtdata.get_instrument_detail(self.code_to_qmt(project_code), False)
        if detail is None:
            raise QMTDataUnavailableError(f"QMT returned no instrument detail for {project_code}")
        if not isinstance(detail, Mapping):
            raise QMTDataSchemaError("QMT instrument detail must be a mapping")
        name = detail.get("InstrumentName")
        if not isinstance(name, str) or not name.strip():
            raise QMTDataSchemaError("QMT instrument detail has no InstrumentName")
        price_tick = self._finite_number(detail.get("PriceTick"), "PriceTick")
        if price_tick <= 0:
            raise QMTDataSchemaError("QMT PriceTick must be positive")
        return {
            "code": project_code,
            "name": name.strip(),
            "precision": fun.reverse_decimal_to_power_of_ten(price_tick),
        }

    @classmethod
    def _tick_from_payload(cls, project_code: str, payload: Any) -> Tick:
        if not isinstance(payload, Mapping):
            raise QMTDataSchemaError("QMT tick must be a mapping")
        for field in ("bidPrice", "askPrice"):
            values = payload.get(field)
            if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
                raise QMTDataSchemaError(f"QMT tick {field!r} must contain level 1")
        return Tick(
            code=project_code,
            last=cls._finite_number(payload.get("lastPrice"), "lastPrice"),
            buy1=cls._finite_number(payload["bidPrice"][0], "bidPrice[0]"),
            sell1=cls._finite_number(payload["askPrice"][0], "askPrice[0]"),
            high=cls._finite_number(payload.get("high"), "high"),
            low=cls._finite_number(payload.get("low"), "low"),
            open=cls._finite_number(payload.get("open"), "open"),
            volume=cls._finite_number(payload.get("volume"), "volume", nonnegative=True),
            rate=calculate_change_rate(payload.get("lastPrice"), payload.get("lastClose")),
        )

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        if not isinstance(codes, list):
            raise QMTRequestError("codes must be a list")
        if not codes:
            return {}
        qmt_codes = [self.code_to_qmt(code) for code in codes]
        response = xtdata.get_full_tick(qmt_codes)
        if response is None:
            raise QMTDataUnavailableError("QMT returned no tick response")
        if not isinstance(response, Mapping):
            raise QMTDataSchemaError("QMT tick response must be a mapping")
        result: dict[str, Tick] = {}
        for qmt_code, payload in response.items():
            project_code = self.code_to_tdx(qmt_code)
            result[project_code] = self._tick_from_payload(project_code, payload)
        return result

    def all_ticks(self) -> Dict[str, Tick]:
        allowed = {item["code"] for item in self.all_stocks()}
        response = xtdata.get_full_tick(["SH", "SZ", "BJ"])
        if response is None:
            raise QMTDataUnavailableError("QMT returned no whole-market tick response")
        if not isinstance(response, Mapping):
            raise QMTDataSchemaError("QMT tick response must be a mapping")
        result: dict[str, Tick] = {}
        for qmt_code, payload in response.items():
            project_code = self.code_to_tdx(qmt_code)
            if project_code in allowed:
                result[project_code] = self._tick_from_payload(project_code, payload)
        return result

    def get_divid_factors(self, stock_code: str) -> pd.DataFrame | None:
        project_code = self.code_to_tdx(stock_code)
        frame = xtdata.get_divid_factors(self.code_to_qmt(project_code))
        if frame is None or (isinstance(frame, pd.DataFrame) and frame.empty):
            return None
        if not isinstance(frame, pd.DataFrame) or "time" not in frame.columns:
            raise QMTDataSchemaError("QMT dividend factors must be a DataFrame with time")
        result = frame.copy()
        result.loc[:, "stock_code"] = project_code
        result["divid_date"] = pd.to_datetime(result["time"], unit="ms", utc=True).dt.tz_convert(
            self._TIMEZONE
        )
        return result

    def subscribe_all_ticks(
        self, callback, market_list: List[str] | None = None
    ) -> None:
        if not callable(callback):
            raise QMTRequestError("callback must be callable")
        markets = ["SH", "SZ", "BJ"] if market_list is None else list(market_list)
        allowed = {item["code"] for item in self.all_stocks()}

        def on_tick(values):
            if not isinstance(values, Mapping):
                raise QMTDataSchemaError("QMT subscription payload must be a mapping")
            for qmt_code, payload in values.items():
                project_code = self.code_to_tdx(qmt_code)
                if project_code in allowed:
                    callback(project_code, payload)

        xtdata.subscribe_whole_quote(markets, on_tick)
        xtdata.run()

    def subscribe_stocks_quotes(self, codes: List[str], callback) -> None:
        if not callable(callback):
            raise QMTRequestError("callback must be callable")
        project_codes = [self.code_to_tdx(code) for code in codes]
        qmt_codes = [self.code_to_qmt(code) for code in project_codes]

        def on_tick(values):
            if not isinstance(values, Mapping):
                raise QMTDataSchemaError("QMT subscription payload must be a mapping")
            for qmt_code, payload in values.items():
                project_code = self.code_to_tdx(qmt_code)
                if project_code in project_codes:
                    callback(project_code, payload)

        xtdata.subscribe_whole_quote(qmt_codes, on_tick)
        xtdata.run()

    def now_trading(self):
        """
        返回当前是否是交易时间
        周一至周五，09:30-11:30 13:00-15:00
        """
        now_dt = datetime.datetime.now()
        if now_dt.weekday() in [5, 6]:
            return False
        hour = now_dt.hour
        minute = now_dt.minute
        if hour == 9 and minute >= 30:
            return True
        if hour in [10, 13, 14]:
            return True
        if hour == 11 and minute < 30:
            return True
        return False

    def stock_owner_plate(self, code: str):
        raise Exception("交易所不支持")

    def plate_stocks(self, code: str):
        raise Exception("交易所不支持")

    def balance(self):
        raise Exception("QMT 交易功能在 trader 目录实现")

    def positions(self, code: str = ""):
        raise Exception("QMT 交易功能在 trader 目录实现")

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)
