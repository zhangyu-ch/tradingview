"""Typed, versioned boundary for generic monitoring-event persistence.

Legacy Chanlun-oriented alert columns remain readable during migration, but all
new strategy events must use the canonical event type, a persistable
``StrategyAction`` and a finite numeric score.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from tradingview_zy.strategies.base import StrategyAction


class MonitoringEventType(StrEnum):
    """Canonical persisted monitoring-event categories."""

    STRATEGY_SIGNAL = "strategy_signal"


@dataclass(frozen=True, slots=True)
class MonitoringEventValues:
    event_type: MonitoringEventType
    action: StrategyAction
    score: float


_PERSISTABLE_ACTIONS = frozenset(
    {
        StrategyAction.WATCH,
        StrategyAction.BUY,
        StrategyAction.SELL,
        StrategyAction.OPEN,
        StrategyAction.CLOSE,
    }
)
_LEGACY_EVENT_TYPE_ALIASES: dict[str, MonitoringEventType] = {
    "sig": MonitoringEventType.STRATEGY_SIGNAL,
    "signal": MonitoringEventType.STRATEGY_SIGNAL,
    MonitoringEventType.STRATEGY_SIGNAL.value: MonitoringEventType.STRATEGY_SIGNAL,
}


def _normalize_token(value: Any, *, field: str, max_length: int) -> str:
    if isinstance(value, StrEnum):
        value = value.value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string or enum")
    token = value.strip().lower()
    if not token:
        raise ValueError(f"{field} must not be empty")
    if len(token) > max_length:
        raise ValueError(f"{field} exceeds {max_length} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in token):
        raise ValueError(f"{field} contains control characters")
    return token


def normalize_monitoring_event_type(value: Any) -> MonitoringEventType:
    if isinstance(value, MonitoringEventType):
        return value
    token = _normalize_token(value, field="event_type", max_length=32)
    try:
        return MonitoringEventType(token)
    except ValueError as error:
        raise ValueError(f"unsupported monitoring event_type: {token!r}") from error


def normalize_monitoring_action(value: Any) -> StrategyAction:
    if isinstance(value, StrategyAction):
        action = value
    else:
        token = _normalize_token(value, field="action", max_length=16)
        try:
            action = StrategyAction(token)
        except ValueError as error:
            raise ValueError(f"unsupported monitoring action: {token!r}") from error
    if action not in _PERSISTABLE_ACTIONS:
        raise ValueError(f"monitoring action is not persistable: {action.value!r}")
    return action


def normalize_monitoring_score(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("score must be a numeric value")
    score = float(value)
    if not math.isfinite(score):
        raise ValueError("score must be finite")
    return score


def normalize_monitoring_event(
    *, event_type: Any, action: Any, score: Any
) -> MonitoringEventValues:
    return MonitoringEventValues(
        event_type=normalize_monitoring_event_type(event_type),
        action=normalize_monitoring_action(action),
        score=normalize_monitoring_score(score),
    )


def legacy_event_type(value: Any) -> MonitoringEventType | None:
    """Map only recognized old aliases; unknown historical values stay untouched."""

    if value is None:
        return None
    try:
        token = _normalize_token(value, field="legacy event_type", max_length=32)
    except (TypeError, ValueError):
        return None
    return _LEGACY_EVENT_TYPE_ALIASES.get(token)


def legacy_aliases_for(value: MonitoringEventType | str) -> tuple[str, ...]:
    canonical = normalize_monitoring_event_type(value)
    return tuple(
        alias
        for alias, event_type in _LEGACY_EVENT_TYPE_ALIASES.items()
        if event_type is canonical
    )


def legacy_action(value: Any) -> StrategyAction | None:
    if value is None:
        return None
    try:
        return normalize_monitoring_action(value)
    except (TypeError, ValueError):
        return None


def legacy_score(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        score = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return score if math.isfinite(score) else None
