#!/usr/bin/env python3
"""Reject plaintext business credentials and direct config-secret consumers."""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingview_zy.secret_store import CONFIG_SECRET_POLICIES  # noqa: E402

SENSITIVE_ATTRIBUTES = tuple(CONFIG_SECRET_POLICIES)
REFERENCE_PREFIXES = ("env://", "managed://", "file://", "keyring://")


def _literal_assignments(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                result[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
    return result


def _valid_reference(value: object) -> bool:
    return isinstance(value, str) and (not value or value.startswith(REFERENCE_PREFIXES))


def validate(root: Path) -> list[str]:
    root = root.resolve()
    config_path = root / "src/tradingview_zy/config.py.demo"
    errors: list[str] = []
    try:
        assignments = _literal_assignments(config_path)
    except (OSError, SyntaxError) as error:
        return [f"cannot parse config.py.demo: {error}"]

    if assignments.get("SECRET_ALLOW_LEGACY_PLAINTEXT") is not False:
        errors.append("SECRET_ALLOW_LEGACY_PLAINTEXT must default to False")
    for name in SENSITIVE_ATTRIBUTES:
        if name not in assignments:
            errors.append(f"config template is missing {name}")
        elif not _valid_reference(assignments[name]):
            errors.append(f"{name} must be blank or use an approved secret reference")

    feishu = assignments.get("FEISHU_KEYS")
    if not isinstance(feishu, dict):
        errors.append("FEISHU_KEYS must be a literal mapping of references")
    else:
        for market, value in feishu.items():
            if market == "enable_img":
                continue
            if market == "user_id":
                if not _valid_reference(value):
                    errors.append("FEISHU_KEYS.user_id must use a secret reference")
                continue
            if not isinstance(value, dict):
                errors.append(f"FEISHU_KEYS.{market} must be a mapping")
                continue
            for field in ("app_id", "app_secret"):
                if not _valid_reference(value.get(field)):
                    errors.append(f"FEISHU_KEYS.{market}.{field} must use a secret reference")

    scan_roots = [root / "src", root / "web", root / "script", root / "check_env.py"]
    direct_pattern = re.compile(
        r"\bconfig\.(" + "|".join(re.escape(name) for name in SENSITIVE_ATTRIBUTES) + r")\b"
    )
    for scan_root in scan_roots:
        paths = [scan_root] if scan_root.is_file() else scan_root.rglob("*.py")
        for path in paths:
            if not path.is_file() or path == config_path:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in direct_pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"direct plaintext-prone config consumer: {path.relative_to(root)}:{line} config.{match.group(1)}"
                )

    allowed_legacy = root / "src/tradingview_zy/settings_security.py"
    for path in (root / "src").rglob("*.py"):
        if path == allowed_legacy:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r'["\']fs_app_secret["\']\s*:', text):
            errors.append(f"legacy fs_app_secret persistence outside migrator: {path.relative_to(root)}")

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.root)
    if errors:
        print("Secret reference contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Secret reference contract passed: business credentials are reference-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
