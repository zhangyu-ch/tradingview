from __future__ import annotations

import re
from typing import Any

_POSITIVE_INT_RE = re.compile(r"[1-9][0-9]*\Z")


class WebParameterError(ValueError):
    """Stable validation failure for public Web/API parameters."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def parse_positive_int(value: Any, *, field: str, maximum: int = 2**63 - 1) -> int:
    """Accept a canonical positive integer and reject bool/leading-zero variants."""

    if isinstance(value, bool) or value is None:
        raise WebParameterError(field, f"{field} must be a positive integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and _POSITIVE_INT_RE.fullmatch(value):
        result = int(value)
    else:
        raise WebParameterError(field, f"{field} must be a positive integer")
    if result <= 0 or result > maximum:
        raise WebParameterError(field, f"{field} must be a positive integer")
    return result


def parse_bounded_text(
    value: Any,
    *,
    field: str,
    max_chars: int = 200,
    allow_empty: bool = False,
) -> str:
    """Normalize a short public text parameter without accepting control characters."""

    if not isinstance(value, str):
        raise WebParameterError(field, f"{field} must be text")
    result = value.strip()
    if not allow_empty and result == "":
        raise WebParameterError(field, f"{field} must not be empty")
    if len(result) > max_chars:
        raise WebParameterError(field, f"{field} is too long")
    if any(ord(char) < 32 or ord(char) == 127 for char in result):
        raise WebParameterError(field, f"{field} contains control characters")
    return result
