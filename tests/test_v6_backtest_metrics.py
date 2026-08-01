import math

import numpy as np
import pytest

from tradingview_zy.backtesting.metrics import (
    annual_to_period_rate,
    safe_return_drawdown_ratio,
    safe_sharpe_ratio,
)


def test_sharpe_uses_decimal_returns_and_compounded_period_risk_free_rate():
    returns = np.array([0.01, -0.005, 0.02, 0.0])
    periods = 240
    annual_rf = 0.03
    period_rf = (1 + annual_rf) ** (1 / periods) - 1
    expected = (returns.mean() - period_rf) / returns.std(ddof=1) * math.sqrt(periods)
    assert safe_sharpe_ratio(returns, annual_periods=periods, annual_risk_free_rate=annual_rf) == pytest.approx(expected)
    assert annual_to_period_rate(annual_rf, periods) == pytest.approx(period_rf)


def test_degenerate_metrics_are_finite_and_do_not_emit_infinity():
    assert safe_sharpe_ratio([0.0, 0.0], annual_periods=240) == 0.0
    assert safe_return_drawdown_ratio(0.25, 0.0) == 0.0
    assert safe_return_drawdown_ratio(float("inf"), 0.1) == 0.0
    assert math.isfinite(safe_return_drawdown_ratio(0.25, -0.05))
