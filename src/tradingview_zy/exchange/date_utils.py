from __future__ import annotations

import datetime as dt

from tradingview_zy import fun


def parse_optional_datetime(value, *, field_name: str) -> dt.datetime | None:
    """Parse an optional date boundary without assuming it is still a string."""

    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return fun.str_to_datetime(value.isoformat(), "%Y-%m-%d")
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be str, date, datetime, or None; "
            f"got {type(value).__name__}"
        )

    text = value.strip()
    if text == "":
        raise ValueError(f"{field_name} cannot be empty")
    if len(text) == 10:
        return fun.str_to_datetime(text, "%Y-%m-%d")

    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return fun.str_to_datetime(text)
    if parsed.tzinfo is None:
        return fun.str_to_datetime(parsed.strftime("%Y-%m-%d %H:%M:%S"))
    return parsed
