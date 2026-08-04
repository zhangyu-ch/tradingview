from __future__ import annotations

import copy
import datetime as dt
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

import pandas as pd

from tradingview_zy.base import Market
from tradingview_zy.domain import Frequency, parse_frequency
from tradingview_zy.market_registry import parse_market
from tradingview_zy.web_payloads import market_timezone, normalize_klines_for_market

StrategyRunStage = Literal["target", "provider", "input", "strategy", "output"]
SIGNAL_SCHEMA_VERSION = 1
MAX_SIGNALS_PER_TARGET = 64
MAX_MESSAGE_CHARS = 2_000
MAX_MESSAGE_BYTES = 8_192
MAX_METADATA_DEPTH = 6
MAX_METADATA_NODES = 256
MAX_METADATA_BYTES = 16_384
MAX_EVENT_FUTURE_SKEW = dt.timedelta(minutes=5)
_REQUIRED_KLINE_COLUMNS = ("date", "open", "close", "high", "low", "volume")


class StrategyAction(StrEnum):
    SELECT = "select"
    WATCH = "watch"
    BUY = "buy"
    SELL = "sell"
    OPEN = "open"
    CLOSE = "close"
    IGNORE = "ignore"


class StrategyPurpose(StrEnum):
    SELECTION = "selection"
    MONITORING = "monitoring"


_ALLOWED_ACTIONS: dict[StrategyPurpose, frozenset[StrategyAction]] = {
    StrategyPurpose.SELECTION: frozenset(
        {StrategyAction.SELECT, StrategyAction.IGNORE}
    ),
    StrategyPurpose.MONITORING: frozenset(
        {
            StrategyAction.WATCH,
            StrategyAction.BUY,
            StrategyAction.SELL,
            StrategyAction.OPEN,
            StrategyAction.CLOSE,
            StrategyAction.IGNORE,
        }
    ),
}


@dataclass(frozen=True)
class StrategyContext:
    market: Market | str
    code: str
    name: str
    frequency: Frequency | str
    klines: pd.DataFrame
    now: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySignal:
    code: str
    name: str
    action: StrategyAction | str
    score: float
    message: str
    frequency: Frequency | str
    event_time: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = SIGNAL_SCHEMA_VERSION

    def to_payload(self) -> dict[str, Any]:
        action = self.action.value if isinstance(self.action, StrategyAction) else str(self.action)
        return {
            "schema_version": self.schema_version,
            "code": self.code,
            "name": self.name,
            "action": action,
            "score": self.score,
            "message": self.message,
            "frequency": (
                self.frequency.value
                if isinstance(self.frequency, Frequency)
                else str(self.frequency)
            ),
            "event_time": self.event_time.isoformat(),
            "metadata": copy.deepcopy(self.metadata),
        }


@dataclass(frozen=True)
class StrategyRunTarget:
    market: Market | str
    code: str
    name: str
    frequency: Frequency | str


@dataclass(frozen=True)
class StrategyRunFailure:
    target: StrategyRunTarget
    stage: StrategyRunStage
    error_type: str
    message: str

    @property
    def market(self) -> str:
        return self.target.market.value if isinstance(self.target.market, Market) else self.target.market

    @property
    def code(self) -> str:
        return self.target.code

    @property
    def name(self) -> str:
        return self.target.name

    @property
    def frequency(self) -> str:
        return (
            self.target.frequency.value
            if isinstance(self.target.frequency, Frequency)
            else self.target.frequency
        )


@dataclass
class BatchRunResult:
    hits: list[StrategySignal] = field(default_factory=list)
    misses: list[StrategyRunTarget] = field(default_factory=list)
    failures: list[StrategyRunFailure] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.failures) == 0

    def extend(self, other: "BatchRunResult") -> "BatchRunResult":
        if not isinstance(other, BatchRunResult):
            raise TypeError("batch result must be BatchRunResult")
        self.hits.extend(other.hits)
        self.misses.extend(other.misses)
        self.failures.extend(other.failures)
        return self

    def __iter__(self):
        return iter(self.hits)

    def __len__(self) -> int:
        return len(self.hits)

    def __getitem__(self, index):
        return self.hits[index]


