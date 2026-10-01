from __future__ import annotations

import math
from typing import Any


def calculate_change_rate(last: Any, previous_close: Any) -> float | None:
    """Return the percentage change using the previous close as denominator.

    A missing, non-finite or non-positive price is not a valid zero-percent move.
    Returning ``None`` preserves that distinction through the API and UI instead
    of silently presenting unavailable market data as an unchanged quote.
    """
    try:
        last_value = float(last)
        previous_value = float(previous_close)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(last_value) or not math.isfinite(previous_value):
        return None
    if last_value <= 0 or previous_value <= 0:
        return None
    return round((last_value - previous_value) / previous_value * 100.0, 2)


def fetch_exhq_ticks(client, connect_info, to_tdx_code, codes):
    """Fetch ExHq quotes in request order using one connection.

    Code conversion remains provider-specific. Missing markets/empty quotes are
    skipped; conversion and SDK errors propagate after closing the connection.
    """
    from tradingview_zy.exchange.exchange import Tick

    ticks = {}
    with client.connect(connect_info["ip"], connect_info["port"]):
        for code in codes:
            market, tdx_code = to_tdx_code(code)
            if market is None:
                continue
            quotes = client.get_instrument_quote(market, tdx_code)
            if len(quotes) > 0:
                quote = quotes[0]
                ticks[code] = Tick(
                    code=code,
                    last=quote["price"],
                    buy1=quote["bid1"],
                    sell1=quote["ask1"],
                    low=quote["low"],
                    high=quote["high"],
                    volume=quote["zongliang"],
                    open=quote["open"],
                    rate=calculate_change_rate(quote["price"], quote["pre_close"]),
                )
    return ticks
