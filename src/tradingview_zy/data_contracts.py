"""Immutable data-clump contracts at provider, strategy and order boundaries.

Internal pandas frames and third-party SDK objects remain implementation details.
At module boundaries, repeated field groups are materialized and validated once so
callers cannot silently omit, rename or mutate one field in the group.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import math
from dataclasses import dataclass, replace
from typing import Any, Mapping

from tradingview_zy.base import Market
from tradingview_zy.domain import (
    InvalidRequestError,
    OrderOffset,
    OrderSide,
    OrderStatus,
    parse_order_offset,
    parse_order_side,
    parse_order_status,
)
from tradingview_zy.market_registry import parse_market

DATA_CONTRACT_SCHEMA_VERSION = 1


class DataContractError(ValueError):
    """A repeated payload group cannot be represented without guessing."""


def _text(value: Any, field: str, *, maximum: int = 256, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise DataContractError(f"{field} contains control characters")
    result = value.strip()
    if not result and not allow_empty:
        raise DataContractError(f"{field} must not be empty")
    if len(result) > maximum:
        raise DataContractError(f"{field} exceeds {maximum} characters")
    return result


def _finite(value: Any, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise DataContractError(f"{field} must be finite")
    if minimum is not None and result < minimum:
        raise DataContractError(f"{field} must be at least {minimum}")
    return result


def _aware_datetime(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, dt.datetime):
        raise TypeError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DataContractError(f"{field} must be timezone-aware")
    return value


def _canonical_json_object(value: Any, field: str, *, maximum_bytes: int = 32 * 1024) -> str:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be an object")
    candidate = copy.deepcopy(dict(value))
    try:
        encoded = json.dumps(
            candidate,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise DataContractError(f"{field} must contain only JSON values") from error
    try:
        size = len(encoded.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise DataContractError(f"{field} contains invalid Unicode") from error
    if size > maximum_bytes:
        raise DataContractError(f"{field} exceeds {maximum_bytes} UTF-8 bytes")
    return encoded


@dataclass(frozen=True, slots=True)
class ProviderBarPayload:
    """One raw provider OHLCV row before timestamp normalization."""

    timestamp: Any
    open: float
    close: float
    high: float
    low: float
    volume: float

    def __post_init__(self) -> None:
        open_price = _finite(self.open, "open")
        close_price = _finite(self.close, "close")
        high_price = _finite(self.high, "high")
        low_price = _finite(self.low, "low")
        volume = _finite(self.volume, "volume", minimum=0.0)
        if high_price < max(open_price, close_price, low_price):
            raise DataContractError("high is inconsistent with OHLC values")
        if low_price > min(open_price, close_price, high_price):
            raise DataContractError("low is inconsistent with OHLC values")
        object.__setattr__(self, "open", open_price)
        object.__setattr__(self, "close", close_price)
        object.__setattr__(self, "high", high_price)
        object.__setattr__(self, "low", low_price)
        object.__setattr__(self, "volume", volume)

    def to_mapping(self, *, timestamp_field: str = "timestamp") -> dict[str, Any]:
        return {
            timestamp_field: self.timestamp,
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
        }


@dataclass(frozen=True, slots=True)
class KlineBar:
    """Canonical, timezone-aware OHLCV row exported by an adapter boundary."""

    code: str
    date: dt.datetime
    open: float
    close: float
    high: float
    low: float
    volume: float

    def __post_init__(self) -> None:
        code = _text(self.code, "code", maximum=64).upper()
        date = _aware_datetime(self.date, "date")
        payload = ProviderBarPayload(
            timestamp=date,
            open=self.open,
            close=self.close,
            high=self.high,
            low=self.low,
            volume=self.volume,
        )
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "date", date)
        for field in ("open", "close", "high", "low", "volume"):
            object.__setattr__(self, field, getattr(payload, field))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "date": self.date,
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
        }


@dataclass(frozen=True, slots=True)
class StrategyParameters:
    """Versioned strategy identity plus immutable canonical JSON parameters."""

    strategy_id: str = ""
    strategy_path: str = ""
    kwargs_json: str = "{}"
    schema_version: int = DATA_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DATA_CONTRACT_SCHEMA_VERSION:
            raise DataContractError("unsupported strategy parameter schema_version")
        strategy_id = _text(
            self.strategy_id, "strategy_id", maximum=128, allow_empty=True
        )
        strategy_path = _text(
            self.strategy_path, "strategy_path", maximum=512, allow_empty=True
        )
        if strategy_id and strategy_path:
            raise DataContractError("strategy_id and strategy_path are mutually exclusive")
        if not isinstance(self.kwargs_json, str):
            raise TypeError("strategy kwargs JSON must be a string")
        try:
            kwargs = json.loads(self.kwargs_json, parse_constant=lambda value: (_ for _ in ()).throw(DataContractError(f"strategy kwargs cannot contain {value}")))
        except DataContractError:
            raise
        except json.JSONDecodeError as error:
            raise DataContractError("strategy kwargs JSON is invalid") from error
        canonical = _canonical_json_object(kwargs, "strategy kwargs")
        object.__setattr__(self, "strategy_id", strategy_id)
        object.__setattr__(self, "strategy_path", strategy_path)
        object.__setattr__(self, "kwargs_json", canonical)

    @classmethod
    def create(
        cls,
        *,
        strategy_id: str = "",
        strategy_path: str = "",
        kwargs: Mapping[str, Any] | None = None,
    ) -> "StrategyParameters":
        return cls(
            strategy_id=strategy_id,
            strategy_path=strategy_path,
            kwargs_json=_canonical_json_object(kwargs or {}, "strategy kwargs"),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StrategyParameters":
        if not isinstance(value, Mapping):
            raise TypeError("strategy configuration must be an object")
        unknown = set(value) - {
            "schema_version",
            "strategy_id",
            "strategy_path",
            "strategy_kwargs",
        }
        if unknown:
            raise DataContractError(
                "strategy configuration contains unknown fields: "
                + ", ".join(sorted(map(str, unknown)))
            )
        schema_version = value.get("schema_version", DATA_CONTRACT_SCHEMA_VERSION)
        if isinstance(schema_version, bool) or not isinstance(schema_version, int):
            raise TypeError("strategy parameter schema_version must be an integer")
        return cls(
            strategy_id=value.get("strategy_id", ""),
            strategy_path=value.get("strategy_path", ""),
            kwargs_json=_canonical_json_object(
                value.get("strategy_kwargs", {}), "strategy kwargs"
            ),
            schema_version=schema_version,
        )

    @classmethod
    def from_json(cls, value: str) -> "StrategyParameters":
        if not isinstance(value, str):
            raise TypeError("strategy configuration JSON must be a string")
        try:
            parsed = json.loads(
                value,
                parse_constant=lambda constant: (_ for _ in ()).throw(
                    DataContractError(f"strategy configuration cannot contain {constant}")
                ),
            )
        except DataContractError:
            raise
        except json.JSONDecodeError as error:
            raise DataContractError("strategy configuration JSON is invalid") from error
        return cls.from_mapping(parsed)

    @property
    def kwargs(self) -> dict[str, Any]:
        return json.loads(self.kwargs_json)

    def to_mapping(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "strategy_kwargs": self.kwargs,
        }
        if self.strategy_id:
            result["strategy_id"] = self.strategy_id
        if self.strategy_path:
            result["strategy_path"] = self.strategy_path
        return result

    def to_json(self) -> str:
        return json.dumps(
            self.to_mapping(),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """Canonical order intent.  It is not permission to submit a live order."""

    market: Market
    code: str
    side: OrderSide
    offset: OrderOffset
    quantity: float
    price: float | None = None
    client_order_id: str = ""
    metadata_json: str = "{}"
    schema_version: int = DATA_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DATA_CONTRACT_SCHEMA_VERSION:
            raise DataContractError("unsupported order request schema_version")
        try:
            market = parse_market(self.market)
        except (InvalidRequestError, TypeError, ValueError) as error:
            raise DataContractError("unsupported order market") from error
        code = _text(self.code, "order code", maximum=64)
        side = parse_order_side(self.side)
        offset = parse_order_offset(self.offset)
        quantity = _finite(self.quantity, "order quantity", minimum=0.0)
        if quantity <= 0:
            raise DataContractError("order quantity must be greater than zero")
        price = None if self.price is None else _finite(self.price, "order price", minimum=0.0)
        if price == 0:
            raise DataContractError("order price must be greater than zero")
        client_order_id = _text(
            self.client_order_id,
            "client_order_id",
            maximum=128,
            allow_empty=True,
        )
        if not isinstance(self.metadata_json, str):
            raise TypeError("order metadata JSON must be a string")
        try:
            metadata = json.loads(self.metadata_json)
        except json.JSONDecodeError as error:
            raise DataContractError("order metadata JSON is invalid") from error
        metadata_json = _canonical_json_object(metadata, "order metadata", maximum_bytes=16 * 1024)
        object.__setattr__(self, "market", market)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "side", side)
        object.__setattr__(self, "offset", offset)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "client_order_id", client_order_id)
        object.__setattr__(self, "metadata_json", metadata_json)

    @classmethod
    def create(cls, *, metadata: Mapping[str, Any] | None = None, **values: Any) -> "OrderRequest":
        return cls(
            metadata_json=_canonical_json_object(
                metadata or {}, "order metadata", maximum_bytes=16 * 1024
            ),
            **values,
        )

    @property
    def metadata(self) -> dict[str, Any]:
        return json.loads(self.metadata_json)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "market": self.market.value,
            "code": self.code,
            "side": self.side.value,
            "offset": self.offset.value,
            "quantity": self.quantity,
            "price": self.price,
            "client_order_id": self.client_order_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    fill_id: str
    code: str
    side: OrderSide
    quantity: float
    price: float
    fee: float
    event_time: dt.datetime
    schema_version: int = DATA_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DATA_CONTRACT_SCHEMA_VERSION:
            raise DataContractError("unsupported fill schema_version")
        object.__setattr__(self, "order_id", _text(self.order_id, "order_id", maximum=128))
        object.__setattr__(self, "fill_id", _text(self.fill_id, "fill_id", maximum=128))
        object.__setattr__(self, "code", _text(self.code, "fill code", maximum=64))
        object.__setattr__(self, "side", parse_order_side(self.side))
        quantity = _finite(self.quantity, "fill quantity", minimum=0.0)
        if quantity <= 0:
            raise DataContractError("fill quantity must be greater than zero")
        price = _finite(self.price, "fill price", minimum=0.0)
        if price <= 0:
            raise DataContractError("fill price must be greater than zero")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "fee", _finite(self.fee, "fill fee", minimum=0.0))
        object.__setattr__(self, "event_time", _aware_datetime(self.event_time, "fill event_time"))

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "order_id": self.order_id,
            "fill_id": self.fill_id,
            "code": self.code,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": self.price,
            "fee": self.fee,
            "event_time": self.event_time.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class OrderState:
    request: OrderRequest
    order_id: str
    status: OrderStatus
    filled_quantity: float
    average_price: float | None
    updated_at: dt.datetime
    schema_version: int = DATA_CONTRACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != DATA_CONTRACT_SCHEMA_VERSION:
            raise DataContractError("unsupported order state schema_version")
        if not isinstance(self.request, OrderRequest):
            raise TypeError("order state request must be an OrderRequest")
        object.__setattr__(self, "order_id", _text(self.order_id, "order_id", maximum=128))
        object.__setattr__(self, "status", parse_order_status(self.status))
        filled = _finite(self.filled_quantity, "filled quantity", minimum=0.0)
        if filled > self.request.quantity:
            raise DataContractError("filled quantity exceeds requested quantity")
        average = (
            None
            if self.average_price is None
            else _finite(self.average_price, "average fill price", minimum=0.0)
        )
        if filled > 0 and (average is None or average <= 0):
            raise DataContractError("average price is required after a fill")
        if filled == 0 and average is not None:
            raise DataContractError("average price must be empty before the first fill")
        if self.status is OrderStatus.FILLED and filled != self.request.quantity:
            raise DataContractError("filled status requires the full requested quantity")
        object.__setattr__(self, "filled_quantity", filled)
        object.__setattr__(self, "average_price", average)
        object.__setattr__(self, "updated_at", _aware_datetime(self.updated_at, "order updated_at"))

    def apply_fill(self, fill: Fill) -> "OrderState":
        if not isinstance(fill, Fill):
            raise TypeError("fill must be a Fill")
        if fill.order_id != self.order_id or fill.code != self.request.code or fill.side is not self.request.side:
            raise DataContractError("fill does not belong to this order")
        new_quantity = self.filled_quantity + fill.quantity
        if new_quantity > self.request.quantity:
            raise DataContractError("fill exceeds the remaining order quantity")
        previous_notional = (self.average_price or 0.0) * self.filled_quantity
        average = (previous_notional + fill.price * fill.quantity) / new_quantity
        status = (
            OrderStatus.FILLED
            if new_quantity == self.request.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        return replace(
            self,
            status=status,
            filled_quantity=new_quantity,
            average_price=average,
            updated_at=fill.event_time,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request": self.request.to_payload(),
            "order_id": self.order_id,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "average_price": self.average_price,
            "updated_at": self.updated_at.isoformat(),
        }
