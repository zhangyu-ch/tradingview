from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import Any

from tradingview_zy.strategies.base import (
    BatchRunResult,
    run_strategy_batch,
    StrategyPurpose,
)


class MonitoringRunner:
    def __init__(self, exchange: Any, strategy: Any):
        self.exchange = exchange
        self.strategy = strategy

    def run(
        self,
        market: str,
        stocks: Iterable[dict],
        frequency: str,
        now: dt.datetime | None = None,
    ) -> BatchRunResult:
        return run_strategy_batch(
            self.exchange,
            self.strategy,
            market,
            stocks,
            frequency,
            purpose=StrategyPurpose.MONITORING,
            now=now,
        )

    def run_code(
        self,
        market: str,
        code: str,
        name: str,
        frequency: str,
        now: dt.datetime | None = None,
    ) -> BatchRunResult:
        return self.run(
            market=market,
            stocks=[{"code": code, "name": name}],
            frequency=frequency,
            now=now,
        )
