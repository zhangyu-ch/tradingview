# Live trading is disabled

The repository currently provides market-data, research, monitoring, and backtesting capabilities. It does **not** expose a supported live-order execution path.

The former A-share notification trader, HK/Futu trader, Binance trader, TQ futures trader, and IB order worker were not backed by a single persisted Order/Fill state machine. Several paths treated order submission, a one-time status query, or a local position observation as if it were a final fill. That can permanently diverge the local ledger from the broker or exchange after rejection, partial fill, cancellation, disconnect, duplicate callback, or process restart.

Every `Exchange.order()` and cancellation entry now fails closed with `LiveTradingDisabledError`. Restoring live trading requires, at minimum:

- persisted `client_order_id`, broker order ID, order transitions, and individual fills;
- idempotent callback processing and cumulative filled quantity/price/fees;
- explicit submitted, accepted, partially-filled, filled, cancelled, and rejected states;
- crash-safe reconciliation on startup and after reconnect;
- no local cash, position, watchlist, or success notification update before confirmed fills;
- adapter-specific sandbox tests for rejection, delayed/partial fill, cancellation, duplicate callbacks, disconnect, and restart.

Backtesting order records remain available and are not broker orders.
