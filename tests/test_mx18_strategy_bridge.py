from __future__ import annotations

import datetime as dt

import pytest

from tradingview_zy.backtesting.base import Operation
from tradingview_zy.strategies.base import StrategyAction, StrategySignal
from tradingview_zy.strategy_bridge import (
    BRIDGE_INFO_KEY,
    StrategyBridgeError,
    operation_to_strategy_signal,
    signal_to_trade_decision,
    strategy_signal_to_operation,
)

NOW = dt.datetime(2026, 8, 4, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=8)))


def _signal(action: StrategyAction = StrategyAction.OPEN, **overrides) -> StrategySignal:
    values = {
        "code": "SH.600000",
        "name": "浦发银行",
        "action": action,
        "score": 0.9,
        "message": "突破确认",
        "frequency": "30m",
        "event_time": NOW,
        "metadata": {
            "trace_id": "strategy-run-1",
            "trade": {
                "position_rate": 0.25,
                "loss_price": 9.5,
                "signal": "breakout",
                "key": "2026-08-04T10:00+08:00",
                "open_uid": "SH.600000:breakout",
                "close_uid": "clear",
            },
        },
    }
    values.update(overrides)
    return StrategySignal(**values)


def test_signal_operation_round_trip_is_versioned_and_traceable() -> None:
    signal = _signal()
    operation = strategy_signal_to_operation(signal, market="a", context_now=NOW)

    assert operation.opt == "buy"
    assert operation.pos_rate == 0.25
    assert operation.loss_price == 9.5
    assert operation.signal == "breakout"
    assert operation.info[BRIDGE_INFO_KEY]["metadata"]["trace_id"] == "strategy-run-1"

    restored = operation_to_strategy_signal(operation, market="a", context_now=NOW)
    assert restored.to_payload() == signal.to_payload()


def test_close_signal_maps_to_sell_without_guessing() -> None:
    operation = strategy_signal_to_operation(
        _signal(StrategyAction.CLOSE), market="a", context_now=NOW
    )
    assert operation.opt == "sell"
    assert operation.close_uid == "clear"


@pytest.mark.parametrize(
    "action",
    [StrategyAction.SELECT, StrategyAction.WATCH, StrategyAction.IGNORE],
)
def test_non_executable_signal_actions_are_rejected(action: StrategyAction) -> None:
    with pytest.raises(StrategyBridgeError, match="executable"):
        signal_to_trade_decision(_signal(action), market="a", context_now=NOW)


def test_trade_metadata_is_required_and_position_is_not_inferred_from_score() -> None:
    with pytest.raises(StrategyBridgeError, match="metadata.trade"):
        signal_to_trade_decision(_signal(metadata={}), market="a", context_now=NOW)
    invalid = _signal(
        metadata={"trade": {"position_rate": 0, "signal": "x", "key": "k"}}
    )
    with pytest.raises(StrategyBridgeError, match="position_rate"):
        signal_to_trade_decision(invalid, market="a", context_now=NOW)


def test_tampered_operation_cannot_be_converted_back() -> None:
    operation = strategy_signal_to_operation(_signal(), market="a", context_now=NOW)
    operation.pos_rate = 0.75
    with pytest.raises(StrategyBridgeError, match="position_rate"):
        operation_to_strategy_signal(operation, market="a", context_now=NOW)


def test_arbitrary_legacy_operation_is_not_silently_guessed() -> None:
    legacy = Operation(code="SH.600000", opt="buy", signal="legacy")
    with pytest.raises(StrategyBridgeError, match="snapshot"):
        operation_to_strategy_signal(legacy, market="a", context_now=NOW)


def test_bridge_snapshot_schema_and_signal_schema_are_enforced() -> None:
    operation = strategy_signal_to_operation(_signal(), market="a", context_now=NOW)
    operation.info[BRIDGE_INFO_KEY]["schema_version"] = 999
    with pytest.raises(StrategyBridgeError, match="schema_version"):
        operation_to_strategy_signal(operation, market="a", context_now=NOW)
