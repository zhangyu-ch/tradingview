from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import Any

from tradingview_zy.strategies.base import (
    BatchRunResult,
    failure_result,
    placeholder_target,
    run_strategy_target,
    strategy_target_from_stock,
    StrategyPurpose,
)


class SelectionRunner:
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
        batch = BatchRunResult()
        try:
            iterator = iter(stocks)
        except Exception as error:
            target = placeholder_target(market, stocks, frequency)
            return failure_result(target, "target", error)

        for stock in iterator:
            try:
                target = strategy_target_from_stock(market, stock, frequency)
            except Exception as error:
                target = placeholder_target(market, stock, frequency)
                batch.extend(failure_result(target, "target", error))
                continue
            batch.extend(
                run_strategy_target(
                    self.exchange,
                    self.strategy,
                    target,
                    purpose=StrategyPurpose.SELECTION,
                    now=now,
                )
            )
        return batch
