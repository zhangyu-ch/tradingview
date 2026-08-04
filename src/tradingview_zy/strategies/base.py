from __future__ import annotations

import datetime as dt
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from tradingview_zy.web_payloads import normalize_klines_for_market

StrategyAction = Literal["select", "watch", "buy", "sell", "open", "close", "ignore"]
StrategyRunStage = Literal["target", "provider", "input", "strategy", "output"]

_REQUIRED_KLINE_COLUMNS = ("date", "open", "close", "high", "low", "volume")
_ALLOWED_ACTIONS = {"select", "watch", "buy", "sell", "open", "close", "ignore"}


@dataclass(frozen=True)
class StrategyContext:
    market: str
    code: str
    name: str
    frequency: str
    klines: pd.DataFrame
    now: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategySignal:
    code: str
    name: str
    action: StrategyAction
    score: float
    message: str
    frequency: str
    event_time: dt.datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyRunTarget:
    market: str
    code: str
    name: str
    frequency: str


@dataclass(frozen=True)
class StrategyRunFailure:
    target: StrategyRunTarget
    stage: StrategyRunStage
    error_type: str
    message: str

    @property
    def market(self) -> str:
        return self.target.market

    @property
    def code(self) -> str:
        return self.target.code

    @property
    def name(self) -> str:
        return self.target.name

    @property
    def frequency(self) -> str:
        return self.target.frequency


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

    # Keep the historical signal-list read API usable while callers migrate to
    # explicit hits/misses/failures handling.
    def __iter__(self):
        return iter(self.hits)

    def __len__(self) -> int:
        return len(self.hits)

    def __getitem__(self, index):
        return self.hits[index]


class StrategyInputError(ValueError):
    """Raised when provider data violates the strategy K-line contract."""


def normalize_strategy_results(results: Any) -> list[StrategySignal]:
    if results is None:
        return []
    if isinstance(results, StrategySignal):
        return [results]
    if isinstance(results, list) and all(isinstance(item, StrategySignal) for item in results):
        return results
    raise TypeError("strategy run() must return StrategySignal, list[StrategySignal], or None")


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
    market_value = _validate_text(market, "market", 32)
    code = _validate_text(stock.get("code"), "code", 128)
    raw_name = stock.get("name", code)
    name = _validate_text(raw_name, "name", 256)
    frequency_value = _validate_text(frequency, "frequency", 32)
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


def _validate_strategy_signals(
    signals: list[StrategySignal],
    target: StrategyRunTarget,
) -> list[StrategySignal]:
    for signal in signals:
        if signal.code != target.code:
            raise ValueError("strategy signal code does not match the target")
        if signal.frequency != target.frequency:
            raise ValueError("strategy signal frequency does not match the target")
        if signal.action not in _ALLOWED_ACTIONS:
            raise ValueError("strategy signal action is unsupported")
        if isinstance(signal.score, bool) or not isinstance(signal.score, (int, float)):
            raise TypeError("strategy signal score must be numeric")
        if not math.isfinite(float(signal.score)):
            raise ValueError("strategy signal score must be finite")
        if not isinstance(signal.message, str):
            raise TypeError("strategy signal message must be a string")
        if not isinstance(signal.event_time, dt.datetime):
            raise TypeError("strategy signal event_time must be a datetime")
    return signals


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
    now: dt.datetime | None = None,
) -> BatchRunResult:
    try:
        # Targets constructed outside the standard runner still receive the same
        # validation before any provider side effect.
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

    context = StrategyContext(
        market=target.market,
        code=target.code,
        name=target.name,
        frequency=target.frequency,
        klines=prepared_klines,
        now=now or dt.datetime.now(),
    )
    try:
        raw_results = strategy.run(context)
    except Exception as error:
        return failure_result(target, "strategy", error)

    try:
        signals = _validate_strategy_signals(
            normalize_strategy_results(raw_results), target
        )
    except Exception as error:
        return failure_result(target, "output", error)

    if signals:
        return BatchRunResult(hits=signals)
    return BatchRunResult(misses=[target])
