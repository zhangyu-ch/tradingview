# Quality gates

The `Tests` workflow exposes five stable checks that should be configured as required
checks in GitHub branch protection for the default branch. Every job uses Python 3.11,
installs the exact reviewed uv `0.10.0`, disables implicit Python downloads, and installs
with `uv sync --locked`.

- `unit-contracts` runs the complete pytest suite without ignore, deselect, keyword, or
  collection-error bypasses.
- `provider-contracts` runs the offline reliability matrix with warnings treated as errors,
  including pagination, retry, lifecycle, calendar, payload, and footprint contracts.
- `mysql-contracts` uses a real MySQL 8.0 service and verifies schema migration plus long
  strategy/chart content round trips that SQLite cannot prove.
- `browser-contracts` installs real Chromium and verifies the rendered settings DOM never
  contains a previously stored secret and keeps the replacement field empty and password-only.
- `supply-chain-contracts` proves `uv.lock` is current, verifies every local wheel against its
  SHA-256/provenance manifest, checks deterministic CycloneDX 1.6 and license evidence, and
  runs a live fail-closed OSV batch scan. Its evidence is retained as a workflow artifact.

The read-only repository-hygiene workflow runs `check_quality_gates.py`, the dependency
source contract, and the deterministic supply-chain checkers before dependency installation.
Removal or weakening of a stable job therefore fails independently. The job identifiers above
are intentionally stable; maintainers must add all five to repository branch protection after
the workflow is pushed.

Offline provider tests use protocol fakes and fault injection. They do not replace live broker,
exchange, Futu OpenD, TQ, IB, TDX, or other provider sandbox acceptance tests. Real order
execution remains disabled until the separate persisted Order/Fill and reconciliation
requirements are satisfied. Likewise, OSV coverage and package metadata do not replace vendor
security advisories, artifact signatures, or container/operating-system scanning.
