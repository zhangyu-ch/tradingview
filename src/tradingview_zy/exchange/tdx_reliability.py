from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeVar


T = TypeVar("T")


class ProviderUnavailableError(RuntimeError):
    """A market-data provider could not become ready within its deadline."""


class TdxMarketMapError(RuntimeError):
    """The ExHq service returned an unusable market-map payload."""


def call_with_bounded_retry(
    operation: Callable[[float], T],
    *,
    recover: Callable[[], object] | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    deadline_seconds: float = 12.0,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
    description: str = "TDX provider initialization",
) -> T:
    """Run a retryable TDX operation with attempt and wall-clock bounds.

    ``operation`` receives the remaining deadline so the SDK connection timeout
    can never exceed the overall budget. Recovery (for example selecting a new
    node) is also inside the same budget.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if deadline_seconds <= 0:
        raise ValueError("deadline_seconds must be positive")

    started = clock()
    deadline = started + deadline_seconds
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        try:
            result = operation(remaining)
            if clock() > deadline:
                last_error = TimeoutError("operation completed after its deadline")
                break
            return result
        except retry_on as exc:
            last_error = exc
            if attempt >= max_attempts:
                break

            if recover is not None:
                remaining = deadline - clock()
                if remaining <= 0:
                    break
                try:
                    recover()
                except retry_on as recover_exc:
                    last_error = recover_exc

            remaining = deadline - clock()
            if remaining <= 0:
                break
            delay = min(
                base_delay_seconds * (2 ** (attempt - 1)),
                max_delay_seconds,
                remaining,
            )
            if delay > 0:
                sleeper(delay)

    elapsed = max(0.0, clock() - started)
    message = (
        f"{description} unavailable after {max_attempts} attempts "
        f"within {deadline_seconds:.2f}s (elapsed {elapsed:.2f}s)"
    )
    raise ProviderUnavailableError(message) from last_error


class TdxExHqLifecycleMixin:
    """Shared, dependency-injected lifecycle for TDX ExHq adapters.

    The mixin intentionally imports neither the database singleton nor pytdx.
    Adapters inject the cache backend, node selector and SDK client factory so
    the lifecycle can be fault-injected without opening sockets or importing
    optional provider packages.
    """

    _tdx_cache_key = "tdxex_connect_ip"

    def _initialize_tdx_exhq(
        self,
        *,
        cache_backend: Any,
        selector: Any,
        client_factory: Callable[..., Any],
        connection_errors: tuple[type[BaseException], ...],
        description: str,
        market_category: int | None = None,
        market_ids: Iterable[int] | None = None,
        load_markets: bool = True,
        client_kwargs: Mapping[str, Any] | None = None,
        retry_options: Mapping[str, Any] | None = None,
    ) -> None:
        if not connection_errors or not all(
            isinstance(error, type) and issubclass(error, BaseException)
            for error in connection_errors
        ):
            raise ValueError("connection_errors must contain exception classes")
        if not callable(client_factory):
            raise TypeError("client_factory must be callable")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("description must be a non-empty string")

        self._tdx_cache_backend = cache_backend
        self._tdx_selector = selector
        self._tdx_client_factory = client_factory
        self._tdx_connection_errors = tuple(connection_errors)
        self._tdx_description = description.strip()
        self._tdx_client_kwargs = {
            **dict(client_kwargs or {}),
            "raise_exception": True,
            "auto_retry": True,
        }
        self._tdx_retry_options = dict(retry_options or {})
        self._tdx_market_category = market_category
        self._tdx_market_ids = (
            frozenset(int(value) for value in market_ids)
            if market_ids is not None
            else None
        )

        try:
            cached = cache_backend.cache_get(self._tdx_cache_key)
            try:
                self.connect_info = self._normalize_connect_info(cached)
            except (TypeError, ValueError):
                self.connect_info = self.reset_tdx_ip()

            self.market_maps = self._load_tdx_markets() if load_markets else {}
        except ProviderUnavailableError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError(
                f"{self._tdx_description} initialization failed"
            ) from exc

    @staticmethod
    def _normalize_connect_info(value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError("TDX node must be an object")
        ip = value.get("ip")
        if not isinstance(ip, str) or not ip.strip():
            raise ValueError("TDX node IP/host is empty")
        if any(ord(character) < 32 for character in ip):
            raise ValueError("TDX node IP/host contains control characters")
        port_value = value.get("port")
        if isinstance(port_value, bool):
            raise ValueError("TDX node port is invalid")
        try:
            port = int(port_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("TDX node port is invalid") from exc
        if not 1 <= port <= 65535:
            raise ValueError("TDX node port is outside 1..65535")
        return {"ip": ip.strip(), "port": port}

    def reset_tdx_ip(self) -> dict[str, Any]:
        """Select, validate and cache one ExHq node with a finite TTL."""
        selected = self._tdx_selector.select_best_ip("future")
        connect_info = self._normalize_connect_info(selected)
        expiry = int(self._tdx_selector.cache_expiry_epoch())
        if expiry <= 0:
            raise ValueError("TDX node cache expiry must be positive")
        self._tdx_cache_backend.cache_set(
            self._tdx_cache_key,
            connect_info,
            expire=expiry,
        )
        self.connect_info = connect_info
        return connect_info

    def _new_tdx_client(self) -> Any:
        """Create a fresh SDK client with the adapter's canonical options."""
        return self._tdx_client_factory(**dict(self._tdx_client_kwargs))

    def _load_tdx_markets(self) -> dict[str, dict[str, Any]]:
        """Load and canonicalize the ExHq market map within one total budget."""

        def operation(remaining_seconds: float) -> Any:
            client = self._new_tdx_client()
            with client.connect(
                self.connect_info["ip"],
                self.connect_info["port"],
                time_out=max(0.1, min(float(remaining_seconds), 4.0)),
            ):
                markets = client.get_markets()
            if markets is None:
                raise TdxMarketMapError("TDX market map is missing")
            return markets

        retry_options = {
            "max_attempts": 3,
            "deadline_seconds": 12.0,
            "base_delay_seconds": 0.25,
            "max_delay_seconds": 1.0,
            **dict(self._tdx_retry_options),
        }
        retry_options["description"] = (
            f"{self._tdx_description} market-map initialization"
        )
        raw_markets = call_with_bounded_retry(
            operation,
            recover=self.reset_tdx_ip,
            retry_on=self._tdx_connection_errors + (TdxMarketMapError,),
            **retry_options,
        )

        if not isinstance(raw_markets, Iterable) or isinstance(
            raw_markets, (str, bytes, Mapping)
        ):
            raise ProviderUnavailableError(
                f"{self._tdx_description} returned an invalid market map"
            )

        result: dict[str, dict[str, Any]] = {}
        for raw_market in raw_markets:
            if not isinstance(raw_market, Mapping):
                raise ProviderUnavailableError(
                    f"{self._tdx_description} returned a malformed market entry"
                )
            try:
                category = int(raw_market["category"])
                market_id = int(raw_market["market"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderUnavailableError(
                    f"{self._tdx_description} returned a malformed market entry"
                ) from exc
            if self._tdx_market_category is not None and category != int(
                self._tdx_market_category
            ):
                continue
            if (
                self._tdx_market_ids is not None
                and market_id not in self._tdx_market_ids
            ):
                continue

            short_name = raw_market.get("short_name")
            name = raw_market.get("name")
            if not isinstance(short_name, str) or not short_name.strip():
                raise ProviderUnavailableError(
                    f"{self._tdx_description} returned an empty market short name"
                )
            if short_name in result:
                raise ProviderUnavailableError(
                    f"{self._tdx_description} returned duplicate market {short_name!r}"
                )
            result[short_name] = {
                "market": market_id,
                "category": category,
                "name": str(name or ""),
            }

        if not result:
            raise ProviderUnavailableError(
                f"{self._tdx_description} returned no supported markets"
            )
        return result
