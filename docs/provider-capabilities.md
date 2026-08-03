# Provider capability boundary

The current local codebase does not yet expose a runtime `MarketRegistry` capability model. Until the separate interface/capability work is completed, callers must not infer capabilities merely because a provider implements the broad legacy `Exchange` class.

In particular, the database provider currently supports persisted K-line market data and derived ticks. It does **not** provide a security master or plate/sector membership service:

- `ExchangeDB.all_stocks()` returns no security universe;
- `ExchangeDB.stock_owner_plate()` is not implemented;
- `ExchangeDB.plate_stocks()` is not implemented.

Any future registry must therefore limit DB capabilities to market data/ticks unless behaviour-level contract tests prove those methods are implemented. Declaring `SECURITY_MASTER` or `PLATES` without those tests is forbidden.
