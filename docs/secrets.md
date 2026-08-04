# Business secret configuration and rotation

Business credentials are never stored directly in `config.py`. Every credential field accepts
one of these references:

- `env://VARIABLE` reads an environment variable;
- `managed://namespace/version.secret` reads a versioned file under `DATA_PATH/secrets`;
- `file:///absolute/private/path` reads an operator-managed file that is not group/world readable;
- `keyring://service/account` uses the optional operating-system keyring integration.

`SECRET_ALLOW_LEGACY_PLAINTEXT` defaults to `False`. It is only a temporary migration switch for
a private, already-controlled configuration and must be returned to `False` immediately after
moving values to references. Example placeholders such as `******` are rejected even when legacy
mode is enabled.

## Classification and rotation ownership

The runtime inventory classifies every configuration credential as database, market-data,
broker-trading, messaging, or AI. Configuration references use external rotation ownership: the
operator changes the environment/file/keyring value and revokes the prior provider credential.
The Feishu Web App Secret is the managed exception: each update creates a new versioned private
file, commits only its reference, and retires the superseded local version after the database write.
`check_secret_references.py` derives its field list from this inventory so a newly added credential
cannot silently bypass classification.

## Managed files

`ManagedSecretStore` creates `DATA_PATH/secrets` and namespace directories with mode `0700`, then
writes each new version atomically with mode `0600`. The database stores only the resulting
`managed://` reference. A rotation writes the new version before updating the reference; the old
file is retired only after the database update succeeds.

The system settings page follows this process for Feishu App Secret. Existing historical
`fs_app_secret` cache rows are migrated on first read and immediately rewritten without plaintext.
Leaving the password field blank keeps the existing reference; submitting a value creates a new
version. The page never receives either the old value or the reference path.

## Deployment examples

```bash
export TRADINGVIEW_ZY_DB_PASSWORD='use-the-real-password-manager-value'
export TRADINGVIEW_ZY_BINANCE_API_KEY='...'
export TRADINGVIEW_ZY_BINANCE_SECRET='...'
```

For containers, inject environment variables from the platform secret manager. For long-lived
hosts, a root-owned `file://` reference or system keyring is preferable to shell profile text.
References are resolved only at the consumer boundary, and errors never include the reference's
resolved value.

## Rotation and logging

Changing an environment or file-backed secret requires replacing the external value and restarting
or recreating the affected provider. Managed Feishu rotation is available through the settings
page. Third-party revocation remains an operator responsibility: rotate or revoke the old key at
the provider as part of the same change window.

Resolved values are registered with the central redactor. Public errors and message delivery logs
remove exact registered values, bearer/basic authorization values, credential-bearing URL userinfo,
and common `password`/`secret`/`token`/`api_key` key-value forms. Do not log SDK request objects or
raw configuration dictionaries.
