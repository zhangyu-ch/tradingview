#!/usr/bin/env python3
"""Generate deterministic SBOM, license, and offline vulnerability evidence."""
from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from supply_chain_lib import artifact_bytes


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--installed-licenses", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    generated = artifact_bytes(root, installed_licenses=args.installed_licenses)
    if args.check:
        if args.output_dir is not None or args.installed_licenses:
            parser.error("--check only validates the committed offline artifacts")
        errors = []
        for relative, expected in generated.items():
            path = root / relative
            if not path.is_file():
                errors.append(f"missing generated artifact: {relative.as_posix()}")
            elif path.read_bytes() != expected:
                errors.append(f"stale generated artifact: {relative.as_posix()}")
        if errors:
            print("Generated supply-chain evidence is stale:")
            for error in errors:
                print(f"- {error}")
            return 1
        print("Generated supply-chain evidence is current.")
        return 0

    output_dir = args.output_dir.resolve() if args.output_dir else None
    for relative, content in generated.items():
        destination = (output_dir / relative.name) if output_dir else (root / relative)
        _atomic_write(destination, content)
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
