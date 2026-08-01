import datetime
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from tradingview_zy.backtesting.backtest import (
    ANNUALIZATION_DAYS_BY_MARKET,
    BackTest,
    annualization_days_for_market,
)
from tradingview_zy.base import Market


@pytest.mark.parametrize(
    ("market", "expected"),
    [
        (Market.A, 240),
        (Market.HK, 240),
        (Market.US, 240),
        (Market.FUTURES, 240),
        (Market.NY_FUTURES, 240),
        (Market.CURRENCY, 365),
        (Market.CURRENCY_SPOT, 365),
        (Market.FX, 365),
    ],
)
def test_annualization_days_are_explicit_for_every_market(market, expected):
    assert annualization_days_for_market(market) == expected
    assert annualization_days_for_market(market.value) == expected


def test_annualization_mapping_covers_market_enum_exactly():
    assert set(ANNUALIZATION_DAYS_BY_MARKET) == {market.value for market in Market}


def test_unknown_market_fails_instead_of_silently_defaulting():
    with pytest.raises(ValueError, match="不支持的回测市场"):
        annualization_days_for_market("new-market-without-policy")


def _trade_backtest(market: str) -> BackTest:
    base_klines = pd.DataFrame(
        [
            {"date": datetime.datetime(2024, 1, 2), "open": 100.0, "close": 100.0},
            {"date": datetime.datetime(2024, 1, 4), "open": 100.0, "close": 106.0},
        ]
    )
    exchange = SimpleNamespace(klines=lambda *args, **kwargs: base_klines)

    backtest = BackTest()
    backtest.mode = "trade"
    backtest.market = market
    backtest.base_code = "TEST"
    backtest.frequencys = ["d"]
    backtest.start_datetime = datetime.datetime(2024, 1, 2)
    backtest.end_datetime = datetime.datetime(2024, 1, 4)
    backtest.init_balance = 100.0
    backtest.datas = SimpleNamespace(ex=exchange)
    backtest.trader = SimpleNamespace(
        balance_history={
            "2024-01-02 15:00:00": 100.0,
            "2024-01-03 15:00:00": 90.0,
            "2024-01-04 15:00:00": 110.0,
        },
        fee_total=0.0,
        results={},
    )
    return backtest


@pytest.mark.parametrize(
    ("market", "annual_days"),
    [("hk", 240), ("futures", 240), ("ny_futures", 240), ("currency", 365)],
)
def test_result_uses_market_annualization_for_account_and_benchmark(market, annual_days):
    result = _trade_backtest(market).result(is_print=False)

    assert result["annual_return"] == pytest.approx(10.0 / 3 * annual_days)
    assert result["base_annual_return"] == pytest.approx(6.0 / 3 * annual_days)

    # BackTest.result() computes period returns in decimal units. The annual
    # risk-free rate must therefore be converted to one period by compounding,
    # rather than mixed into percentage units or divided by sqrt(N).
    period_returns = pd.Series([0.0, 0.9 - 1.0, 110.0 / 90.0 - 1.0])
    period_risk_free = (1.0 + 0.03) ** (1.0 / annual_days) - 1.0
    expected_sharpe = (
        (period_returns.mean() - period_risk_free)
        / period_returns.std()
        * np.sqrt(annual_days)
    )
    assert result["sharpe_ratio"] == pytest.approx(expected_sharpe)
