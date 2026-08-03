#!/usr/bin/env python3
"""Static guard against returning or logging persisted Web setting secrets."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def validate(app_source: str, template_source: str) -> list[str]:
    errors: list[str] = []

    value_patterns = [
        r'value\s*=\s*["\']\s*\{\{\s*fs_app_secret',
        r'value\s*=\s*["\'][^"\']*fs_app_secret',
    ]
    if any(re.search(pattern, template_source, re.IGNORECASE) for pattern in value_patterns):
        errors.append("setting template embeds the persisted Feishu secret in an input value")

    secret_input = re.search(
        r"<input\b(?=[^>]*\bname=[\"']fs_app_secret[\"'])[^>]*>",
        template_source,
        re.IGNORECASE | re.DOTALL,
    )
    if not secret_input:
        errors.append("setting template has no fs_app_secret input")
    else:
        tag = secret_input.group(0)
        if not re.search(r"\btype=[\"']password[\"']", tag, re.IGNORECASE):
            errors.append("fs_app_secret input must use type=password")
        if not re.search(r"\bvalue=[\"']\s*[\"']", tag, re.IGNORECASE):
            errors.append("fs_app_secret input must always render with an empty value")

    if re.search(r"console\.(?:log|debug|info|warn)\s*\([^)]*data\.field", template_source):
        errors.append("setting form fields are written to the browser console")

    try:
        get_start = app_source.index("def setting():")
        save_start = app_source.index('@app.route("/setting/save"', get_start)
        get_block = app_source[get_start:save_start]
    except ValueError:
        errors.append("cannot locate setting GET/save route boundary")
    else:
        if re.search(r'["\']fs_app_secret["\']\s*:', get_block):
            errors.append("setting GET route returns fs_app_secret")
        if "fs_app_secret_configured" not in get_block:
            errors.append("setting GET route must expose only configured/not-configured state")
        if '"Cache-Control": "no-store"' not in get_block:
            errors.append("setting GET response must be non-cacheable")

    return errors


def validate_root(root: Path) -> list[str]:
    app = root / "web/tradingview_zy_chart/cl_app/__init__.py"
    template = root / "web/tradingview_zy_chart/cl_app/templates/setting.html"
    return validate(
        app.read_text(encoding="utf-8"),
        template.read_text(encoding="utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_root(args.root.resolve())
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("secret exposure guard OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
