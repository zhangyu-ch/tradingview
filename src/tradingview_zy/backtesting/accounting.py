from __future__ import annotations

import math
from typing import Iterable


class BackTestAccountingError(ValueError):
    """Raised when a fill would make the backtest position internally inconsistent."""


_MIN_ABSOLUTE_TOLERANCE = 1e-15
_ULP_MULTIPLIER = 8


def _finite_float(value: float, *, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise BackTestAccountingError(f"{label} must be finite, got {value!r}")
    return number


def quantity_tolerance(*values: float) -> float:
    """Return a scale-aware tolerance for quantities represented as floats.

    The absolute floor handles ordinary fractional assets (for example crypto), while
    the ULP term scales for very large quantities without introducing a broad relative
    tolerance that would hide a materially open position.
    """

    finite_values: Iterable[float] = (
        abs(_finite_float(value, label="quantity")) for value in values
    )
    scale = max([1.0, *finite_values])
    return max(_MIN_ABSOLUTE_TOLERANCE, math.ulp(scale) * _ULP_MULTIPLIER)


def normalize_nonnegative_quantity(
    value: float, *, label: str = "quantity", scale_values: tuple[float, ...] = ()
) -> float:
    """Clamp a floating-point residue to exactly zero and reject material negatives."""

    number = _finite_float(value, label=label)
    tolerance = quantity_tolerance(number, *scale_values)
    if number < -tolerance:
        raise BackTestAccountingError(f"{label} cannot be negative: {number}")
    if abs(number) <= tolerance:
        return 0.0
    return number


def add_quantity(current: float, added: float, *, label: str = "quantity") -> float:
    current_number = normalize_nonnegative_quantity(current, label=label)
    added_number = normalize_nonnegative_quantity(added, label=f"added {label}")
    return normalize_nonnegative_quantity(
        math.fsum((current_number, added_number)),
        label=label,
        scale_values=(current_number, added_number),
    )


def subtract_quantity(
    current: float, removed: float, *, label: str = "quantity"
) -> float:
    current_number = normalize_nonnegative_quantity(current, label=label)
    removed_number = normalize_nonnegative_quantity(removed, label=f"removed {label}")
    tolerance = quantity_tolerance(current_number, removed_number)
    if removed_number > current_number + tolerance:
        raise BackTestAccountingError(
            f"removed {label} {removed_number} exceeds current {label} {current_number}"
        )
    return normalize_nonnegative_quantity(
        math.fsum((current_number, -removed_number)),
        label=label,
        scale_values=(current_number, removed_number),
    )


def is_zero_quantity(value: float) -> bool:
    return normalize_nonnegative_quantity(value) == 0.0


def quantities_close(left: float, right: float) -> bool:
    left_number = _finite_float(left, label="left quantity")
    right_number = _finite_float(right, label="right quantity")
    return abs(left_number - right_number) <= quantity_tolerance(
        left_number, right_number
    )


def weighted_average_price(
    current_price: float,
    current_amount: float,
    fill_price: float,
    fill_amount: float,
) -> float:
    """Calculate the volume-weighted entry price after an additional opening fill."""

    existing_amount = normalize_nonnegative_quantity(
        current_amount, label="current amount"
    )
    added_amount = normalize_nonnegative_quantity(fill_amount, label="fill amount")
    if added_amount == 0.0:
        raise BackTestAccountingError("fill amount must be greater than zero")

    fill_price_number = _finite_float(fill_price, label="fill price")
    if fill_price_number <= 0:
        raise BackTestAccountingError(f"fill price must be positive: {fill_price_number}")

    if existing_amount == 0.0:
        return fill_price_number

    current_price_number = _finite_float(current_price, label="current price")
    if current_price_number <= 0:
        raise BackTestAccountingError(
            f"current price must be positive when a position exists: {current_price_number}"
        )

    total_amount = add_quantity(existing_amount, added_amount, label="position amount")
    weighted_value = math.fsum(
        (
            current_price_number * existing_amount,
            fill_price_number * added_amount,
        )
    )
    if not math.isfinite(weighted_value):
        raise BackTestAccountingError("weighted position value must be finite")
    average_price = weighted_value / total_amount
    if not math.isfinite(average_price) or average_price <= 0:
        raise BackTestAccountingError(
            f"weighted average price must be positive and finite: {average_price}"
        )
    return average_price

# ---------------------------------------------------------------------------
# FIFO lot accounting used by incremental close and A-share T+1 validation.
# ---------------------------------------------------------------------------
import datetime as _datetime
from dataclasses import dataclass


@dataclass(slots=True)
class PositionLot:
    opened_at: _datetime.datetime
    amount: float
    price: float
    hold_balance: float
    opening_fee: float
    pos_rate: float

    def __post_init__(self) -> None:
        self.amount = normalize_nonnegative_quantity(self.amount, label="lot amount")
        self.hold_balance = normalize_nonnegative_quantity(
            self.hold_balance, label="lot hold balance"
        )
        self.opening_fee = normalize_nonnegative_quantity(
            self.opening_fee, label="lot opening fee"
        )
        self.pos_rate = normalize_nonnegative_quantity(
            self.pos_rate, label="lot position rate"
        )
        self.price = _finite_float(self.price, label="lot price")
        if self.amount == 0 or self.price <= 0:
            raise BackTestAccountingError("lot amount and price must be positive")

    def is_sellable(self, as_of: _datetime.datetime, can_close_today: bool) -> bool:
        return can_close_today or self.opened_at.date() < as_of.date()


@dataclass(frozen=True, slots=True)
class LotConsumption:
    amount: float
    hold_balance: float
    opening_fee: float
    pos_rate: float
    weighted_open_price: float


def available_lot_amount(
    lots: Iterable[PositionLot],
    *,
    as_of: _datetime.datetime,
    can_close_today: bool,
) -> float:
    return math.fsum(
        lot.amount for lot in lots if lot.is_sellable(as_of, can_close_today)
    )


def consume_fifo_lots(
    lots: list[PositionLot],
    amount: float,
    *,
    as_of: _datetime.datetime,
    can_close_today: bool,
) -> LotConsumption:
    """Consume sellable lots in FIFO order and mutate remaining quantities.

    Opening fee, logical position rate and held capital are allocated in the
    same proportion as quantity. A material over-consumption is rejected before
    any caller-visible accounting state is committed.
    """
    requested = normalize_nonnegative_quantity(amount, label="close amount")
    if requested == 0:
        raise BackTestAccountingError("close amount must be greater than zero")
    available = available_lot_amount(
        lots, as_of=as_of, can_close_today=can_close_today
    )
    if requested > available + quantity_tolerance(requested, available):
        raise BackTestAccountingError(
            f"close amount {requested} exceeds sellable lot amount {available}"
        )

    remaining = requested
    consumed_hold = 0.0
    consumed_fee = 0.0
    consumed_rate = 0.0
    consumed_value = 0.0
    for lot in lots:
        if remaining == 0 or not lot.is_sellable(as_of, can_close_today):
            continue
        take = min(lot.amount, remaining)
        fraction = take / lot.amount
        consumed_hold += lot.hold_balance * fraction
        consumed_fee += lot.opening_fee * fraction
        consumed_rate += lot.pos_rate * fraction
        consumed_value += lot.price * take
        lot.amount = subtract_quantity(lot.amount, take, label="lot amount")
        lot.hold_balance = normalize_nonnegative_quantity(
            lot.hold_balance * (1.0 - fraction), label="lot hold balance"
        )
        lot.opening_fee = normalize_nonnegative_quantity(
            lot.opening_fee * (1.0 - fraction), label="lot opening fee"
        )
        lot.pos_rate = normalize_nonnegative_quantity(
            lot.pos_rate * (1.0 - fraction), label="lot position rate"
        )
        remaining = subtract_quantity(remaining, take, label="close amount")

    lots[:] = [lot for lot in lots if not is_zero_quantity(lot.amount)]
    if not is_zero_quantity(remaining):
        raise BackTestAccountingError(f"FIFO lot consumption left residue {remaining}")
    return LotConsumption(
        amount=requested,
        hold_balance=consumed_hold,
        opening_fee=consumed_fee,
        pos_rate=consumed_rate,
        weighted_open_price=consumed_value / requested,
    )


def close_settlement(
    *,
    direction: str,
    consumption: LotConsumption,
    close_price: float,
    closing_fee: float,
    futures_symbol_size: float | None = None,
) -> tuple[float, float]:
    """Return ``(cash_delta, realised_profit)`` for one close fill."""
    close_price = _finite_float(close_price, label="close price")
    closing_fee = normalize_nonnegative_quantity(closing_fee, label="closing fee")
    if close_price <= 0:
        raise BackTestAccountingError("close price must be positive")
    if direction not in {"long", "short"}:
        raise BackTestAccountingError(f"unsupported direction: {direction}")

    if futures_symbol_size is not None:
        size = _finite_float(futures_symbol_size, label="futures symbol size")
        if size <= 0:
            raise BackTestAccountingError("futures symbol size must be positive")
        price_delta = (
            close_price - consumption.weighted_open_price
            if direction == "long"
            else consumption.weighted_open_price - close_price
        )
        gross_profit = price_delta * consumption.amount * size
        realised = gross_profit - consumption.opening_fee - closing_fee
        cash_delta = consumption.hold_balance + gross_profit - closing_fee
        return cash_delta, realised

    close_notional = close_price * consumption.amount
    if direction == "long":
        cash_delta = close_notional - closing_fee
        realised = (
            close_notional
            - consumption.hold_balance
            - consumption.opening_fee
            - closing_fee
        )
    else:
        # Existing backtest cash semantics reserve the short notional on open.
        # Closing restores that reserve plus P&L.
        cash_delta = 2 * consumption.hold_balance - close_notional - closing_fee
        realised = (
            consumption.hold_balance
            - close_notional
            - consumption.opening_fee
            - closing_fee
        )
    return cash_delta, realised
