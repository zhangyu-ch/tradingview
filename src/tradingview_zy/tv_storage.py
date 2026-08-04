"""Capacity, validation and quota policy for TradingView-compatible storage."""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from typing import Any


class TVStorageError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TVStorageFieldError(TVStorageError):
    def __init__(self, message: str) -> None:
        super().__init__("storage_field_too_large", message)


class TVStorageQuotaError(TVStorageError):
    def __init__(self, message: str) -> None:
        super().__init__("storage_quota_exceeded", message)


@dataclass(frozen=True, slots=True)
class TVStoragePolicy:
    chart_max_bytes: int = 512 * 1024
    template_max_bytes: int = 256 * 1024
    drawing_max_bytes: int = 512 * 1024
    max_charts: int = 100
    max_templates: int = 200
    max_drawings: int = 2000
    max_total_bytes: int = 16 * 1024 * 1024

    @classmethod
    def from_config(cls, config: Any) -> "TVStoragePolicy":
        defaults = cls()
        values = {
            "chart_max_bytes": getattr(config, "TV_STORAGE_CHART_MAX_BYTES", defaults.chart_max_bytes),
            "template_max_bytes": getattr(config, "TV_STORAGE_TEMPLATE_MAX_BYTES", defaults.template_max_bytes),
            "drawing_max_bytes": getattr(config, "TV_STORAGE_DRAWING_MAX_BYTES", defaults.drawing_max_bytes),
            "max_charts": getattr(config, "TV_STORAGE_MAX_CHARTS", defaults.max_charts),
            "max_templates": getattr(config, "TV_STORAGE_MAX_TEMPLATES", defaults.max_templates),
            "max_drawings": getattr(config, "TV_STORAGE_MAX_DRAWINGS", defaults.max_drawings),
            "max_total_bytes": getattr(config, "TV_STORAGE_MAX_TOTAL_BYTES", defaults.max_total_bytes),
        }
        normalized = {key: int(value) for key, value in values.items()}
        if any(value <= 0 for value in normalized.values()):
            raise ValueError("TradingView storage limits must be positive integers")
        return cls(**normalized)

    def max_blob_bytes(self, kind: str) -> int:
        if kind == "chart":
            return self.chart_max_bytes
        if kind == "template":
            return self.template_max_bytes
        if kind == "drawing":
            return self.drawing_max_bytes
        raise ValueError(f"unsupported storage kind: {kind!r}")

    def max_records(self, kind: str) -> int:
        if kind == "chart":
            return self.max_charts
        if kind == "template":
            return self.max_templates
        if kind == "drawing":
            return self.max_drawings
        raise ValueError(f"unsupported storage kind: {kind!r}")


def utf8_size(value: str, *, field: str) -> int:
    if not isinstance(value, str):
        raise TVStorageFieldError(f"{field} must be a string")
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise TVStorageFieldError(f"{field} contains invalid Unicode") from error


def normalize_identifier(
    value: Any,
    *,
    field: str,
    max_bytes: int,
    allow_empty: bool = False,
) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        value = str(value)
    normalized = value.strip()
    if not allow_empty and normalized == "":
        raise TVStorageFieldError(f"{field} is required")
    for character in normalized:
        if character == "\x00" or unicodedata.category(character) in {"Cc", "Cs"}:
            raise TVStorageFieldError(f"{field} contains control characters")
    size = utf8_size(normalized, field=field)
    if size > max_bytes:
        raise TVStorageFieldError(f"{field} exceeds {max_bytes} UTF-8 bytes")
    return normalized


def normalize_blob(value: Any, *, field: str, max_bytes: int) -> str:
    if isinstance(value, str):
        blob = value
    else:
        try:
            blob = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise TVStorageFieldError(f"{field} is not serializable JSON") from error
    size = utf8_size(blob, field=field)
    if size > max_bytes:
        raise TVStorageFieldError(f"{field} exceeds {max_bytes} UTF-8 bytes")
    return blob


def normalize_owner(client_id: Any, user_id: Any) -> tuple[str, str]:
    return (
        normalize_identifier(client_id, field="client", max_bytes=50),
        normalize_identifier(user_id, field="user", max_bytes=50),
    )


def normalize_chart_payload(
    policy: TVStoragePolicy,
    *,
    chart_type: str,
    client_id: Any,
    user_id: Any,
    name: Any,
    content: Any,
    symbol: Any,
    resolution: Any,
) -> dict[str, str]:
    if chart_type not in {"chart", "template"}:
        raise TVStorageFieldError("chart_type must be chart or template")
    client, user = normalize_owner(client_id, user_id)
    return {
        "chart_type": chart_type,
        "client_id": client,
        "user_id": user,
        "name": normalize_identifier(name, field="name", max_bytes=50),
        "content": normalize_blob(
            content,
            field="content",
            max_bytes=policy.max_blob_bytes(chart_type),
        ),
        "symbol": normalize_identifier(
            symbol,
            field="symbol",
            max_bytes=50,
            allow_empty=chart_type == "template",
        ),
        "resolution": normalize_identifier(
            resolution,
            field="resolution",
            max_bytes=20,
            allow_empty=chart_type == "template",
        ),
    }


def normalize_drawing_payload(
    policy: TVStoragePolicy,
    *,
    client_id: Any,
    user_id: Any,
    layout_id: Any,
    chart_id: Any,
    symbol: Any,
    state: Any,
) -> dict[str, str]:
    client, user = normalize_owner(client_id, user_id)
    return {
        "client_id": client,
        "user_id": user,
        "layout_id": normalize_identifier(layout_id, field="layout", max_bytes=100),
        "chart_id": normalize_identifier(chart_id, field="chart", max_bytes=100),
        "symbol": normalize_identifier(
            symbol, field="symbol", max_bytes=100, allow_empty=True
        ),
        "state": normalize_blob(
            state,
            field="state",
            max_bytes=policy.drawing_max_bytes,
        ),
    }


def enforce_quota(
    policy: TVStoragePolicy,
    *,
    kind: str,
    current_count: int,
    projected_count: int,
    current_total_bytes: int,
    projected_total_bytes: int,
) -> None:
    record_limit = policy.max_records(kind)
    if projected_count > record_limit and projected_count > current_count:
        raise TVStorageQuotaError(
            f"{kind} record quota exceeded: {projected_count} > {record_limit}"
        )
    if (
        projected_total_bytes > policy.max_total_bytes
        and projected_total_bytes > current_total_bytes
    ):
        raise TVStorageQuotaError(
            "combined TradingView storage quota exceeded: "
            f"{projected_total_bytes} > {policy.max_total_bytes} bytes"
        )
