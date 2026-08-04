# Provider capability boundary

The standard `get_exchange()` path returns a `ContractedExchange` facade rather
than the legacy broad `Exchange` object. The facade checks a fine-grained
`Capability` before calling an SDK and translates SDK failures into stable,
secret-safe domain errors.

The complete market/provider/capability table is generated from the registry and
continuously checked in CI: [`provider-support-matrix.md`](provider-support-matrix.md).
That generated matrix is the support source of truth; this document explains the
contract and conservative-declaration rules.

The registry is side-effect free: reading capability metadata does not import an
SDK, open a socket or publish a cache entry. A provider is cached only after its
constructor and declared-method validation both succeed. Removed CTP and ZB
providers are rejected before registry lookup, import and cache mutation.

## Conservative declarations

No built-in provider declares `LIVE_ORDERS`. Existing live-order methods remain
fail-closed until a separate order/fill state-machine and sandbox acceptance are
complete.

The database provider exposes:

- static metadata;
- persisted K-line market data;
- derived ticks;
- a persisted-code `CATALOG` discovered from existing K-line tables;
- explicit fail-closed session status.

It does **not** provide an authoritative security master. Stored K-line tables do
not contain issuer names, listing state or corporate metadata, so DB providers
must not declare `SECURITY_MASTER`. Declaring `SECURITY_MASTER` or `PLATES` without behavior-level evidence is forbidden. `stock_owner_plate()` and `plate_stocks()`
remain unsupported, so declaring `PLATES` is also forbidden.

## Public errors

Callers may rely on stable error codes:

- `unsupported_provider`;
- `unsupported_capability`;
- `provider_unavailable` (retryable);
- `provider_response_invalid`.

Original SDK exception messages are retained only in the Python exception chain
for local debugging; they are not copied into `str(error)` or `to_dict()` and
must not be returned to clients or logs without a separate redaction boundary.