class StrategyInputError(ValueError):
    """Raised when provider data violates the strategy K-line contract."""


class StrategyOutputError(ValueError):
    """Raised when a strategy output violates the versioned signal contract."""


def normalize_strategy_results(results: Any) -> list[StrategySignal]:
    if results is None:
        return []
    if isinstance(results, StrategySignal):
        return [results]
    if not isinstance(results, list):
        raise TypeError(
            "strategy run() must return StrategySignal, list[StrategySignal], or None"
        )
    if len(results) > MAX_SIGNALS_PER_TARGET:
        raise StrategyOutputError(
            f"strategy returned more than {MAX_SIGNALS_PER_TARGET} signals"
        )
    if not all(isinstance(item, StrategySignal) for item in results):
        raise TypeError("strategy result list contains a non-StrategySignal item")
    return results


def _clean_error_message(error: BaseException) -> str:
    message = str(error).strip() or error.__class__.__name__
    message = " ".join(message.split())
    return message[:500]


def _safe_placeholder(value: Any, default: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned[:128]
    return default


def placeholder_target(market: Any, stock: Any, frequency: Any) -> StrategyRunTarget:
    code = "<invalid>"
    name = "<invalid>"
    if isinstance(stock, Mapping):
        code = _safe_placeholder(stock.get("code"), code)
        name = _safe_placeholder(stock.get("name"), code)
    return StrategyRunTarget(
        market=_safe_placeholder(market, "<invalid>"),
        code=code,
        name=name,
        frequency=_safe_placeholder(frequency, "<invalid>"),
    )


def _validate_text(value: Any, field_name: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    value = value.strip()
    if value == "":
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field_name} contains invalid Unicode") from error
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def strategy_target_from_stock(
    market: Any,
    stock: Any,
    frequency: Any,
) -> StrategyRunTarget:
    if not isinstance(stock, Mapping):
        raise TypeError("strategy target must be an object")
    market_value = parse_market(_validate_text(market, "market", 32))
    code = _validate_text(stock.get("code"), "code", 128)
    raw_name = stock.get("name", code)
    name = _validate_text(raw_name, "name", 256)
    frequency_value = parse_frequency(
        _validate_text(frequency, "frequency", 32)
    )
    return StrategyRunTarget(
        market=market_value,
        code=code,
        name=name,
        frequency=frequency_value,
    )


def validate_strategy_klines(
    klines: Any,
    target: StrategyRunTarget,
) -> pd.DataFrame:
    if not isinstance(klines, pd.DataFrame):
        raise StrategyInputError("provider must return a pandas DataFrame")
    if klines.empty:
        raise StrategyInputError("provider returned an empty K-line frame")

    missing = [column for column in _REQUIRED_KLINE_COLUMNS if column not in klines.columns]
    if missing:
        raise StrategyInputError(f"K-line frame is missing required columns: {missing}")

    try:
        normalized = normalize_klines_for_market(klines, target.market)
    except Exception as error:
        raise StrategyInputError(str(error)) from error
    if normalized is None or normalized.empty:
        raise StrategyInputError("provider returned an empty K-line frame")

    if normalized["date"].isna().any():
        raise StrategyInputError("K-line date contains null values")
    if normalized["date"].duplicated().any():
        raise StrategyInputError("K-line timestamps must be unique")
    if not normalized["date"].is_monotonic_increasing:
        raise StrategyInputError("K-line timestamps must be in ascending order")

    for column in ("open", "close", "high", "low", "volume"):
        try:
            values = pd.to_numeric(normalized[column], errors="raise")
        except Exception as error:
            raise StrategyInputError(f"K-line {column} must be numeric") from error
        if values.isna().any() or not values.map(math.isfinite).all():
            raise StrategyInputError(f"K-line {column} must contain only finite values")
        normalized[column] = values

    if (normalized["volume"] < 0).any():
        raise StrategyInputError("K-line volume must not be negative")

    row_max = normalized[["open", "close", "low"]].max(axis=1)
    row_min = normalized[["open", "close", "high"]].min(axis=1)
    if (normalized["high"] < row_max).any() or (normalized["low"] > row_min).any():
        raise StrategyInputError("K-line OHLC values are inconsistent")

    if "code" in normalized.columns:
        if normalized["code"].isna().any() or not normalized["code"].map(str).eq(target.code).all():
            raise StrategyInputError("K-line code does not match the strategy target")
    if "frequency" in normalized.columns:
        if normalized["frequency"].isna().any() or not normalized["frequency"].map(str).eq(target.frequency).all():
            raise StrategyInputError("K-line frequency does not match the strategy target")

    return normalized


def _market_datetime(value: Any, market: str, field_name: str) -> dt.datetime:
    if not isinstance(value, dt.datetime):
        raise TypeError(f"{field_name} must be a datetime")
    tz = market_timezone(market)
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _validate_metadata_text(
    value: Any,
    field_name: str,
    max_length: int,
    *,
    allow_empty: bool,
) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not allow_empty and value.strip() == "":
        raise ValueError(f"{field_name} must not be empty")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds {max_length} characters")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field_name} contains invalid Unicode") from error
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _metadata_value(
    value: Any,
    *,
    depth: int,
    budget: list[int],
    field_name: str = "metadata",
) -> Any:
    budget[0] += 1
    if budget[0] > MAX_METADATA_NODES:
        raise StrategyOutputError("strategy signal metadata has too many nodes")
    if depth > MAX_METADATA_DEPTH:
        raise StrategyOutputError("strategy signal metadata is too deeply nested")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StrategyOutputError("strategy signal metadata contains a non-finite number")
        return value
    if isinstance(value, str):
        return _validate_metadata_text(
            value, field_name, 2_000, allow_empty=True
        )
    if isinstance(value, list):
        if len(value) > 128:
            raise StrategyOutputError("strategy signal metadata list is too large")
        return [
            _metadata_value(item, depth=depth + 1, budget=budget, field_name=field_name)
            for item in value
        ]
    if isinstance(value, Mapping):
        if len(value) > 128:
            raise StrategyOutputError("strategy signal metadata object is too large")
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = _validate_metadata_text(
                raw_key, "metadata key", 128, allow_empty=False
            )
            result[key] = _metadata_value(
                raw_value,
                depth=depth + 1,
                budget=budget,
                field_name=f"metadata.{key}",
            )
        return result
    raise TypeError("strategy signal metadata must contain JSON-compatible values")


