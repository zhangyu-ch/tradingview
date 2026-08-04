"""Side-effect-free Web and UDF views derived from the market registry."""
from __future__ import annotations

from typing import Any, Mapping

from tradingview_zy.market_registry import (
    MARKET_REGISTRY,
    MarketSpec,
    market_spec,
    market_value,
)
from tradingview_zy.trading_calendar import market_calendar_metadata


def _specs(registry: Mapping[Any, MarketSpec]) -> tuple[MarketSpec, ...]:
    return tuple(registry.values())


def market_web_metadata(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> dict[str, dict[str, object]]:
    return {
        market_value(spec.market): {
            "default_code": spec.default_code,
            "frequencies": list(spec.frequencies),
        }
        for spec in _specs(registry)
    }


def market_default_codes(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> dict[str, str]:
    return {
        market_value(spec.market): spec.default_code
        for spec in _specs(registry)
    }


def market_frequencies(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> dict[str, list[str]]:
    return {
        market_value(spec.market): list(spec.frequencies)
        for spec in _specs(registry)
    }


def market_ui_options(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> list[dict[str, str]]:
    return [
        {"value": market_value(spec.market), "label": spec.ui_label}
        for spec in _specs(registry)
    ]


def market_catalog(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> list[dict[str, object]]:
    """Return the full UI/UDF market catalogue from the registry order."""

    return [
        {
            "value": market_value(spec.market),
            "label": spec.ui_label,
            "name": spec.tradingview_name,
            "desc": spec.description,
            "default_code": spec.default_code,
            "has_seconds": bool(spec.has_seconds),
            "search_name": bool(spec.search_by_name),
            "plate_panel": bool(spec.plate_panel),
            "is_default": bool(spec.is_default),
        }
        for spec in _specs(registry)
    ]


def default_market_value(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> str:
    defaults = [
        market_value(spec.market) for spec in _specs(registry) if spec.is_default
    ]
    if len(defaults) != 1:
        raise ValueError(
            f"market registry must declare exactly one default market: {defaults}"
        )
    return defaults[0]


def market_ui_metadata(
    market: str,
    *,
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> dict[str, bool]:
    spec = market_spec(market, registry=registry)
    return {
        "has_seconds": bool(spec.has_seconds),
        "search_name": bool(spec.search_by_name),
        "plate_panel": bool(spec.plate_panel),
    }


def market_exchange_descriptors(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> list[dict[str, str]]:
    return [
        {
            "value": market_value(spec.market),
            "name": spec.tradingview_name,
            "desc": spec.description,
        }
        for spec in _specs(registry)
    ]


def market_chart_defaults(
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
    *,
    default_market: str | None = None,
    default_interval: str = "1D",
) -> dict[str, str]:
    specs = _specs(registry)
    if not specs:
        raise ValueError("market registry must not be empty")
    default_market = default_market or default_market_value(registry)
    available = {market_value(spec.market) for spec in specs}
    if default_market not in available:
        raise ValueError(f"default market is not registered: {default_market!r}")
    result = {
        "theme": "Light",
        "market": default_market,
        "chart_layout_type": "single",
    }
    for spec in specs:
        key = market_value(spec.market)
        result[f"{key}_interval_1"] = default_interval
        result[f"{key}_interval_2"] = default_interval
        result[f"{key}_code"] = spec.default_code
    return result


def all_market_frequencies(
    markets: Mapping[str, list[str]] | None = None,
) -> list[str]:
    """Return the stable union of every registered Web market frequency."""

    source = market_frequencies() if markets is None else markets
    result: list[str] = []
    seen: set[str] = set()
    for frequencies in source.values():
        for frequency in frequencies:
            if frequency in seen:
                continue
            seen.add(frequency)
            result.append(frequency)
    return result


def tradingview_symbol_metadata(
    market: str,
    code: str | None = None,
    *,
    registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY,
) -> dict[str, str]:
    """Return type/session/timezone from one market descriptor.

    A descriptor may opt into the versioned calendar profile resolver. Unknown
    instrument profiles fail closed to that descriptor's conservative default.
    """

    try:
        spec = market_spec(market, registry=registry)
    except Exception as error:
        raise ValueError(f"unsupported TradingView market metadata: {market!r}") from error

    profile = spec.default_session_profile
    if spec.session_profile_from_calendar and code:
        try:
            profile = str(
                market_calendar_metadata(market_value(spec.market), code).get(
                    "profile", spec.default_session_profile
                )
            )
        except ValueError:
            profile = spec.default_session_profile
    session = spec.tradingview_sessions.get(
        profile,
        spec.tradingview_sessions[spec.default_session_profile],
    )
    return {
        "type": spec.tradingview_type,
        "session": session,
        "timezone": spec.tradingview_timezone,
    }


def market_has_seconds(
    market: str, *, registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY
) -> bool:
    return market_ui_metadata(market, registry=registry)["has_seconds"]


def market_searches_by_name(
    market: str, *, registry: Mapping[Any, MarketSpec] = MARKET_REGISTRY
) -> bool:
    return market_ui_metadata(market, registry=registry)["search_name"]
