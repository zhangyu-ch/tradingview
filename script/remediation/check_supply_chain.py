#!/usr/bin/env python3
"""Validate locked dependency evidence, local artifacts, and generated reports."""
from __future__ import annotations

import argparse
from pathlib import Path

from supply_chain_lib import validate_supply_chain


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = validate_supply_chain(args.root)
    if errors:
        print("Supply-chain contract failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Supply-chain contract passed: lock, local artifacts, policy, and generated evidence agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
