"""Helpers for rotating sensitive Web settings without echoing secret values."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tradingview_zy.secret_store import (
    ManagedSecretStore,
    SecretError,
    reference_is_configured,
)


def _clean_public(value: object, *, limit: int = 512) -> str:
    text = str(value or "").strip()
    if "\x00" in text or len(text.encode("utf-8")) > limit:
        raise ValueError("setting value is invalid or too long")
    return text


def feishu_secret_is_configured(
    settings: Mapping[str, Any] | None,
    *,
    store: ManagedSecretStore | None = None,
) -> bool:
    """Return configured state without resolving or returning the secret."""

    if not isinstance(settings, Mapping):
        return False
    reference = str(settings.get("fs_app_secret_ref", "") or "").strip()
    if reference:
        if store is None:
            return True
        return reference_is_configured(reference, data_path=store.data_path)
    # Legacy cache rows remain visible only as a boolean until atomically migrated.
    return bool(str(settings.get("fs_app_secret", "") or "").strip())


def migrate_feishu_settings(
    existing: Mapping[str, Any] | None,
    *,
    store: ManagedSecretStore,
) -> tuple[dict[str, str], bool]:
    """Move one legacy plaintext cache row into the managed private store."""

    current = existing if isinstance(existing, Mapping) else {}
    reference = str(current.get("fs_app_secret_ref", "") or "").strip()
    changed = False
    legacy = str(current.get("fs_app_secret", "") or "").strip()
    if not reference and legacy:
        reference = store.rotate("feishu/web", legacy)
        changed = True
    sanitized = {
        "fs_app_id": _clean_public(current.get("fs_app_id", "")),
        "fs_app_secret_ref": reference,
        "fs_user_id": _clean_public(current.get("fs_user_id", "")),
    }
    if "fs_app_secret" in current:
        changed = True
    return sanitized, changed


def merge_feishu_settings(
    existing: Mapping[str, Any] | None,
    *,
    app_id: str | None,
    app_secret: str | None,
    user_id: str | None,
    store: ManagedSecretStore,
) -> tuple[dict[str, str], str | None]:
    """Return reference-only settings and the superseded managed reference.

    A blank submitted secret preserves the current reference. A non-empty value is
    written to a new private version before the caller updates the database. The old
    version is returned so the caller can retire it only after the database commit.
    """

    current, _ = migrate_feishu_settings(existing, store=store)
    old_reference = current.get("fs_app_secret_ref", "") or None
    submitted_secret = str(app_secret or "").strip()
    new_reference = old_reference or ""
    if submitted_secret:
        new_reference = store.rotate("feishu/web", submitted_secret)
    return (
        {
            "fs_app_id": _clean_public(app_id),
            "fs_app_secret_ref": new_reference,
            "fs_user_id": _clean_public(user_id),
        },
        old_reference if submitted_secret and old_reference != new_reference else None,
    )


def retire_superseded_feishu_secret(
    store: ManagedSecretStore,
    reference: str | None,
) -> None:
    if not reference:
        return
    try:
        store.retire(reference)
    except SecretError:
        # Rotation is already committed. A stale old file is safer than deleting the
        # wrong path or rolling back the new reference after the DB write succeeded.
        return
