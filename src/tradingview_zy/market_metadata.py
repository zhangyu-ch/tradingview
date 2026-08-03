"""Side-effect-free Web metadata for configured market families."""

from __future__ import annotations

from copy import deepcopy

# This metadata intentionally contains no SDK imports and performs no network I/O.
# Provider-specific capabilities are checked when the corresponding request is made.
_MARKET_WEB_METADATA = {
    "a": {"default_code": "SH.000001", "frequencies": ["y", "m", "w", "d", "120m", "60m", "30m", "15m", "10m", "5m"]},
    "hk": {"default_code": "HK.00700", "frequencies": ["y", "q", "m", "w", "d", "60m", "30m", "15m", "5m"]},
    "fx": {"default_code": "USDCNH", "frequencies": ["w", "d", "60m", "30m", "15m", "5m", "1m"]},
    "us": {"default_code": "AAPL", "frequencies": ["m", "w", "d", "60m", "30m", "15m", "10m", "5m", "2m", "1m"]},
    "futures": {"default_code": "KQ.m@SHFE.rb", "frequencies": ["w", "d", "120m", "60m", "30m", "15m", "10m", "5m", "1m"]},
    "ny_futures": {"default_code": "CO.GC00W", "frequencies": ["w", "d", "120m", "60m", "30m", "15m", "10m", "5m", "1m"]},
    "currency": {"default_code": "BTC/USDT", "frequencies": ["w", "d", "4h", "60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"]},
    "currency_spot": {"default_code": "BTC/USDT", "frequencies": ["w", "d", "4h", "60m", "30m", "15m", "10m", "5m", "3m", "2m", "1m"]},
}


def market_web_metadata() -> dict[str, dict[str, object]]:
    return deepcopy(_MARKET_WEB_METADATA)


def market_default_codes() -> dict[str, str]:
    return {market: str(metadata["default_code"]) for market, metadata in _MARKET_WEB_METADATA.items()}


def market_frequencies() -> dict[str, list[str]]:
    return {market: list(metadata["frequencies"]) for market, metadata in _MARKET_WEB_METADATA.items()}
