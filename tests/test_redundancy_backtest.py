"""Offline behavior contracts for replay windows, queues and close hooks."""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from tradingview_zy.backtesting import futures_contracts
from tradingview_zy.backtesting.backtest_klines import BackTestKlines
from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.base import Operation, POSITION


MARKET_BOUNDARIES = [
    ("a", "Asia/Shanghai", True),
    ("hk", "Asia/Shanghai", True),
    ("us", "US/Eastern", False),
    ("futures", "Asia/Shanghai", False),
    ("currency", "UTC", False),
    ("currency_spot", "UTC", False),
]
CODE = "TEST"


def bars(minutes, zone="UTC"):
    dates = pd.DatetimeIndex([
        pd.Timestamp("2025-01-02 09:00", tz=zone) + pd.Timedelta(minutes=m)
        for m in minutes
    ])
    return pd.DataFrame({
        "date": dates, "open": 10.0, "high": 12.0, "low": 9.0,
        "close": [10.0 + m for m in minutes],
        "volume": [0 if m in (1, 3) else 10 for m in minutes],
    })


@pytest.fixture
def replay_factory(monkeypatch):
    """Use real replay initialization with an in-memory exchange only."""
    def make(market="currency", frames=None):
        frames = {"1m": bars(range(6))} if frames is None else frames
        calls = []

        def klines(code, frequency, **kwargs):
            calls.append((code, frequency, kwargs))
            data = frames[frequency]
            return None if data is None else data.copy(deep=True)

        exchange = SimpleNamespace(klines=klines, calls=calls)
        module = types.ModuleType("tradingview_zy.exchange.exchange_db")
        module.ExchangeDB = lambda market: exchange
        monkeypatch.setitem(sys.modules, module.__name__, module)
        monkeypatch.setitem(
            BackTestKlines.init.__globals__, "tqdm",
            lambda **kwargs: SimpleNamespace(total=kwargs["total"], update=Mock()),
        )
        start = pd.Timestamp("2025-01-02 09:00", tz="UTC")
        return BackTestKlines(market, start, start + pd.Timedelta(days=1), list(frames))

    return make


@pytest.mark.parametrize("market,zone,inclusive", MARKET_BOUNDARIES)
@pytest.mark.parametrize("limit", [3, 0, -2, 100, -100])
@pytest.mark.parametrize("drop_zero", [False, True])
def test_cached_windows_match_visible_prefix_slice_without_mutating_history(
    replay_factory, market, zone, inclusive, limit, drop_zero,
):
    data = bars([5, 1, 3, 0, 4, 2], zone)
    original = data.copy(deep=True)
    replay = replay_factory(market, {"1m": data})
    replay.load_kline_nums = limit
    replay.del_volume_zero = drop_zero
    ordered = data.sort_values("date").reset_index(drop=True)
    # Before/at/between/after the history bounds, then rewind a warm history.
    for minute in (-1, 0, 3, 3.5, 8, 2):
        replay.now_date = pd.Timestamp("2025-01-02 09:00", tz=zone) + pd.Timedelta(minutes=minute)
        replay.cache_klines = {}
        visible = ordered[
            ordered.date <= replay.now_date if inclusive else ordered.date < replay.now_date
        ]
        expected = visible.iloc[-limit:]
        if drop_zero:
            expected = expected[expected.volume != 0]
        expected = expected.reset_index(drop=True)

        result = replay.klines(CODE, "1m")
        pd.testing.assert_frame_equal(result, expected)
        if minute == 3 and limit == 3 and drop_zero:
            assert result.date.dt.minute.tolist() == ([2] if inclusive else [0, 2])
        assert result.index.equals(pd.RangeIndex(len(result)))
        if len(result):
            result.loc[0, "close"] = -999.0
            result.loc[0, "date"] = pd.Timestamp("2040-01-01", tz=zone)
        pd.testing.assert_frame_equal(replay.all_klines[f"{CODE}-1m"], ordered)
        pd.testing.assert_frame_equal(data, original)
    assert len(replay.ex.calls) == 1


@pytest.mark.parametrize("limit", [3, 0, -2])
def test_empty_cached_history_stays_empty(replay_factory, limit):
    empty = bars([0]).iloc[:0]
    replay = replay_factory(frames={"1m": empty})
    replay.load_kline_nums = limit
    replay.del_volume_zero = True
    pd.testing.assert_frame_equal(replay.klines(CODE, "1m"), empty)
    pd.testing.assert_frame_equal(replay.all_klines[f"{CODE}-1m"], empty)


@pytest.mark.parametrize("market,zone,inclusive", MARKET_BOUNDARIES)
def test_duplicate_boundary_dates_are_all_included_or_excluded(replay_factory, market, zone, inclusive):
    replay = replay_factory(market, {"1m": bars([0, 1, 2, 2, 3], zone)})
    replay.now_date = pd.Timestamp("2025-01-02 09:02", tz=zone)
    result = replay.klines(CODE, "1m")
    assert result.date.dt.minute.tolist() == ([0, 1, 2, 2] if inclusive else [0, 1])


