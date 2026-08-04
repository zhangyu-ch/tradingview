"""Fine-grained exchange capabilities and stable public error contracts."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


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
