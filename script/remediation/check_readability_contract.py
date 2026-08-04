#!/usr/bin/env python3
"""Enforce the executable readability baseline for runtime provider code."""
from __future__ import annotations

import ast
import argparse
from pathlib import Path

AUDITED_PROVIDERS = (
    Path("src/tradingview_zy/exchange/exchange_alpaca.py"),
    Path("src/tradingview_zy/exchange/exchange_polygon.py"),
    Path("src/tradingview_zy/exchange/exchange_baostock.py"),
)
AUDITED_BOUNDARIES = AUDITED_PROVIDERS + (
    Path("src/tradingview_zy/exchange/provider_observability.py"),
)
RUNTIME_ROOTS = (Path("src"), Path("script"), Path("web"))
FORBIDDEN_NAMES = {"_c", "_t", "_dt", "_d", "_mmd", "_ks", "req", "res", "ex"}


def _python_files(root: Path):
    for relative_root in RUNTIME_ROOTS:
        directory = root / relative_root
        if directory.is_dir():
            yield from sorted(directory.rglob("*.py"))


def _exception_is_broad(handler: ast.ExceptHandler) -> bool:
    return isinstance(handler.type, ast.Name) and handler.type.id in {"Exception", "BaseException"}


def find_readability_violations(root: Path) -> list[str]:
    root = root.resolve()
    violations: list[str] = []

    for path in _python_files(root):
        relative = path.relative_to(root)
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source, filename=str(relative))
        except SyntaxError as error:
            violations.append(f"{relative}:{error.lineno}: syntax error")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                violations.append(f"{relative}:{node.lineno}: wildcard import is forbidden (F403/F405)")

    for relative in AUDITED_BOUNDARIES:
        path = root / relative
        if not path.is_file():
            violations.append(f"missing audited readability path: {relative}")
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        lines = source.splitlines()
        tree = ast.parse(source, filename=str(relative))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _exception_is_broad(node):
                line = lines[node.lineno - 1]
                if "noqa: BLE001" not in line or " - " not in line:
                    violations.append(
                        f"{relative}:{node.lineno}: broad exception needs an explicit BLE001 rationale"
                    )
            if isinstance(node, ast.arg) and node.arg in FORBIDDEN_NAMES:
                violations.append(f"{relative}:{node.lineno}: mysterious parameter name {node.arg!r}")
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in FORBIDDEN_NAMES:
                violations.append(f"{relative}:{node.lineno}: mysterious local name {node.id!r}")

    pyproject = root / "pyproject.toml"
    config = pyproject.read_text(encoding="utf-8", errors="replace") if pyproject.is_file() else ""
    for rule in ('"F403"', '"F405"', '"BLE001"'):
        if rule not in config:
            violations.append(f"pyproject.toml must enable Ruff rule {rule.strip(chr(34))}")

    workflow = root / ".github/workflows/repository-hygiene.yml"
    workflow_text = workflow.read_text(encoding="utf-8", errors="replace") if workflow.is_file() else ""
    command = "python script/remediation/check_readability_contract.py"
    if command not in workflow_text:
        violations.append("repository hygiene must run the readability contract")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    violations = find_readability_violations(args.root)
    if violations:
        print("Readability contract failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Readability contract passed: explicit imports and audited exception boundaries are enforced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