def test_multiple_frequency_queues_consume_independently_and_clear_step_cache(replay_factory):
    replay = replay_factory(frames={"5m": bars([5, 0, 5]), "1m": bars([2, 0, 1])})
    replay.init(CODE, ["5m", "1m"])
    assert replay.bar.total == 3
    assert list(replay.loop_datetime_list["5m"]) == bars([0, 5, 5]).date.tolist()
    assert list(replay.loop_datetime_list["1m"]) == bars([0, 1, 2]).date.tolist()
    assert [call[1] for call in replay.ex.calls] == ["5m", "1m"]
    assert all(call[2]["args"] == {"limit": None} for call in replay.ex.calls)

    for frequency, minute in [("5m", 0), ("", 0), (None, 1), ("5m", 5), ("1m", 2)]:
        replay.cache_klines = {CODE: {"1m": bars([0])}}
        replay.all_klines = {f"{CODE}-1m": bars([0])}
        assert replay.next(frequency)
        assert replay.now_date == bars([minute]).date.iloc[0]
        assert replay.cache_klines == {}
        assert replay.all_klines
    assert len(replay.loop_datetime_list["1m"]) == 0
    assert len(replay.loop_datetime_list["5m"]) == 1
    assert replay.next() is False
    assert replay.all_klines == {} and replay.cache_klines == {}
    # Exhausting one frequency does not consume or discard another queue.
    assert replay.next("5m") is True
    assert replay.now_date == bars([5]).date.iloc[0]
    assert replay.next("5m") is False
    assert replay.bar.update.call_count == 6


@pytest.mark.parametrize("empty", [None, pd.DataFrame({"date": pd.to_datetime([])})])
@pytest.mark.parametrize("frequency", [None, "1m"])
def test_empty_loop_initialization_and_repeated_exhaustion(replay_factory, empty, frequency):
    replay = replay_factory(frames={"1m": empty})
    replay.init(CODE, frequency)
    now = replay.now_date
    assert len(replay.loop_datetime_list["1m"]) == 0
    assert replay.bar.total == 0
    assert replay.next() is False
    assert replay.next(None) is False
    assert replay.now_date == now
    replay.bar.update.assert_not_called()


@pytest.mark.parametrize("mode", ["signal", "trade", "real"])
@pytest.mark.parametrize("market,expected_amount", [
    ("a", 200), ("futures", 251), ("us", 251.25), ("hk", 251.25),
    ("currency", 251.25), ("currency_spot", 251.25),
])
@pytest.mark.parametrize("loss_price", [0, 88.5])
def test_long_and_short_close_hooks_share_price_and_partial_lot_rules(
    mode, market, expected_amount, loss_price,
):
    options = {}
    if market == "futures":
        options["futures_parameter_manifest"] = futures_contracts.build_futures_parameter_manifest(
            version="2024-12-13-r2", start_datetime="2025-01-01",
            end_datetime="2025-01-02", codes=["SHFE.RB"],
        )
    trader = BackTestTrader("close-contract", mode=mode, market=market, **options)
    position = POSITION(CODE, "breakout", amount=753.75)
    position.now_pos_rate = 0.6
    operation = Operation(CODE, "sell", "breakout", loss_price=loss_price, pos_rate=0.2)
    for close in (trader.close_buy, trader.close_sell):
        trader.get_price = Mock(return_value={"close": 123.5})
        assert close(CODE, position, operation) == {
            "price": loss_price or 123.5, "amount": expected_amount,
        }
        if loss_price:
            trader.get_price.assert_not_called()
        else:
            trader.get_price.assert_called_once_with(CODE)
        assert position.amount == 753.75 and position.now_pos_rate == 0.6
        assert operation.pos_rate == 0.2 and operation.loss_price == loss_price


@pytest.mark.parametrize("direction,hook,price", [("long", "buy", 102), ("short", "sell", 98)])
@pytest.mark.parametrize("mode", ["signal", "trade"])
@pytest.mark.parametrize("reject", [False, True])
def test_execute_keeps_independent_overridable_long_short_close_hooks(direction, hook, price, mode, reject):
    calls = []

    class CustomTrader(BackTestTrader):
        def close_buy(self, code, pos, opt):
            calls.append("buy")
            result = super().close_buy(code, pos, opt)
            result["price"] = 102
            return False if reject else result

        def close_sell(self, code, pos, opt):
            calls.append("sell")
            result = super().close_sell(code, pos, opt)
            result["price"] = 98
            return False if reject else result

    trader = CustomTrader("hooks", mode=mode, market="currency", fee_rate=0)
    trader.datas = SimpleNamespace(
        now_date=pd.Timestamp("2025-01-02", tz="UTC"),
        last_k_info=lambda code: {"close": 100},
    )
    assert trader.execute(CODE, Operation(CODE, "buy", "breakout", info={"type": direction}))
    position = trader.positions[f"{CODE}:breakout"]
    amount = position.amount
    assert trader.execute(CODE, Operation(CODE, "sell", "breakout"), position) is not reject
    assert calls == [hook]
    if reject:
        assert position.amount == amount
        assert position.close_records == []
    else:
        assert position.amount == 0
        assert position.close_records[-1]["price"] == price
        assert position.profit == pytest.approx(amount * 2)
