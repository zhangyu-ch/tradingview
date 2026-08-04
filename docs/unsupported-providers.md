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

## All live order execution (`CR-03`)

All remaining live order and cancellation entry points now fail closed. See
[`live-trading-disabled.md`](live-trading-disabled.md) for the required Order/Fill state
machine, idempotency, reconciliation, and sandbox acceptance criteria. Market-data and
backtesting capabilities remain available.

## ZB cryptocurrency provider (`MX-02`)

The orphaned `ExchangeZB` adapter was removed from the runtime package. The configuration
template previously listed `zb` as supported even though the standard exchange factory never
registered it, so a documented configuration could not start. The legacy adapter also disabled
TLS certificate verification, which made directly importing it unsafe.

`EXCHANGE_CURRENCY = "zb"` now fails closed before any provider import or exchange-cache
mutation. Supported built-in cryptocurrency-futures providers are `binance` and `db`. Restoring
ZB requires a newly reviewed adapter with verified TLS, an explicit registry entry, provider
contract tests, and maintained upstream API compatibility.

### CTP front-address restoration contract (`NX-01`)

Any future CTP implementation must treat market-data and trade front addresses as
validated configuration, not as an attribute-presence fallback. Each endpoint must be
a non-empty `tcp://host:port` value before an OpenCTP SDK object is constructed. An
empty string must either be rejected with a configuration error or resolved through one
single, documented default; code must not silently continue because the configuration
attribute happens to exist.

Endpoint parsing must reject missing schemes, credentials, paths, queries, fragments,
invalid ports, and control characters. Health output may identify the environment and
whether an endpoint is configured, but logs, exceptions, and diagnostics must not expose
credentials or other secrets. Restoring these settings is permitted only together with
the full CR-05 provider review and simulation acceptance tests described above.
