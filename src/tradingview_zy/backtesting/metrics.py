"""Numerically safe performance metrics for backtest reports."""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def annual_to_period_rate(annual_rate: float, periods: int) -> float:
    if periods <= 0:
        raise ValueError("periods 必须大于 0")
    if annual_rate <= -1:
        raise ValueError("annual_rate 必须大于 -1")
    return (1.0 + float(annual_rate)) ** (1.0 / periods) - 1.0


def safe_sharpe_ratio(
    returns: Iterable[float],
    *,
    annual_periods: int,
    annual_risk_free_rate: float = 0.0,
) -> float:
    """Return annualised Sharpe in decimal-return units.

    A degenerate or insufficient sample returns ``0.0`` instead of ``inf`` or
    ``nan`` so API/JSON output remains finite and deterministic.
    """
    values = np.asarray(list(returns), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return 0.0
    period_rf = annual_to_period_rate(annual_risk_free_rate, annual_periods)
    excess = values - period_rf
    std = float(np.std(values, ddof=1))
    if not math.isfinite(std) or std <= np.finfo(float).eps:
        return 0.0
    value = float(np.mean(excess) / std * math.sqrt(annual_periods))
    return value if math.isfinite(value) else 0.0


def safe_return_drawdown_ratio(total_return: float, max_drawdown: float) -> float:
    total_return = float(total_return)
    max_drawdown = float(max_drawdown)
    if not math.isfinite(total_return) or not math.isfinite(max_drawdown):
        return 0.0
    denominator = abs(max_drawdown)
    if denominator <= np.finfo(float).eps:
        return 0.0
    value = total_return / denominator
    return value if math.isfinite(value) else 0.0


def finite_or_zero(value: float) -> float:
    value = float(value)
    return value if math.isfinite(value) else 0.0
