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
