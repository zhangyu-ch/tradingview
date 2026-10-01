"""Offline SDK-to-adapter contracts; never load private config or open sockets."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest
from alpaca.data import StockBarsRequest
from alpaca.data.models.bars import BarSet
from polygon.rest.models import Agg

import tradingview_zy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["alpaca", "polygon"])
def provider(request, monkeypatch):
    config = ModuleType("tradingview_zy.config")
    monkeypatch.setitem(sys.modules, config.__name__, config)
    monkeypatch.setattr(tradingview_zy, "config", config, raising=False)
    if "tradingview_zy.exchange" not in sys.modules:
        # Do not leave the factory package bound to this temporary configuration.
        package = ModuleType("tradingview_zy.exchange")
        package.__path__ = [str(ROOT / "src/tradingview_zy/exchange")]
        monkeypatch.setitem(sys.modules, package.__name__, package)
        monkeypatch.setattr(tradingview_zy, "exchange", package, raising=False)
    name = request.param
    spec = importlib.util.spec_from_file_location(
        f"test_us_history_{name}",
        ROOT / f"src/tradingview_zy/exchange/exchange_{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    cls = module.ExchangeAlpaca if name == "alpaca" else module.ExchangePolygon
    instance = cls.__new__(cls)  # Client construction resolves credentials, not history.
    instance.is_vip = False
    calls = []

    class AlpacaClient:
        def get_stock_bars(self, request: StockBarsRequest) -> BarSet:
            calls.append(request)
            return self.response

    class PolygonClient:
        def get_aggs(self, ticker, multiplier, timespan, from_, to, *, limit):
            calls.append((ticker, multiplier, timespan, from_, to, limit))
            return self.response

    instance.client = AlpacaClient() if name == "alpaca" else PolygonClient()
    return name, instance, calls


@pytest.mark.parametrize("frequency,day,second_day,utc_hour,expected_dates", [
    ("30m", "2026-07-06", "2026-07-06", 13,
     ["2026-07-06T09:30:00-04:00", "2026-07-06T10:00:00-04:00"]),
    ("d", "2026-01-05", "2026-01-06", 14,
     ["2026-01-05T16:00:00-05:00", "2026-01-06T16:00:00-05:00"]),
])
def test_sdk_history_requests_and_payloads_reach_canonical_bars(
    provider, frequency, day, second_day, utc_hour, expected_dates,
):
    name, exchange, calls = provider
    first = f"{day}T{utc_hour}:30:00Z"
    second = f"{second_day}T{utc_hour + 1}:00:00Z"
    # Out-of-order responses and a corrected duplicate must not lose any fields.
    raw = [
        {"t": second, "o": 30, "c": 32, "h": 35, "l": 28, "v": 300},
        {"t": first, "o": 10, "c": 11, "h": 12, "l": 9, "v": 100},
        {"t": first, "o": 20, "c": 23, "h": 27, "l": 18, "v": 250},
    ]
    if name == "alpaca":
        # Alpaca's actual SDK produces BarSet.data[symbol] of datetime-backed Bar.
        exchange.client.response = BarSet({
            "AAPL": [{**row, "n": 1, "vw": None} for row in raw],
        })
    else:
        # Polygon produces a list of Agg with epoch-millisecond timestamps.
        exchange.client.response = [
            Agg.from_dict({**row, "t": pd.Timestamp(row["t"]).value // 1_000_000})
            for row in raw
        ]

    args = {"request_id": "history-test"}
    output = exchange.klines(
        "aapl", frequency, start_date=f"{day} 09:30:00",
        end_date="2026-07-07" if frequency == "30m" else "2026-01-07", args=args,
    )

    assert args == {"request_id": "history-test"}
    assert output.columns.tolist() == ["code", "date", "open", "close", "high", "low", "volume"]
    assert output.code.tolist() == ["AAPL", "AAPL"]
    assert [value.isoformat() for value in output.date] == expected_dates
    assert str(output.date.dt.tz) == "America/New_York"
    assert output[["open", "close", "high", "low", "volume"]].values.tolist() == [
        [20, 23, 27, 18, 250], [30, 32, 35, 28, 300],
    ]
    assert len(calls) == 1
    end_day = 7
    if name == "alpaca":
        request = calls[0]
        assert isinstance(request, StockBarsRequest)
        assert request.symbol_or_symbols == "AAPL"
        assert request.timeframe.amount_value == (30 if frequency == "30m" else 1)
        assert request.timeframe.unit_value.value == ("Min" if frequency == "30m" else "Day")
        # Alpaca normalizes aware request datetimes to naive UTC in its SDK model.
        assert request.start == datetime.fromisoformat(f"{day}T{utc_hour}:30:00")
        assert request.end == datetime(2026, 7 if frequency == "30m" else 1, end_day, utc_hour - 9)
        assert request.limit == 5000
    else:
        ticker, multiplier, timespan, start, end, limit = calls[0]
        assert (ticker, multiplier, timespan, limit) == (
            "AAPL", 30 if frequency == "30m" else 1,
            "minute" if frequency == "30m" else "day", 50000,
        )
        offset = "-04:00" if frequency == "30m" else "-05:00"
        assert start.isoformat() == f"{day}T09:30:00{offset}"
        assert end.isoformat() == f"2026-{'07' if frequency == '30m' else '01'}-07T00:00:00{offset}"
