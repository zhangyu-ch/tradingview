import datetime
from types import SimpleNamespace

import pytest

from tradingview_zy.backtesting.accounting import (
    BackTestAccountingError,
    subtract_quantity,
    weighted_average_price,
)
from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.base import Operation


FUTURES_CONFIG = {
    "symbol_size": 1,
    "margin_rate_long": 0.1,
    "margin_rate_short": 0.2,
    "fee_rate_open": 0,
    "fee_rate_close": 0,
    "fee_rate_close_today": 0,
}


def make_trader(market="currency"):
    trader = BackTestTrader(
        "accounting-test",
        mode="signal",
        market=market,
        init_balance=1_000_000,
        fee_rate=0,
        max_pos=10,
    )
    trader.set_data(
        SimpleNamespace(
            now_date=datetime.datetime(2024, 1, 2, 9, 30),
            last_k_info=lambda code: {
                "date": datetime.datetime(2024, 1, 2, 9, 30),
                "open": 10.0,
                "close": 10.0,
                "high": 10.0,
                "low": 10.0,
            },
        )
    )
    if market == "futures":
        trader.futures_contracts = {"TEST": FUTURES_CONFIG}
    return trader


def open_operation(*, key, rate, direction="long", code="TEST"):
    return Operation(
        code=code,
        opt="buy",
        signal="breakout",
        key=key,
        pos_rate=rate,
        open_uid=f"{code}:breakout",
        info={"type": direction},
    )


def close_operation(*, key, rate, code="TEST"):
    return Operation(
        code=code,
        opt="sell",
        signal="breakout",
        key=key,
        pos_rate=rate,
        open_uid=f"{code}:breakout",
        close_uid="clear",
        msg="test close",
    )


@pytest.mark.parametrize(
    ("market", "direction", "fill_method"),
    [
        ("currency", "long", "open_buy"),
        ("currency", "short", "open_sell"),
        ("futures", "long", "open_buy"),
        ("futures", "short", "open_sell"),
    ],
)
def test_incremental_open_uses_volume_weighted_average_price(
    market, direction, fill_method
):
    trader = make_trader(market)
    fills = iter(
        [
            {"price": 10.0, "amount": 2.0},
            {"price": 20.0, "amount": 3.0},
        ]
    )
    setattr(trader, fill_method, lambda code, opt: next(fills))

    assert trader.execute(
        "TEST", open_operation(key="open-1", rate=0.4, direction=direction)
    )
    assert trader.execute(
        "TEST", open_operation(key="open-2", rate=0.6, direction=direction)
    )

    position = trader.positions["TEST:breakout"]
    assert position.amount == pytest.approx(5.0)
    assert position.price == pytest.approx(16.0)
    assert [record["price"] for record in position.open_records] == [10.0, 20.0]
    assert [record["amount"] for record in position.open_records] == [2.0, 3.0]


def test_weighted_average_respects_unequal_quantities():
    assert weighted_average_price(10.0, 100.0, 20.0, 50.0) == pytest.approx(
        40.0 / 3.0
    )


@pytest.mark.parametrize(
    ("bad_price", "bad_amount"),
    [
        (float("nan"), 1.0),
        (float("inf"), 1.0),
        (10.0, float("nan")),
        (10.0, float("inf")),
        (10.0, -1.0),
        (0.0, 1.0),
    ],
)
def test_invalid_open_fills_are_rejected_before_position_accounting(
    bad_price, bad_amount
):
    trader = make_trader()
    trader.open_buy = lambda code, opt: {"price": bad_price, "amount": bad_amount}

    with pytest.raises(BackTestAccountingError):
        trader.execute("TEST", open_operation(key="bad", rate=1.0))

    position = trader.positions["TEST:breakout"]
    assert position.amount == 0
    assert position.price == 0
    assert position.open_records == []


def test_fractional_position_closes_exactly_once_despite_float_residue():
    trader = make_trader()
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": 0.3}
    assert trader.execute("TEST", open_operation(key="open", rate=1.0))
    position = trader.positions["TEST:breakout"]

    close_fills = iter(
        [
            {"price": 11.0, "amount": 0.1},
            {"price": 12.0, "amount": 0.2},
        ]
    )
    trader.close_buy = lambda code, pos, opt: next(close_fills)

    assert trader.execute("TEST", close_operation(key="close-1", rate=1 / 3), position)
    assert position.amount == pytest.approx(0.2)
    assert position.now_pos_rate == pytest.approx(2 / 3)
    assert trader.positions_history == {}

    assert trader.execute("TEST", close_operation(key="close-2", rate=2 / 3), position)
    assert position.amount == 0.0
    assert position.now_pos_rate == 0.0
    assert len(trader.positions_history["TEST"]) == 1
    history_count = len(trader.positions_history["TEST"])

    # A repeated close against the already-closed object is a no-op and must not
    # record settlement twice.
    assert trader.execute("TEST", close_operation(key="close-3", rate=1.0), position)
    assert len(trader.positions_history["TEST"]) == history_count


def test_subtract_quantity_clamps_only_machine_precision_residue():
    remaining = subtract_quantity(0.3, 0.1)
    assert remaining == pytest.approx(0.2)
    assert subtract_quantity(remaining, 0.2) == 0.0

    # A genuinely open quantity must not be hidden by an overly broad epsilon.
    assert subtract_quantity(1e-10, 0.0) == pytest.approx(1e-10)


