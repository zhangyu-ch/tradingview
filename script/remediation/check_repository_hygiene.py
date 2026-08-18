#!/usr/bin/env python3
"""Fail when temporary remediation transport or archived-branch workflow references enter .github."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN_EXACT_PATHS = {
    ".github/PR_BODY_CURRENT_REMEDIATION.md",
    ".github/workflows/apply-current-comprehensive-remediation.yml",
    ".github/workflows/finalize-current-comprehensive-remediation.yml",
    ".github/workflows/push-current-comprehensive-remediation.yml",
}
FORBIDDEN_PATH_PARTS = {".github/remediation"}
FORBIDDEN_NAME_PATTERNS = (
    re.compile(r"current-remediation\.part\.", re.IGNORECASE),
    re.compile(r"current-comprehensive-remediation", re.IGNORECASE),
)
FORBIDDEN_WORKFLOW_PATTERNS = (
    re.compile(r"(?mi)^\s*contents\s*:\s*write\s*(?:#.*)?$"),
    re.compile(r"(?i)git\s+reset\s+--soft\b"),
    re.compile(r"(?i)git\s+push\b[^\n]*(?:--force(?:-with-lease)?|-f\b)"),
    re.compile(r"(?i)\bmaster\b"),
)


def find_violations(root: Path) -> list[str]:
    root = root.resolve()
    github_dir = root / ".github"
    if not github_dir.exists():
        return []

    violations: list[str] = []
    for path in sorted(github_dir.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in FORBIDDEN_EXACT_PATHS:
            violations.append(f"forbidden temporary path: {relative}")
        if any(relative == part or relative.startswith(f"{part}/") for part in FORBIDDEN_PATH_PARTS):
            violations.append(f"forbidden remediation transport directory: {relative}")
        if any(pattern.search(relative) for pattern in FORBIDDEN_NAME_PATTERNS):
            violations.append(f"forbidden remediation transport name: {relative}")

        if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
            if pattern.search(text):
                violations.append(f"forbidden workflow content in {relative}: {pattern.pattern}")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    violations = find_violations(args.root)
    if violations:
        print("Repository hygiene check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Repository hygiene check passed: no remediation transport, force-push workflow, or archived-branch workflow reference found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
