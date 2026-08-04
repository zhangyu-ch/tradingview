# Quality gates

The `Tests` workflow exposes four stable checks that should be configured as required
checks in GitHub branch protection for the default branch:

- `unit-contracts` installs Python 3.11 from `uv.lock` and runs the complete pytest suite
  without ignore, deselect, or collection-error bypasses.
- `provider-contracts` runs the offline reliability matrix with warnings treated as errors,
  including pagination, retry, lifecycle, calendar, payload, and footprint contracts.
- `mysql-contracts` uses a real MySQL 8.0 service and verifies schema migration plus long
  strategy/chart content round trips that SQLite cannot prove.
- `browser-contracts` installs real Chromium and verifies the rendered settings DOM never
  contains a previously stored secret and keeps the replacement field empty and password-only.

The read-only repository-hygiene workflow runs `check_quality_gates.py` before dependency
installation so removal or weakening of these jobs is itself rejected. The job identifiers
above are intentionally stable; maintainers must add them to repository branch protection
after the workflow is pushed.

Offline provider tests use protocol fakes and fault injection. They do not replace live
broker, exchange, Futu OpenD, TQ, IB, TDX, or other provider sandbox acceptance tests.
Real order execution remains disabled until the separate persisted Order/Fill and
reconciliation requirements are satisfied.
