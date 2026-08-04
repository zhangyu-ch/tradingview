from __future__ import annotations

import re
from collections.abc import Mapping, Iterable
from typing import Any

from tradingview_zy.domain import Frequency, parse_frequency

_POSITIVE_INT_RE = re.compile(r"[1-9][0-9]*\Z")
_CANONICAL_INT_RE = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


class WebParameterError(ValueError):
    """Stable validation failure for public Web/API parameters."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def _has_control_character(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) == 127 for char in value)


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


def parse_int(
    value: Any,
    *,
    field: str,
    minimum: int = -(2**63),
    maximum: int = 2**63 - 1,
) -> int:
    if isinstance(value, bool) or value is None:
        raise WebParameterError(field, f"{field} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and _CANONICAL_INT_RE.fullmatch(value):
        result = int(value)
    else:
        raise WebParameterError(field, f"{field} must be an integer")
    if result < minimum or result > maximum:
        raise WebParameterError(field, f"{field} is out of range")
    return result


def parse_strict_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise WebParameterError(field, f"{field} must be true or false")


def parse_bounded_text(
    value: Any,
    *,
    field: str,
    max_chars: int = 200,
    max_bytes: int | None = None,
    allow_empty: bool = False,
) -> str:
    """Normalize public text without accepting controls or unbounded payloads."""

    if not isinstance(value, str):
        raise WebParameterError(field, f"{field} must be text")
    result = value.strip()
    if not allow_empty and result == "":
        raise WebParameterError(field, f"{field} must not be empty")
    if len(result) > max_chars:
        raise WebParameterError(field, f"{field} is too long")
    if max_bytes is not None and len(result.encode("utf-8")) > max_bytes:
        raise WebParameterError(field, f"{field} is too long")
    if _has_control_character(result):
        raise WebParameterError(field, f"{field} contains control characters")
    return result


def parse_market(
    value: Any,
    *,
    allowed_markets: Iterable[str],
    field: str = "market",
) -> str:
    market = parse_bounded_text(value, field=field, max_chars=32).lower()
    allowed = {str(item).lower() for item in allowed_markets}
    if market not in allowed:
        raise WebParameterError(field, f"unsupported {field}")
    return market


def parse_symbol(
    value: Any,
    *,
    allowed_markets: Iterable[str],
    field: str = "symbol",
    max_code_bytes: int = 128,
) -> tuple[str, str]:
    symbol = parse_bounded_text(value, field=field, max_chars=260, max_bytes=512)
    if symbol.count(":") != 1:
        raise WebParameterError(field, f"{field} must be market:code")
    market_raw, code_raw = symbol.split(":", 1)
    market = parse_market(market_raw, allowed_markets=allowed_markets, field="market")
    code = parse_bounded_text(
        code_raw,
        field="code",
        max_chars=200,
        max_bytes=max_code_bytes,
    )
    return market, code


def parse_resolution(
    value: Any,
    *,
    resolution_map: Mapping[str, str],
    field: str = "resolution",
) -> tuple[str, Frequency]:
    resolution = parse_bounded_text(value, field=field, max_chars=16)
    if resolution not in resolution_map:
        raise WebParameterError(field, "unsupported resolution")
    try:
        frequency = parse_frequency(resolution_map[resolution])
    except (TypeError, ValueError) as error:
        raise WebParameterError(field, "unsupported internal frequency") from error
    return resolution, frequency


def parse_time_range(from_value: Any, to_value: Any) -> tuple[int, int]:
    start = parse_int(from_value, field="from")
    end = parse_int(to_value, field="to")
    if start > end:
        raise WebParameterError("from/to", "from must not exceed to")
    return start, end
