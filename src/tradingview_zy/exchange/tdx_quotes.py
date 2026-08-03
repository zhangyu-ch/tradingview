from __future__ import annotations

import math
from typing import Any


def calculate_change_rate(last: Any, previous_close: Any) -> float | None:
    """Return the percentage change using the previous close as denominator.

    A missing, non-finite or non-positive price is not a valid zero-percent move.
    Returning ``None`` preserves that distinction through the API and UI instead
    of silently presenting unavailable market data as an unchanged quote.
    """
    try:
        last_value = float(last)
        previous_value = float(previous_close)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(last_value) or not math.isfinite(previous_value):
        return None
    if last_value <= 0 or previous_value <= 0:
        return None
    return round((last_value - previous_value) / previous_value * 100.0, 2)