def _canonical_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("strategy signal metadata must be an object")
    canonical = _metadata_value(value, depth=0, budget=[0])
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    if len(encoded) > MAX_METADATA_BYTES:
        raise StrategyOutputError("strategy signal metadata exceeds the UTF-8 byte limit")
    return copy.deepcopy(canonical)


def _canonical_signal(
    signal: StrategySignal,
    target: StrategyRunTarget,
    purpose: StrategyPurpose,
    context_now: dt.datetime,
) -> StrategySignal:
    if type(signal.schema_version) is not int or signal.schema_version != SIGNAL_SCHEMA_VERSION:
        raise StrategyOutputError("strategy signal schema_version is unsupported")
    code = _validate_text(signal.code, "strategy signal code", 128)
    name = _validate_text(signal.name, "strategy signal name", 256)
    try:
        frequency = parse_frequency(
            _validate_text(signal.frequency, "strategy signal frequency", 32)
        )
        target_frequency = parse_frequency(target.frequency)
    except (TypeError, ValueError) as error:
        raise StrategyOutputError("strategy signal frequency is unsupported") from error
    if code != target.code:
        raise StrategyOutputError("strategy signal code does not match the target")
    if name != target.name:
        raise StrategyOutputError("strategy signal name does not match the target")
    if frequency is not target_frequency:
        raise StrategyOutputError("strategy signal frequency does not match the target")
    try:
        action = StrategyAction(signal.action)
    except (TypeError, ValueError) as error:
        raise StrategyOutputError("strategy signal action is unsupported") from error
    if action not in _ALLOWED_ACTIONS[purpose]:
        raise StrategyOutputError(
            f"strategy signal action {action.value} is invalid for {purpose.value}"
        )
    if isinstance(signal.score, bool) or not isinstance(signal.score, (int, float)):
        raise TypeError("strategy signal score must be numeric")
    score = float(signal.score)
    if not math.isfinite(score):
        raise StrategyOutputError("strategy signal score must be finite")
    message = _validate_text(signal.message, "strategy signal message", MAX_MESSAGE_CHARS)
    if len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise StrategyOutputError("strategy signal message exceeds the UTF-8 byte limit")
    event_time = _market_datetime(signal.event_time, target.market, "strategy signal event_time")
    if event_time > context_now + MAX_EVENT_FUTURE_SKEW:
        raise StrategyOutputError("strategy signal event_time is too far in the future")
    metadata = _canonical_metadata(signal.metadata)
    return StrategySignal(
        code=code,
        name=name,
        action=action,
        score=score,
        message=message,
        frequency=frequency,
        event_time=event_time,
        metadata=metadata,
        schema_version=SIGNAL_SCHEMA_VERSION,
    )


