from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

StrategyAction = Literal["select", "watch", "buy", "sell", "open", "close", "ignore"]


@dataclass(frozen=True)
class StrategyContext:
    market: str
    code: str
    name: str
    frequency: str
    klines: pd.DataFrame
    now: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySignal:
    code: str
    name: str
    action: StrategyAction
    score: float
    message: str
    frequency: str
    event_time: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_strategy_results(results: Any) -> list[StrategySignal]:
    if results is None:
        return []
    if isinstance(results, StrategySignal):
        return [results]
    if isinstance(results, list) and all(isinstance(item, StrategySignal) for item in results):
        return results
    raise TypeError("strategy run() must return StrategySignal, list[StrategySignal], or None")
