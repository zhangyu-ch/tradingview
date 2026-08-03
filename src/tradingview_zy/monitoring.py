from __future__ import annotations

import datetime as dt

from tradingview_zy.strategies.base import StrategyContext, StrategySignal, normalize_strategy_results


class MonitoringRunner:
    def __init__(self, exchange, strategy):
        self.exchange = exchange
        self.strategy = strategy

    def run_code(
        self,
        market: str,
        code: str,
        name: str,
        frequency: str,
        now: dt.datetime | None = None,
    ) -> list[StrategySignal]:
        run_time = now or dt.datetime.now()
        klines = self.exchange.klines(code, frequency)
        context = StrategyContext(
            market=market,
            code=code,
            name=name,
            frequency=frequency,
            klines=klines,
            now=run_time,
        )
        return normalize_strategy_results(self.strategy.run(context))
