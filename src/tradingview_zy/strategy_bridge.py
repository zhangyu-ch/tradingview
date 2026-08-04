"""Explicit, versioned conversion between strategy signals and trade operations.

Selection/monitoring signals and backtesting operations remain separate domain
models.  Cross-domain reuse is opt-in through this module; callers must provide
trade intent explicitly instead of inferring position size or execution keys
from a score or message.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from tradingview_zy.data_contracts import OrderRequest
from tradingview_zy.domain import OrderOffset, OrderSide
from tradingview_zy.backtesting.base import Operation
from tradingview_zy.strategies.base import (
    SIGNAL_SCHEMA_VERSION,
    StrategyAction,
    StrategyPurpose,
    StrategyRunTarget,
    StrategySignal,
    validate_strategy_signals,
)
from tradingview_zy.web_payloads import market_timezone

BRIDGE_SCHEMA_VERSION = 1
BRIDGE_INFO_KEY = "strategy_bridge"


class StrategyBridgeError(ValueError):
    """A signal/operation cannot be converted without guessing semantics."""


class DecisionAction(StrEnum):
    OPEN = "open"
    CLOSE = "close"


_SIGNAL_TO_DECISION = {
    StrategyAction.BUY: DecisionAction.OPEN,
    StrategyAction.OPEN: DecisionAction.OPEN,
    StrategyAction.SELL: DecisionAction.CLOSE,
    StrategyAction.CLOSE: DecisionAction.CLOSE,
}
_DECISION_TO_OPERATION = {
    DecisionAction.OPEN: "buy",
    DecisionAction.CLOSE: "sell",
}


@dataclass(frozen=True, slots=True)
class TradeDecision:
    code: str
    name: str
    frequency: str
    event_time: dt.datetime
    source_action: StrategyAction
    action: DecisionAction
    score: float
    signal_name: str
    position_rate: float
    loss_price: float
    message: str
    key: str
    open_uid: str
    close_uid: str
    metadata: dict[str, Any]
    schema_version: int = BRIDGE_SCHEMA_VERSION
    signal_schema_version: int = SIGNAL_SCHEMA_VERSION

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "signal_schema_version": self.signal_schema_version,
            "code": self.code,
            "name": self.name,
            "frequency": self.frequency,
            "event_time": self.event_time.isoformat(),
            "source_action": self.source_action.value,
            "action": self.action.value,
            "score": self.score,
            "signal_name": self.signal_name,
            "position_rate": self.position_rate,
            "loss_price": self.loss_price,
            "message": self.message,
            "key": self.key,
            "open_uid": self.open_uid,
            "close_uid": self.close_uid,
            "metadata": copy.deepcopy(self.metadata),
        }


def _text(value: Any, field: str, *, maximum: int = 256) -> str:
    if not isinstance(value, str):
        raise StrategyBridgeError(f"{field} must be a string")
    result = value.strip()
    if not result:
        raise StrategyBridgeError(f"{field} must not be empty")
    if len(result) > maximum or any(ord(character) < 32 for character in result):
        raise StrategyBridgeError(f"{field} is invalid")
    return result


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StrategyBridgeError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise StrategyBridgeError(f"{field} must be finite")
    return result


def _json_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise StrategyBridgeError("metadata must be an object")
    result = copy.deepcopy(dict(value))
    try:
        json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise StrategyBridgeError("metadata must be JSON-compatible") from error
    return result


def _canonical_signal(
    signal: StrategySignal,
    *,
    market: str,
    context_now: dt.datetime | None,
) -> StrategySignal:
    now = context_now or dt.datetime.now(tz=market_timezone(market))
    target = StrategyRunTarget(
        market=market,
        code=signal.code,
        name=signal.name,
        frequency=signal.frequency,
    )
    try:
        canonical = validate_strategy_signals(
            signal,
            target,
            purpose=StrategyPurpose.MONITORING,
            context_now=now,
        )
    except (TypeError, ValueError) as error:
        raise StrategyBridgeError("signal is not an executable monitoring event") from error
    if len(canonical) != 1:
        raise StrategyBridgeError("signal is not an executable monitoring event")
    return canonical[0]


def signal_to_trade_decision(
    signal: StrategySignal,
    *,
    market: str,
    context_now: dt.datetime | None = None,
) -> TradeDecision:
    """Convert one validated executable signal into an explicit decision."""

    canonical = _canonical_signal(signal, market=market, context_now=context_now)
    try:
        source_action = StrategyAction(canonical.action)
        decision_action = _SIGNAL_TO_DECISION[source_action]
    except (TypeError, ValueError, KeyError) as error:
        raise StrategyBridgeError(
            "only buy/sell/open/close monitoring signals are executable"
        ) from error

    trade = canonical.metadata.get("trade")
    if not isinstance(trade, Mapping):
        raise StrategyBridgeError("signal metadata.trade is required")
    position_rate = _finite_number(trade.get("position_rate"), "position_rate")
    if not 0 < position_rate <= 1:
        raise StrategyBridgeError("position_rate must be within (0, 1]")
    loss_price = _finite_number(trade.get("loss_price", 0.0), "loss_price")
    if loss_price < 0:
        raise StrategyBridgeError("loss_price must be non-negative")

    signal_name = _text(trade.get("signal"), "trade.signal", maximum=128)
    key = _text(trade.get("key"), "trade.key", maximum=256)
    open_uid = _text(
        trade.get("open_uid", f"{canonical.code}:{signal_name}"),
        "trade.open_uid",
        maximum=256,
    )
    close_uid = _text(trade.get("close_uid", "clear"), "trade.close_uid", maximum=256)

    return TradeDecision(
        code=canonical.code,
        name=canonical.name,
        frequency=canonical.frequency,
        event_time=canonical.event_time,
        source_action=source_action,
        action=decision_action,
        score=canonical.score,
        signal_name=signal_name,
        position_rate=position_rate,
        loss_price=loss_price,
        message=canonical.message,
        key=key,
        open_uid=open_uid,
        close_uid=close_uid,
        metadata=_json_metadata(canonical.metadata),
    )


def _validate_decision(decision: TradeDecision) -> TradeDecision:
    if not isinstance(decision, TradeDecision):
        raise TypeError("decision must be TradeDecision")
    if decision.schema_version != BRIDGE_SCHEMA_VERSION:
        raise StrategyBridgeError("bridge schema_version is unsupported")
    if decision.signal_schema_version != SIGNAL_SCHEMA_VERSION:
        raise StrategyBridgeError("source signal schema_version is unsupported")
    if _SIGNAL_TO_DECISION.get(decision.source_action) is not decision.action:
        raise StrategyBridgeError("source action and trade decision disagree")
    if not 0 < _finite_number(decision.position_rate, "position_rate") <= 1:
        raise StrategyBridgeError("position_rate must be within (0, 1]")
    if _finite_number(decision.loss_price, "loss_price") < 0:
        raise StrategyBridgeError("loss_price must be non-negative")
    if decision.event_time.tzinfo is None or decision.event_time.utcoffset() is None:
        raise StrategyBridgeError("event_time must be timezone-aware")
    _text(decision.code, "code", maximum=128)
    _text(decision.name, "name", maximum=256)
    _text(decision.frequency, "frequency", maximum=32)
    _text(decision.signal_name, "signal_name", maximum=128)
    _text(decision.message, "message", maximum=2_000)
    _text(decision.key, "key", maximum=256)
    _text(decision.open_uid, "open_uid", maximum=256)
    _text(decision.close_uid, "close_uid", maximum=256)
    _json_metadata(decision.metadata)
    return decision


def trade_decision_to_operation(decision: TradeDecision) -> Operation:
    """Create a legacy Operation while embedding a tamper-evident bridge snapshot."""

    decision = _validate_decision(decision)
    return Operation(
        code=decision.code,
        opt=_DECISION_TO_OPERATION[decision.action],
        signal=decision.signal_name,
        loss_price=decision.loss_price,
        info={BRIDGE_INFO_KEY: decision.to_payload()},
        msg=decision.message,
        pos_rate=decision.position_rate,
        key=decision.key,
        open_uid=decision.open_uid,
        close_uid=decision.close_uid,
    )


def trade_decision_to_order_request(
    decision: TradeDecision,
    *,
    market: str,
    quantity: float,
    price: float | None = None,
    client_order_id: str = "",
) -> OrderRequest:
    """Materialize an explicit order intent without enabling live submission."""

    decision = _validate_decision(decision)
    side = OrderSide.BUY if decision.action is DecisionAction.OPEN else OrderSide.SELL
    offset = (
        OrderOffset.OPEN
        if decision.action is DecisionAction.OPEN
        else OrderOffset.CLOSE
    )
    return OrderRequest.create(
        market=market,
        code=decision.code,
        side=side,
        offset=offset,
        quantity=quantity,
        price=price,
        client_order_id=client_order_id,
        metadata={BRIDGE_INFO_KEY: decision.to_payload()},
    )


def strategy_signal_to_operation(
    signal: StrategySignal,
    *,
    market: str,
    context_now: dt.datetime | None = None,
) -> Operation:
    return trade_decision_to_operation(
        signal_to_trade_decision(signal, market=market, context_now=context_now)
    )


def _decision_from_payload(value: Any) -> TradeDecision:
    if not isinstance(value, Mapping):
        raise StrategyBridgeError("operation bridge snapshot is missing")
    try:
        event_time = dt.datetime.fromisoformat(str(value["event_time"]))
        decision = TradeDecision(
            code=value["code"],
            name=value["name"],
            frequency=value["frequency"],
            event_time=event_time,
            source_action=StrategyAction(value["source_action"]),
            action=DecisionAction(value["action"]),
            score=_finite_number(value["score"], "score"),
            signal_name=value["signal_name"],
            position_rate=_finite_number(value["position_rate"], "position_rate"),
            loss_price=_finite_number(value["loss_price"], "loss_price"),
            message=value["message"],
            key=value["key"],
            open_uid=value["open_uid"],
            close_uid=value["close_uid"],
            metadata=_json_metadata(value["metadata"]),
            schema_version=int(value["schema_version"]),
            signal_schema_version=int(value["signal_schema_version"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StrategyBridgeError("operation bridge snapshot is invalid") from error
    return _validate_decision(decision)


def operation_to_strategy_signal(
    operation: Operation,
    *,
    market: str,
    context_now: dt.datetime | None = None,
) -> StrategySignal:
    """Restore a signal only from the embedded versioned bridge snapshot.

    Arbitrary legacy Operations do not contain name/frequency/event_time/score,
    so converting them would require guessing.  They are rejected until a
    caller first creates an explicit TradeDecision.
    """

    if not isinstance(operation, Operation):
        raise TypeError("operation must be Operation")
    info = operation.info if isinstance(operation.info, Mapping) else {}
    decision = _decision_from_payload(info.get(BRIDGE_INFO_KEY))
    expected_opt = _DECISION_TO_OPERATION[decision.action]
    comparisons = {
        "code": (operation.code, decision.code),
        "opt": (operation.opt, expected_opt),
        "signal": (operation.signal, decision.signal_name),
        "position_rate": (float(operation.pos_rate), decision.position_rate),
        "loss_price": (float(operation.loss_price), decision.loss_price),
        "message": (operation.msg, decision.message),
        "key": (operation.key, decision.key),
        "open_uid": (operation.open_uid, decision.open_uid),
        "close_uid": (operation.close_uid, decision.close_uid),
    }
    changed = [name for name, (actual, expected) in comparisons.items() if actual != expected]
    if changed:
        raise StrategyBridgeError(
            "operation no longer matches its bridge snapshot: " + ", ".join(changed)
        )

    signal = StrategySignal(
        code=decision.code,
        name=decision.name,
        action=decision.source_action,
        score=decision.score,
        message=decision.message,
        frequency=decision.frequency,
        event_time=decision.event_time,
        metadata=_json_metadata(decision.metadata),
        schema_version=decision.signal_schema_version,
    )
    return _canonical_signal(signal, market=market, context_now=context_now)
