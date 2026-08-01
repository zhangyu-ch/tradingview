"""Stable domain contracts shared by market, strategy and trading adapters.

The project historically passed primitive strings and unstructured ``dict``
objects between modules.  These types make invalid states easy to construct and
make provider failures indistinguishable from an empty result.  This module
contains the small, dependency-free contracts used at those boundaries.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class TradingViewError(RuntimeError):
    """Base class for expected, user-facing domain failures."""


class InvalidRequestError(TradingViewError):
    """The caller supplied an invalid market, payload or state transition."""


class ProviderUnavailableError(TradingViewError):
    """The selected external provider could not serve the request."""


class UnsupportedCapabilityError(TradingViewError):
    """The selected provider does not implement a requested capability."""


class DataContractError(TradingViewError):
    """Data crossed a module boundary without satisfying its schema."""


class Capability(str, Enum):
    MARKET_DATA = "market_data"
    TICKS = "ticks"
    SECURITY_MASTER = "security_master"
    PLATES = "plates"
    ACCOUNT_BALANCE = "account_balance"
    POSITIONS = "positions"
    TRADING_EXECUTION = "trading_execution"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderStatus(str, Enum):
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"

    @property
    def terminal(self) -> bool:
        return self in {self.FILLED, self.CANCELLED, self.REJECTED}


@dataclass(frozen=True, slots=True)
class OrderRequest:
    market: str
    code: str
    side: OrderSide
    amount: float
    client_order_id: str
    position_side: PositionSide = PositionSide.LONG
    limit_price: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.market or not self.code or not self.client_order_id:
            raise InvalidRequestError("订单必须包含 market、code 和 client_order_id")
        if not math.isfinite(float(self.amount)) or self.amount <= 0:
            raise InvalidRequestError("订单数量必须是有限正数")
        if self.limit_price is not None and (
            not math.isfinite(float(self.limit_price)) or self.limit_price <= 0
        ):
            raise InvalidRequestError("限价必须是有限正数")


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    fill_id: str
    code: str
    side: OrderSide
    amount: float
    price: float
    fee: float
    filled_at: dt.datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.order_id or not self.fill_id or not self.code:
            raise InvalidRequestError("成交必须包含 order_id、fill_id 和 code")
        numeric = (self.amount, self.price, self.fee)
        if not all(math.isfinite(float(value)) for value in numeric):
            raise InvalidRequestError("成交数量、价格和手续费必须为有限值")
        if self.amount <= 0 or self.price <= 0 or self.fee < 0:
            raise InvalidRequestError("成交数量/价格必须为正，手续费不得为负")
        if self.filled_at.tzinfo is None:
            raise InvalidRequestError("成交时间必须带时区")


@dataclass(frozen=True, slots=True)
class OrderState:
    client_order_id: str
    provider_order_id: str | None
    status: OrderStatus
    requested_amount: float
    filled_amount: float = 0.0
    average_fill_price: float | None = None
    fills: tuple[Fill, ...] = ()
    message: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.requested_amount)) or self.requested_amount <= 0:
            raise InvalidRequestError("requested_amount 必须是有限正数")
        if not math.isfinite(float(self.filled_amount)):
            raise InvalidRequestError("filled_amount 必须是有限值")
        if self.filled_amount < 0 or self.filled_amount > self.requested_amount:
            raise InvalidRequestError("filled_amount 超出订单数量范围")
        total = sum(fill.amount for fill in self.fills)
        if abs(total - self.filled_amount) > max(1e-10, self.requested_amount * 1e-10):
            raise InvalidRequestError("成交明细数量与 filled_amount 不一致")
