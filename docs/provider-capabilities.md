# Provider capability boundary

The current local codebase does not yet expose a runtime `MarketRegistry` capability model. Until the separate interface/capability work is completed, callers must not infer capabilities merely because a provider implements the broad legacy `Exchange` class.

In particular, the database provider supports persisted K-line market data, derived ticks, and a **persisted-code universe** discovered from existing K-line tables. `ExchangeDB.all_stocks()` returns those distinct codes and uses each code as its display name, so search/import/selection can operate on data that is actually stored. The DB provider does **not** provide an authoritative security master: issuer names, listing state and metadata are not present. Plate/sector membership also remains unsupported:

- `ExchangeDB.all_stocks()` exposes distinct codes found in the selected market's K-line tables;
- `ExchangeDB.stock_owner_plate()` is not implemented;
- `ExchangeDB.plate_stocks()` is not implemented.

Any future registry may describe the persisted-code discovery behaviour separately. Declaring `SECURITY_MASTER` or `PLATES` remains forbidden without behaviour-level contract tests and the corresponding metadata implementation.
