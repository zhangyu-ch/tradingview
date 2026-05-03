import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.base import StrategyContext, StrategySignal


class FakeExchange:
    def __init__(self):
        self.requested = []

    def klines(self, code, frequency):
        self.requested.append((code, frequency))
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-05-03 09:30:00"),
                    "frequency": frequency,
                    "code": code,
                    "open": 10.0,
                    "close": 11.0,
                    "high": 11.5,
                    "low": 9.8,
                    "volume": 1000,
                }
            ]
        )


class PositiveCloseStrategy:
    name = "positive_close"

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) > float(last["open"]):
            return [
                StrategySignal(
                    code=context.code,
                    name=context.name,
                    action="select",
                    score=1.0,
                    message="close > open",
                    frequency=context.frequency,
                    event_time=context.now,
                )
            ]
        return []


def test_selection_runner_uses_plain_klines_only():
    exchange = FakeExchange()
    runner = SelectionRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    results = runner.run(
        market="a",
        stocks=[{"code": "SH.000001", "name": "上证指数"}],
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert exchange.requested == [("SH.000001", "d")]
    assert results[0].code == "SH.000001"
    assert results[0].message == "close > open"


def test_monitoring_runner_returns_events_without_chanlun_data():
    exchange = FakeExchange()
    runner = MonitoringRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    events = runner.run_code(
        market="a",
        code="SH.000001",
        name="上证指数",
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert len(events) == 1
    assert events[0].action == "select"
    assert events[0].frequency == "d"
