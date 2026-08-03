# Unsupported and removed providers

## CTP (`CR-05`)

The incomplete CTP market-data and trading adapters were removed from the runtime package.
They did not satisfy the project's `Exchange` contract, constructed invalid `Tick` payloads,
contained duplicate/overridden trading methods, and had no verified order/fill, reconnect, or
resource-release state machine.

`EXCHANGE_FUTURES = "ctp"` now fails closed before importing a provider or populating the
exchange cache. Supported built-in futures providers remain `tq`, `tdx_futures`, and `db`.

Restoring CTP is a new feature, not a configuration toggle. It requires a separately reviewed
adapter, explicit capability declaration, deterministic lifecycle, and OpenCTP simulation tests
covering authentication, subscription, order acknowledgements, partial fills, rejection,
cancellation, reconnect, reconciliation, and shutdown.

## QMT live trading (`CR-04`)

The unsafe `QMTTraderStock` live-trading adapter was removed. QMT **market data** remains a
separate provider in `exchange_qmt.py`; this removal only affects order execution.

The removed trader referenced an undefined price before sizing a buy, hard-coded a local client
path and account number, and could silently fall back from a failed real order to a simulated
"success" while still writing the shared order ledger. No built-in launcher or reconciled
order/fill state machine existed.

Restoring QMT order execution requires an explicit trader factory/capability, mandatory external
configuration, client-order idempotency, broker-confirmed fills, restart reconciliation, and QMT
sandbox tests. Real-mode failures must never be converted into simulated fills.
