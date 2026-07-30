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