def test_close_rejects_amount_and_position_rate_divergence():
    trader = make_trader()
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": 1.0}
    assert trader.execute("TEST", open_operation(key="open", rate=1.0))
    position = trader.positions["TEST:breakout"]

    # The fill claims the full amount was closed while the operation only closes
    # half the position rate. Silently accepting this would corrupt the state model.
    trader.close_buy = lambda code, pos, opt: {"price": 11.0, "amount": 1.0}
    with pytest.raises(BackTestAccountingError, match="diverged"):
        trader.execute("TEST", close_operation(key="bad-close", rate=0.5), position)

    assert position.amount == 1.0
    assert position.now_pos_rate == 1.0


def test_open_fill_is_not_applied_when_futures_accounting_configuration_fails():
    trader = make_trader("futures")
    trader.futures_contracts = {}
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": 1.0}

    with pytest.raises(KeyError):
        trader.execute("TEST", open_operation(key="open", rate=1.0))

    position = trader.positions["TEST:breakout"]
    assert position.amount == 0.0
    assert position.price == 0.0
    assert position.now_pos_rate == 0.0
    assert position.open_records == []


def test_close_profit_reconstruction_clamps_fractional_residue():
    from types import SimpleNamespace

    from tradingview_zy.backtesting.backtest import BackTest
    from tradingview_zy.backtesting.base import POSITION

    position = POSITION(code="TEST", signal="breakout", type="做多", amount=0.3)
    position.open_records = [
        {
            "hold_balance": 3.0,
            "amount": 0.3,
            "fee": 0.0,
        }
    ]
    position.close_records = [
        {
            "close_uid": "clear",
            "release_balance": 1.1,
            "fee": 0.0,
            "price": 11.0,
            "amount": 0.1,
            "datetime": datetime.datetime(2024, 1, 2, 10, 0),
            "close_msg": "part 1",
            "max_profit_rate": 0.0,
            "max_loss_rate": 0.0,
        },
        {
            "close_uid": "clear",
            "release_balance": 2.4,
            "fee": 0.0,
            "price": 12.0,
            "amount": 0.2,
            "datetime": datetime.datetime(2024, 1, 2, 10, 1),
            "close_msg": "part 2",
            "max_profit_rate": 0.0,
            "max_loss_rate": 0.0,
        },
    ]

    bt = BackTest()
    bt.market = "currency"
    bt.trader = SimpleNamespace(
        get_opt_close_uids=lambda code, signal, uids: list(uids)
    )

    result = bt._BackTest__get_close_profit(position, ["clear"])
    assert result["hold_amount"] == pytest.approx(0.3)
    assert result["close_price"] == 12.0
    assert result["profit"] == pytest.approx(0.5)


@pytest.mark.parametrize("market", ["a", "futures"])
def test_lot_rounding_reduces_the_executed_position_rate_consistently(market):
    trader = make_trader(market)
    opening_amount = 300.0 if market == "a" else 3.0
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": opening_amount}
    assert trader.execute("TEST", open_operation(key="open", rate=1.0))
    position = trader.positions["TEST:breakout"]
    if market == "a":
        trader.datas.now_date = datetime.datetime(2024, 1, 3, 9, 30)

    assert trader.execute(
        "TEST", close_operation(key="rounded-close", rate=0.5), position
    )

    expected_closed_amount = 100.0 if market == "a" else 1.0
    assert position.close_records[-1]["amount"] == expected_closed_amount
    assert position.close_records[-1]["pos_rate"] == pytest.approx(1 / 3)
    assert position.amount == pytest.approx(opening_amount - expected_closed_amount)
    assert position.now_pos_rate == pytest.approx(2 / 3)
    assert "TEST" not in trader.positions_history


@pytest.mark.parametrize("direction", ["long", "short"])
def test_three_fractional_closes_clamp_to_exact_zero_and_settle_once(direction):
    trader = make_trader("currency")
    fill_method = "open_buy" if direction == "long" else "open_sell"
    setattr(trader, fill_method, lambda code, opt: {"price": 10.0, "amount": 0.3})
    assert trader.execute(
        "TEST", open_operation(key="open", rate=1.0, direction=direction)
    )
    position = trader.positions["TEST:breakout"]

    for index in range(3):
        assert trader.execute(
            "TEST",
            close_operation(key=f"close-{index}", rate=1 / 3),
            position,
        )

    assert position.amount == 0.0
    assert position.now_pos_rate == 0.0
    assert len(trader.positions_history["TEST"]) == 1
    history_count = len(trader.positions_history["TEST"])
    assert trader.execute(
        "TEST", close_operation(key="close-again", rate=1.0), position
    )
    assert len(trader.positions_history["TEST"]) == history_count


def test_zero_size_open_fill_is_rejected_without_recording_a_position():
    trader = make_trader()
    trader.open_buy = lambda code, opt: {"price": 10.0, "amount": 0.0}

    assert trader.execute("TEST", open_operation(key="zero", rate=1.0)) is False
    position = trader.positions["TEST:breakout"]
    assert position.amount == 0.0
    assert position.price == 0.0
    assert position.open_records == []


def test_small_but_material_fractional_quantity_is_not_hidden_by_tolerance():
    assert subtract_quantity(1e-10, 0.0) == pytest.approx(1e-10)
