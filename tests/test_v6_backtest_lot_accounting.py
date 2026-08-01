from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pytest

from tradingview_zy.backtesting.accounting import (
    LotConsumption,
    close_settlement,
)
from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.base import Operation


def make_trader(*, market: str, mode: str = "signal", balance: float = 1_000.0):
    trader = BackTestTrader(
        "v6-lot-test",
        mode=mode,
        market=market,
        init_balance=balance,
        fee_rate=0,
        max_pos=10,
    )
    data = SimpleNamespace(
        now_date=dt.datetime(2026, 1, 2, 9, 30),
        last_k_info=lambda code: {
            "date": data.now_date,
            "open": 10.0,
            "close": 10.0,
            "high": 10.0,
            "low": 10.0,
        },
    )
    trader.set_data(data)
    return trader, data


def operation(kind: str, key: str, rate: float):
    return Operation(
        code="TEST",
        opt=kind,
        signal="lot",
        key=key,
        pos_rate=rate,
        open_uid="TEST:lot",
        close_uid="clear",
        info={"type": "long"},
    )


def test_rv02_partial_close_releases_cash_and_realises_profit_immediately():
    trader, _ = make_trader(market="currency", mode="trade")
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": 10.0}
    assert trader.execute("TEST", operation("buy", "open", 1.0))
    position = trader.positions["TEST:lot"]
    assert trader.balance == pytest.approx(900.0)

    trader.close_buy = lambda code, pos, opt: {"price": 12.0, "amount": 5.0}
    assert trader.execute("TEST", operation("sell", "half", 0.5), position)
    assert position.amount == pytest.approx(5.0)
    assert position.realized_profit == pytest.approx(10.0)
    assert trader.balance == pytest.approx(960.0)
    assert trader.positions_history == {}

    trader.close_buy = lambda code, pos, opt: {"price": 11.0, "amount": 5.0}
    assert trader.execute("TEST", operation("sell", "rest", 0.5), position)
    assert position.amount == 0.0
    assert position.profit == pytest.approx(15.0)
    assert trader.balance == pytest.approx(1_015.0)
    assert len(trader.positions_history["TEST"]) == 1


def test_rv03_a_share_t1_consumes_only_prior_day_lot():
    trader, data = make_trader(market="a")
    fills = iter(
        [
            {"price": 10.0, "amount": 100.0},
            {"price": 11.0, "amount": 100.0},
        ]
    )
    trader.open_buy = lambda code, opt: next(fills)
    assert trader.execute("TEST", operation("buy", "day1", 0.5))
    data.now_date = dt.datetime(2026, 1, 3, 9, 30)
    assert trader.execute("TEST", operation("buy", "day2", 0.5))
    position = trader.positions["TEST:lot"]
    assert position.amount == 200.0

    # Requesting the whole position on day 2 is clamped to the day-1 lot.
    trader.close_buy = lambda code, pos, opt: {"price": 12.0, "amount": 100.0}
    assert trader.execute("TEST", operation("sell", "day2-close", 1.0), position)
    assert position.amount == 100.0
    assert position.now_pos_rate == pytest.approx(0.5)
    assert len(position.lots) == 1
    assert position.lots[0].opened_at.date() == dt.date(2026, 1, 3)

    data.now_date = dt.datetime(2026, 1, 4, 9, 30)
    trader.close_buy = lambda code, pos, opt: {"price": 12.0, "amount": 100.0}
    assert trader.execute("TEST", operation("sell", "day3-close", 1.0), position)
    assert position.amount == 0.0


def test_futures_short_settlement_uses_short_direction_and_returns_margin_plus_pnl():
    consumption = LotConsumption(
        amount=2.0,
        hold_balance=40.0,  # 10 * 2 * symbol_size 10 * short margin 0.2
        opening_fee=1.0,
        pos_rate=1.0,
        weighted_open_price=10.0,
    )
    cash_delta, realised = close_settlement(
        direction="short",
        consumption=consumption,
        close_price=8.0,
        closing_fee=1.0,
        futures_symbol_size=10.0,
    )
    assert cash_delta == pytest.approx(79.0)  # margin 40 + gross P&L 40 - close fee
    assert realised == pytest.approx(38.0)  # gross 40 - both fees
