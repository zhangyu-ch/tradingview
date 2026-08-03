"""Pure helpers for handling sensitive Web settings without echoing secrets."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def feishu_secret_is_configured(settings: Mapping[str, Any] | None) -> bool:
    """Return whether a non-empty Feishu app secret is already stored."""

    if not isinstance(settings, Mapping):
        return False
    return bool(str(settings.get("fs_app_secret", "") or "").strip())


def merge_feishu_settings(
    existing: Mapping[str, Any] | None,
    *,
    app_id: str | None,
    app_secret: str | None,
    user_id: str | None,
) -> dict[str, str]:
    """Build the persisted Feishu settings using blank-secret-means-unchanged semantics.

    The existing secret is never returned to a browser.  A caller may submit an empty
    secret while changing non-sensitive fields; in that case the stored secret is
    preserved.  A non-empty submitted secret explicitly rotates it.
    """

    current = existing if isinstance(existing, Mapping) else {}
    submitted_secret = str(app_secret or "").strip()
    if not submitted_secret:
        submitted_secret = str(current.get("fs_app_secret", "") or "")

    return {
        "fs_app_id": str(app_id or "").strip(),
        "fs_app_secret": submitted_secret,
        "fs_user_id": str(user_id or "").strip(),
    }
