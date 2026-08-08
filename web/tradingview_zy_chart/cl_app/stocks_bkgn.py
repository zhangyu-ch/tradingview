"""Compatibility export for the shared stock-sector service.

The implementation belongs to the core exchange package.  Keeping this thin
module preserves the existing ``cl_app.stocks_bkgn`` import path without
copying any business logic into the web application package.
"""

from tradingview_zy.exchange.stocks_bkgn import StocksBKGN

__all__ = ["StocksBKGN"]
