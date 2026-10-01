# Quality gates

The `Tests` workflow exposes six stable checks that should be configured as required
checks in GitHub branch protection for the default branch. Every job uses Python 3.11,
installs the exact reviewed uv `0.10.0`, disables implicit Python downloads, and installs
with `uv sync --locked`.

- `unit-contracts` installs Node.js for the bundled PineJS/JavaScript contracts and runs the
  complete pytest suite without ignore, deselect, keyword, or collection-error bypasses.
- `provider-contracts` runs the offline reliability matrix with warnings treated as errors,
  including pagination, retry, lifecycle, calendar, payload, and footprint contracts.
- `mysql-contracts` uses a real MySQL 8.0 service and verifies the current schema and long
  strategy/chart content round trips that SQLite cannot prove. Historical migration and
  failure atomicity are covered separately by the isolated SQLite migration contracts.
- `browser-contracts` installs real Chromium and runs the isolated real application with
  temporary SQLite data. It verifies CSRF transports, chart iframe storage, opt-in table
  styles, and settings save/reload without leaking legacy secrets into the DOM or console.
- `windows-contracts` verifies the locked environment, generated test configuration, local
  file references, scheduler ownership, supply-chain evidence, and native launcher failure,
  pause and non-interactive exit behavior on Windows.
- `supply-chain-contracts` proves `uv.lock` is current, verifies every local wheel against its
  SHA-256/provenance manifest, checks deterministic CycloneDX 1.6 and license evidence, and
  runs a live fail-closed OSV batch scan. Its evidence is retained as a workflow artifact.

The read-only repository-hygiene workflow runs `check_quality_gates.py`, the readability and
repository-hygiene contracts, the dependency source contract, deterministic supply-chain checks,
`generate_provider_support_matrix.py --check`, and both Secret reference/exposure checks before
dependency installation. The generated provider matrix must exactly match `MarketRegistry`, so
code capability changes cannot leave README/support documentation stale.
Removal or weakening of a stable job therefore fails independently. The job identifiers above
are intentionally stable; maintainers must add all six to repository branch protection after
the workflow is pushed.

Offline provider tests use protocol fakes and fault injection. They do not replace live broker,
exchange, Futu OpenD, TQ, IB, TDX, or other provider sandbox acceptance tests. Real order
execution remains disabled until the separate persisted Order/Fill and reconciliation
requirements are satisfied. Likewise, OSV coverage and package metadata do not replace vendor
security advisories, artifact signatures, or container/operating-system scanning.
