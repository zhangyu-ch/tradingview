#!/usr/bin/env python3
"""Reject FIFO close paths that mutate lots before settlement validation."""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

VALIDATION_CALLS = {"close_settlement", "validate_close_settlement"}
CONSUMPTION_CALLS = {"consume_fifo_lots", "commit_fifo_lot_consumption"}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def scan_file(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        return [f"{path}: cannot parse: {exc}"]

    errors: list[str] = []
    for function in (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        validation_lines: list[int] = []
        consumption_lines: list[int] = []
        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            if name in VALIDATION_CALLS:
                validation_lines.append(node.lineno)
            elif name in CONSUMPTION_CALLS:
                consumption_lines.append(node.lineno)
        if validation_lines and consumption_lines and min(consumption_lines) < min(
            validation_lines
        ):
            errors.append(
                f"{path}:{function.lineno} {function.name} consumes FIFO lots "
                "before close-settlement validation"
            )
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "src").rglob("*.py")):
        errors.extend(scan_file(path))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate(args.root.resolve())
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print("FIFO accounting order OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
