#!/usr/bin/env python3
"""Fail when dependency installation entry points drift from project metadata."""
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

EXPECTED_PYTHON = ">=3.11,<3.12"
EXPECTED_LOCK_PYTHON = "==3.11.*"
EXPECTED_WEBSOCKETS = ">=13.1,<14"
EXPECTED_WEBSOCKETS_VERSION = "13.1"
FORBIDDEN_SECONDARY_SOURCES = (
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
)


def _project_name(raw: str) -> str:
    return re.sub(r"[-_.]+", "-", raw).lower()


def _dependency_name(requirement: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", requirement)
    if not match:
        raise ValueError(f"cannot parse dependency: {requirement!r}")
    return _project_name(match.group(1))


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    pyproject_path = root / "pyproject.toml"
    lock_path = root / "uv.lock"

    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [f"cannot read dependency metadata: {exc}"]

    for relative in FORBIDDEN_SECONDARY_SOURCES:
        if (root / relative).exists():
            errors.append(
                f"{relative} is a forbidden second dependency source; use pyproject.toml + uv.lock"
            )

    project = pyproject.get("project", {})
    if project.get("requires-python") != EXPECTED_PYTHON:
        errors.append(
            f"pyproject requires-python must be {EXPECTED_PYTHON!r}; "
            f"got {project.get('requires-python')!r}"
        )

    raw_dependencies = project.get("dependencies", [])
    direct = {_dependency_name(item): item for item in raw_dependencies}
    if "chardet" in direct:
        errors.append("chardet must not be a direct dependency")
    if direct.get("websockets") != f"websockets{EXPECTED_WEBSOCKETS}":
        errors.append(
            "websockets must be constrained to "
            f"{EXPECTED_WEBSOCKETS}; got {direct.get('websockets')!r}"
        )

    if lock.get("requires-python") != EXPECTED_LOCK_PYTHON:
        errors.append(
            f"uv.lock requires-python must be {EXPECTED_LOCK_PYTHON!r}; "
            f"got {lock.get('requires-python')!r}"
        )

    packages = lock.get("package", [])
    by_name: dict[str, list[dict]] = {}
    for package in packages:
        by_name.setdefault(_project_name(package.get("name", "")), []).append(package)
    if "chardet" in by_name:
        errors.append("uv.lock still contains the incompatible chardet package")
    websockets = by_name.get("websockets", [])
    versions = sorted({str(package.get("version")) for package in websockets})
    if versions != [EXPECTED_WEBSOCKETS_VERSION]:
        errors.append(
            f"uv.lock must pin websockets {EXPECTED_WEBSOCKETS_VERSION}; got {versions!r}"
        )

    root_name = _project_name(project.get("name", ""))
    root_candidates = by_name.get(root_name, [])
    root_package = next(
        (
            package
            for package in root_candidates
            if package.get("source", {}).get("virtual") == "."
        ),
        root_candidates[0] if root_candidates else None,
    )
    if not root_package:
        errors.append(f"uv.lock has no root package {root_name!r}")
        return sorted(set(errors))

    locked_direct = {
        _project_name(item.get("name", ""))
        for item in root_package.get("dependencies", [])
    }
    expected_direct = set(direct)
    if locked_direct != expected_direct:
        missing = sorted(expected_direct - locked_direct)
        extra = sorted(locked_direct - expected_direct)
        errors.append(f"uv.lock root dependency drift: missing={missing}, extra={extra}")

    requires_dist = {
        _project_name(item.get("name", "")): item
        for item in root_package.get("metadata", {}).get("requires-dist", [])
    }
    if "chardet" in requires_dist:
        errors.append("uv.lock root metadata still declares chardet")
    ws_metadata = requires_dist.get("websockets")
    if not ws_metadata or ws_metadata.get("specifier") != EXPECTED_WEBSOCKETS:
        errors.append(
            "uv.lock root metadata must preserve the websockets compatibility range"
        )

    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("dependency contract OK: pyproject.toml + uv.lock are the only resolution source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
