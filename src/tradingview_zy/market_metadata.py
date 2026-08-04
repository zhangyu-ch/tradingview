"""Side-effect-free Web metadata for configured market families."""

from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import Mapping

from tradingview_zy.trading_calendar import market_calendar_metadata

# This metadata intentionally contains no SDK imports and performs no network I/O.
# Provider-specific capabilities are checked when the corresponding request is made.
_MARKET_WEB_METADATA = {
    "a": {
        "default_code": "SH.000001",
        "frequencies": ["y", "m", "w", "d", "120m", "60m", "30m", "15m", "10m", "5m"],
    },
    "hk": {
        "default_code": "HK.00700",
        "frequencies": ["y", "q", "m", "w", "d", "60m", "30m", "15m", "5m"],
    },
    "fx": {
        "default_code": "USDCNH",
        "frequencies": ["w", "d", "60m", "30m", "15m", "5m", "1m"],
    },
    "us": {
        "default_code": "AAPL",
        "frequencies": ["m", "w", "d", "60m", "30m", "15m", "10m", "5m", "2m", "1m"],
    },
    "futures": {
        "default_code": "KQ.m@SHFE.rb",
        "frequencies": ["w", "d", "120m", "60m", "30m", "15m", "10m", "5m", "1m"],
    },
    "ny_futures": {
        "default_code": "CO.GC00W",
        "frequencies": ["w", "d", "120m", "60m", "30m", "15m", "10m", "5m", "1m"],
    },
    "currency": {
        "default_code": "BTC/USDT",
        "frequencies": ["w", "d", "4h", "60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"],
    },
    "currency_spot": {
        "default_code": "BTC/USDT",
        "frequencies": ["w", "d", "4h", "60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"],
    },
}

_TRADINGVIEW_STATIC_METADATA: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {
        "a": MappingProxyType(
            {
                "type": "stock",
                "session": "0930-1130,1300-1500:23456",
                "timezone": "Asia/Shanghai",
            }
        ),
        "hk": MappingProxyType(
            {
                "type": "stock",
                "session": "0930-1200,1300-1600:23456",
                "timezone": "Asia/Hong_Kong",
            }
        ),
        "us": MappingProxyType(
            {
                "type": "stock",
                "session": "0930-1600:23456",
                "timezone": "America/New_York",
            }
        ),
        "fx": MappingProxyType(
            {
                "type": "forex",
                "session": "24x5",
                "timezone": "America/New_York",
            }
        ),
        "currency": MappingProxyType(
            {"type": "crypto", "session": "24x7", "timezone": "Etc/UTC"}
        ),
        "currency_spot": MappingProxyType(
            {"type": "crypto", "session": "24x7", "timezone": "Etc/UTC"}
        ),
        "ny_futures": MappingProxyType(
            {
                "type": "futures",
                "session": "1800-1700:23456",
                "timezone": "America/New_York",
            }
        ),
    }
)

_CN_FUTURES_SESSIONS: Mapping[str, str] = MappingProxyType(
    {
        "commodity_day": "0900-1015,1030-1130,1330-1500:23456",
        "night_2300": "2100-2300,0900-1015,1030-1130,1330-1500:23456",
        "night_0100": "2100-0100,0900-1015,1030-1130,1330-1500:23456",
        "night_0230": "2100-0230,0900-1015,1030-1130,1330-1500:23456",
        "cffex_index": "0930-1130,1300-1500:23456",
        "cffex_treasury": "0930-1130,1300-1515:23456",
    }
)


def market_web_metadata() -> dict[str, dict[str, object]]:
    return deepcopy(_MARKET_WEB_METADATA)


def market_default_codes() -> dict[str, str]:
    return {
        market: str(metadata["default_code"])
        for market, metadata in _MARKET_WEB_METADATA.items()
    }


def market_frequencies() -> dict[str, list[str]]:
    return {
        market: list(metadata["frequencies"])
        for market, metadata in _MARKET_WEB_METADATA.items()
    }


def all_market_frequencies(
    markets: dict[str, list[str]] | None = None,
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
    market: str, code: str | None = None
) -> dict[str, str]:
    """Return the authoritative TradingView type/session/timezone descriptor.

    The descriptor represents regular sessions. Holiday and temporary-close
    decisions remain the responsibility of :mod:`trading_calendar` at request
    time. Unknown Chinese futures products are advertised conservatively as
    day-session only rather than as continuous or 24x7 markets.
    """

    market_key = str(market).strip().lower()
    if market_key == "futures":
        profile = "commodity_day"
        if code:
            try:
                profile = str(
                    market_calendar_metadata("futures", code).get(
                        "profile", "commodity_day"
                    )
                )
            except ValueError:
                # Unknown products must never inherit a guessed night session.
                profile = "commodity_day"
        session = _CN_FUTURES_SESSIONS.get(
            profile, _CN_FUTURES_SESSIONS["commodity_day"]
        )
        return {
            "type": "futures",
            "session": session,
            "timezone": "Asia/Shanghai",
        }

    descriptor = _TRADINGVIEW_STATIC_METADATA.get(market_key)
    if descriptor is None:
        raise ValueError(f"unsupported TradingView market metadata: {market!r}")
    return dict(descriptor)
