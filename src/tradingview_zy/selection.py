from __future__ import annotations

import datetime as dt
from typing import Iterable

from tradingview_zy.strategies.base import StrategyContext, StrategySignal, normalize_strategy_results


class SelectionRunner:
    def __init__(self, exchange, strategy):
        self.exchange = exchange
        self.strategy = strategy

    def run(
        self,
        market: str,
        stocks: Iterable[dict],
        frequency: str,
        now: dt.datetime | None = None,
    ) -> list[StrategySignal]:
        run_time = now or dt.datetime.now()
        results: list[StrategySignal] = []
        for stock in stocks:
            code = stock["code"]
            name = stock.get("name", code)
            klines = self.exchange.klines(code, frequency)
            context = StrategyContext(
                market=market,
                code=code,
                name=name,
                frequency=frequency,
                klines=klines,
                now=run_time,
            )
            results.extend(normalize_strategy_results(self.strategy.run(context)))
        return results
