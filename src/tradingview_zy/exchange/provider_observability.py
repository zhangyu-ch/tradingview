"""Stable, secret-free logging for heterogeneous provider SDK boundaries."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from tradingview_zy.domain import ProviderResponseError, ProviderUnavailableError

T = TypeVar("T")


def _safe_log_value(value: object, *, fallback: str = "-") -> str:
    text = str(value or fallback).strip() or fallback
    text = "".join(character if ord(character) >= 32 else "?" for character in text)
    return text[:128]


def call_provider(
    operation: Callable[[], T],
    *,
    logger: logging.Logger,
    provider: str,
    market: str,
    code: str,
    operation_name: str,
    request_id: str | None = None,
) -> T:
    """Execute one vendor call and expose only stable error/log fields.

    Third-party SDKs do not share a reliable base exception.  The single broad
    catch below is therefore the explicit integration boundary; individual
    adapters must not repeat ``except Exception`` or print raw SDK messages.
    """

    log_fields = (
        _safe_log_value(market),
        _safe_log_value(code),
        _safe_log_value(request_id),
        _safe_log_value(operation_name),
        _safe_log_value(provider),
    )
    try:
        return operation()
    except (TimeoutError, ConnectionError, OSError) as error:
        logger.warning(
            "provider_call_failed market=%s code=%s request_id=%s operation=%s provider=%s error_type=%s",
            *log_fields,
            type(error).__name__,
        )
        raise ProviderUnavailableError(provider=provider) from error
    except Exception as error:  # noqa: BLE001 - deliberate heterogeneous SDK boundary
        logger.error(
            "provider_call_failed market=%s code=%s request_id=%s operation=%s provider=%s error_type=%s",
            *log_fields,
            type(error).__name__,
        )
        raise ProviderResponseError(provider=provider) from error
