"""Capability-bound facade and response validation for legacy providers."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Callable, TypeVar

import pandas as pd

from tradingview_zy.base import Market
from tradingview_zy.exchange.exchange import Exchange, LiveTradingDisabledError
from tradingview_zy.domain import (
    CAPABILITY_METHODS,
    Capability,
    ExchangeError,
    ProviderResponseError,
    ProviderUnavailableError,
    UnsupportedCapabilityError,
)
from tradingview_zy.market_registry import ProviderSpec

T = TypeVar("T")


def _looks_unavailable(error: BaseException) -> bool:
    name = type(error).__name__.lower()
    return isinstance(error, (TimeoutError, ConnectionError, OSError)) or any(
        token in name for token in ("timeout", "connection", "unavailable", "network")
    )


class ContractedExchange:
    """Wrap a broad legacy Exchange object with explicit capabilities."""

    def __init__(
        self,
        market: Market,
        provider_name: str,
        provider: Any,
        spec: ProviderSpec,
    ) -> None:
        self.market = market
        self.provider_name = provider_name
        self.raw_provider = provider
        self.capabilities = spec.capabilities
        self._validate_declared_methods()

    def _validate_declared_methods(self) -> None:
        missing: list[str] = []
        for capability in self.capabilities:
            for method in CAPABILITY_METHODS[capability]:
                implementation = getattr(type(self.raw_provider), method, None)
                inherited_stub = implementation is getattr(Exchange, method, None)
                if not callable(getattr(self.raw_provider, method, None)) or inherited_stub:
                    missing.append(f"{capability.value}:{method}")
        if missing:
            raise ProviderResponseError(
                "数据源实现与能力声明不一致", provider=self.provider_name
            )

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def require(self, capability: Capability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedCapabilityError(
                f"{self.market.value}/{self.provider_name} 不支持能力 {capability.value}",
                provider=self.provider_name,
            )

    def _call(self, capability: Capability, method: str, *args: Any, **kwargs: Any) -> Any:
        self.require(capability)
        try:
            return getattr(self.raw_provider, method)(*args, **kwargs)
        except ExchangeError:
            raise
        except Exception as error:
            if _looks_unavailable(error):
                raise ProviderUnavailableError(provider=self.provider_name) from error
            raise ProviderResponseError(provider=self.provider_name) from error

    def default_code(self) -> str:
        value = self._call(Capability.METADATA, "default_code")
        if not isinstance(value, str) or not value.strip():
            raise ProviderResponseError("默认代码响应无效", provider=self.provider_name)
        return value

    def support_frequencys(self) -> dict[str, str]:
        value = self._call(Capability.METADATA, "support_frequencys")
        if not isinstance(value, Mapping) or not value:
            raise ProviderResponseError("周期元数据响应无效", provider=self.provider_name)
        result = dict(value)
        if not all(isinstance(k, str) and k and isinstance(v, str) and v for k, v in result.items()):
            raise ProviderResponseError("周期元数据响应无效", provider=self.provider_name)
        return result

    def klines(self, code: str, frequency: str, start_date=None, end_date=None, args=None):
        value = self._call(
            Capability.MARKET_DATA,
            "klines",
            code,
            frequency,
            start_date=start_date,
            end_date=end_date,
            args=args,
        )
        if value is None:
            return None
        if not isinstance(value, pd.DataFrame):
            raise ProviderResponseError("K 线响应类型无效", provider=self.provider_name)
        required = {"date", "open", "high", "low", "close", "volume"}
        if not value.empty and not required.issubset(value.columns):
            raise ProviderResponseError("K 线响应缺少必需字段", provider=self.provider_name)
        return value

    def ticks(self, codes: list[str]):
        value = self._call(Capability.TICKS, "ticks", codes)
        if not isinstance(value, Mapping):
            raise ProviderResponseError("Tick 响应类型无效", provider=self.provider_name)
        return dict(value)

    def all_stocks(self):
        value = self._call(Capability.CATALOG, "all_stocks")
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ProviderResponseError("证券目录响应类型无效", provider=self.provider_name)
        result = list(value)
        for item in result:
            if not isinstance(item, Mapping):
                raise ProviderResponseError("证券目录响应无效", provider=self.provider_name)
            code = item.get("code")
            name = item.get("name")
            if not isinstance(code, str) or not code or not isinstance(name, str):
                raise ProviderResponseError("证券目录响应无效", provider=self.provider_name)
        return result

    def stock_info(self, code: str):
        value = self._call(Capability.CATALOG, "stock_info", code)
        if value is not None and not isinstance(value, Mapping):
            raise ProviderResponseError("证券信息响应无效", provider=self.provider_name)
        return value

    def now_trading(self, code: str | None = None, at=None) -> bool:
        value = self._call(Capability.SESSION_STATUS, "now_trading", code=code, at=at)
        if type(value) is not bool:
            raise ProviderResponseError("交易状态必须是布尔值", provider=self.provider_name)
        return value

    def stock_owner_plate(self, code: str):
        value = self._call(Capability.PLATES, "stock_owner_plate", code)
        if not isinstance(value, Mapping):
            raise ProviderResponseError("板块响应无效", provider=self.provider_name)
        return value

    def plate_stocks(self, code: str):
        value = self._call(Capability.PLATES, "plate_stocks", code)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ProviderResponseError("板块成分响应无效", provider=self.provider_name)
        return list(value)

    def balance(self):
        return self._call(Capability.ACCOUNT_BALANCE, "balance")

    def positions(self, code: str = ""):
        return self._call(Capability.POSITIONS, "positions", code)

    def _raise_live_trading_disabled(self, action: str = "order") -> None:
        raise LiveTradingDisabledError(
            f"live trading is disabled: ContractedExchange.{action}; "
            "a persisted Order/Fill state machine and broker reconciliation are required"
        )

    def order(self, code: str, o_type: str, amount: float, args=None):
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not math.isfinite(float(amount)):
            raise ProviderResponseError("订单数量无效", provider=self.provider_name)
        return self._raise_live_trading_disabled("order")

    def close(self) -> None:
        close = getattr(self.raw_provider, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                return

    def __getattr__(self, name: str) -> Any:
        # Migration compatibility for helper methods outside the broad Exchange ABC.
        return getattr(self.raw_provider, name)
