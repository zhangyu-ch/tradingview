"""Fine-grained exchange capabilities and stable public error contracts."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, TypeVar, runtime_checkable

from tradingview_zy.base import Market


class Capability(StrEnum):
    """Observable provider behaviours exposed by the standard factory."""

    METADATA = "metadata"
    MARKET_DATA = "market_data"
    TICKS = "ticks"
    CATALOG = "catalog"
    SECURITY_MASTER = "security_master"
    SESSION_STATUS = "session_status"
    PLATES = "plates"
    ACCOUNT_BALANCE = "account_balance"
    POSITIONS = "positions"
    LIVE_ORDERS = "live_orders"


class Frequency(StrEnum):
    """Canonical internal K-line frequency codes."""

    YEAR = "y"
    QUARTER = "q"
    MONTH = "m"
    WEEK = "w"
    DAY = "d"
    HOUR_12 = "12h"
    HOUR_8 = "8h"
    HOUR_6 = "6h"
    HOUR_4 = "4h"
    HOUR_3 = "3h"
    MINUTE_120 = "120m"
    MINUTE_60 = "60m"
    MINUTE_30 = "30m"
    MINUTE_15 = "15m"
    MINUTE_10 = "10m"
    MINUTE_6 = "6m"
    MINUTE_5 = "5m"
    MINUTE_3 = "3m"
    MINUTE_2 = "2m"
    MINUTE_1 = "1m"
    SECOND_30 = "30s"
    SECOND_10 = "10s"


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class PositionSide(StrEnum):
    LONG = "long"
    SHORT = "short"


class OrderOffset(StrEnum):
    OPEN = "open"
    CLOSE = "close"
    CLOSE_TODAY = "close_today"


class OrderStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class OperationAction(StrEnum):
    """Legacy backtest operation semantics with stable persisted values.

    The historical runtime uses ``buy`` for open and ``sell`` for close even
    when the position itself is short.  The enum names expose the actual
    semantics while retaining byte-compatible values.
    """

    OPEN = "buy"
    CLOSE = "sell"


class TradeMode(StrEnum):
    SIGNAL = "signal"
    TRADE = "trade"


_DomainCode = TypeVar("_DomainCode", bound=StrEnum)


def _normalise_domain_code(value: Any, *, field: str, max_length: int = 32) -> str:
    if isinstance(value, StrEnum):
        value = value.value
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string or enum")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{field} contains control characters")
    token = value.strip().lower()
    if not token:
        raise ValueError(f"{field} must not be empty")
    if len(token) > max_length:
        raise ValueError(f"{field} exceeds {max_length} characters")
    return token


def _parse_domain_code(
    value: Any, enum_type: type[_DomainCode], *, field: str, aliases: dict[str, _DomainCode] | None = None
) -> _DomainCode:
    if isinstance(value, enum_type):
        return value
    token = _normalise_domain_code(value, field=field)
    if aliases and token in aliases:
        return aliases[token]
    try:
        return enum_type(token)
    except ValueError as error:
        raise ValueError(f"unsupported {field}: {token!r}") from error


def parse_frequency(value: Any) -> Frequency:
    return _parse_domain_code(value, Frequency, field="frequency")


def parse_order_side(value: Any) -> OrderSide:
    return _parse_domain_code(value, OrderSide, field="order side")


def parse_position_side(value: Any) -> PositionSide:
    return _parse_domain_code(
        value,
        PositionSide,
        field="position side",
        aliases={"做多": PositionSide.LONG, "做空": PositionSide.SHORT},
    )


def parse_order_offset(value: Any) -> OrderOffset:
    return _parse_domain_code(
        value,
        OrderOffset,
        field="order offset",
        aliases={"closetoday": OrderOffset.CLOSE_TODAY},
    )


def parse_order_status(value: Any) -> OrderStatus:
    return _parse_domain_code(
        value,
        OrderStatus,
        field="order status",
        aliases={
            "cancelled": OrderStatus.CANCELED,
            "partial_filled": OrderStatus.PARTIALLY_FILLED,
        },
    )


def parse_operation_action(value: Any) -> OperationAction:
    return _parse_domain_code(
        value,
        OperationAction,
        field="operation action",
        aliases={
            "open": OperationAction.OPEN,
            "buy": OperationAction.OPEN,
            "close": OperationAction.CLOSE,
            "sell": OperationAction.CLOSE,
        },
    )


def parse_trade_mode(value: Any) -> TradeMode:
    return _parse_domain_code(value, TradeMode, field="trade mode")


CAPABILITY_METHODS: dict[Capability, tuple[str, ...]] = {
    Capability.METADATA: ("default_code", "support_frequencys"),
    Capability.MARKET_DATA: ("klines",),
    Capability.TICKS: ("ticks",),
    Capability.CATALOG: ("all_stocks", "stock_info"),
    Capability.SECURITY_MASTER: ("all_stocks", "stock_info"),
    Capability.SESSION_STATUS: ("now_trading",),
    Capability.PLATES: ("stock_owner_plate", "plate_stocks"),
    Capability.ACCOUNT_BALANCE: ("balance",),
    Capability.POSITIONS: ("positions",),
    Capability.LIVE_ORDERS: ("order",),
}


class ExchangeError(RuntimeError):
    """Base class whose public representation never reflects SDK exception text."""

    code = "exchange_error"
    retryable = False
    default_message = "交易所请求失败"

    def __init__(self, message: str | None = None, *, provider: str | None = None):
        self.public_message = message or self.default_message
        self.provider = provider
        super().__init__(self.public_message)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.public_message,
            "retryable": self.retryable,
        }
        if self.provider:
            payload["provider"] = self.provider
        return payload


class InvalidRequestError(ExchangeError):
    code = "invalid_exchange_request"
    default_message = "交易所请求参数无效"


class UnsupportedProviderError(ExchangeError):
    code = "unsupported_provider"
    default_message = "配置的交易所数据源不受支持"


class UnsupportedCapabilityError(ExchangeError):
    code = "unsupported_capability"
    default_message = "该数据源不支持请求的能力"


class ProviderUnavailableError(ExchangeError):
    code = "provider_unavailable"
    retryable = True
    default_message = "交易所数据源暂时不可用"


class ProviderResponseError(ExchangeError):
    code = "provider_response_invalid"
    default_message = "交易所数据源返回了无效响应"


@runtime_checkable
class MetadataProvider(Protocol):
    def default_code(self) -> str: ...

    def support_frequencys(self) -> dict[str, str]: ...


@runtime_checkable
class MarketDataProvider(Protocol):
    def klines(self, code: str, frequency: str, start_date=None, end_date=None, args=None): ...


@runtime_checkable
class TickProvider(Protocol):
    def ticks(self, codes: list[str]): ...


@runtime_checkable
class CatalogProvider(Protocol):
    def all_stocks(self): ...

    def stock_info(self, code: str): ...


@runtime_checkable
class SessionProvider(Protocol):
    def now_trading(self, code: str | None = None, at=None) -> bool: ...