def validate_strategy_signals(
    results: Any,
    target: StrategyRunTarget,
    *,
    purpose: StrategyPurpose,
    context_now: dt.datetime,
) -> list[StrategySignal]:
    signals = normalize_strategy_results(results)
    canonical: list[StrategySignal] = []
    fingerprints: set[str] = set()
    for signal in signals:
        item = _canonical_signal(signal, target, purpose, context_now)
        fingerprint = json.dumps(
            item.to_payload(),
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        if fingerprint in fingerprints:
            raise StrategyOutputError("strategy returned a duplicate signal")
        fingerprints.add(fingerprint)
        if item.action is not StrategyAction.IGNORE:
            canonical.append(item)
    return canonical


def failure_result(
    target: StrategyRunTarget,
    stage: StrategyRunStage,
    error: BaseException,
) -> BatchRunResult:
    return BatchRunResult(
        failures=[
            StrategyRunFailure(
                target=target,
                stage=stage,
                error_type=error.__class__.__name__,
                message=_clean_error_message(error),
            )
        ]
    )


def run_strategy_target(
    exchange: Any,
    strategy: Any,
    target: StrategyRunTarget,
    *,
    purpose: StrategyPurpose,
    now: dt.datetime | None = None,
) -> BatchRunResult:
    try:
        target = strategy_target_from_stock(
            target.market,
            {"code": target.code, "name": target.name},
            target.frequency,
        )
    except Exception as error:
        return failure_result(target, "target", error)

    try:
        klines = exchange.klines(target.code, target.frequency)
    except Exception as error:
        return failure_result(target, "provider", error)

    try:
        prepared_klines = validate_strategy_klines(klines, target)
    except Exception as error:
        return failure_result(target, "input", error)

    try:
        context_now = _market_datetime(
            now or dt.datetime.now(tz=market_timezone(target.market)),
            target.market,
            "strategy context now",
        )
    except Exception as error:
        return failure_result(target, "input", error)

    context = StrategyContext(
        market=target.market,
        code=target.code,
        name=target.name,
        frequency=target.frequency,
        klines=prepared_klines,
        now=context_now,
    )
    try:
        raw_results = strategy.run(context)
    except Exception as error:
        return failure_result(target, "strategy", error)

    try:
        signals = validate_strategy_signals(
            raw_results,
            target,
            purpose=purpose,
            context_now=context_now,
        )
    except Exception as error:
        return failure_result(target, "output", error)

    if signals:
        return BatchRunResult(hits=signals)
    return BatchRunResult(misses=[target])
