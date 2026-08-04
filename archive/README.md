# Historical archives

Files under `archive/` are retained only as migration or research evidence. They are not
imported, packaged, tested as supported runtime modules, or included in the provider capability
matrix.

- `chanlun-runtime-source.zip` preserves the removed Chanlun calculation runtime.
- `docs/` preserves historical Chanlun documentation.
- `joinquant-legacy.zip` preserves the former top-level JoinQuant notebooks and helper module.
  That code imports the proprietary `jqdata` environment and the removed `cl` package; it is
  intentionally unavailable from the active project root.

Restoring archived code requires a new issue, an explicit supported capability, dependency and
license review, and executable tests. Copying an archive back into the runtime tree is not a
supported installation path.
