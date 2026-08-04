#!/usr/bin/env python3
"""Create the ignored local config used by isolated CI tests."""
from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path


def prepare_test_config(root: Path, target: Path | None = None) -> Path:
    root = root.resolve()
    source = root / "src/tradingview_zy/config.py.demo"
    destination = target or root / "src/tradingview_zy/config.py"
    runtime = root / ".ci-test-runtime"
    text = source.read_text(encoding="utf-8")
    text, count = re.subn(
        r'^DATA_PATH\s*=\s*["\'][^"\']*["\']\s*$',
        f'DATA_PATH = {str(runtime)!r}',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("config template must contain exactly one DATA_PATH assignment")
    text, count = re.subn(
        r'^DB_DATABASE\s*=\s*["\'][^"\']*["\']\s*$',
        "DB_DATABASE = 'ci_test'",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("config template must contain exactly one DB_DATABASE assignment")

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    destination = prepare_test_config(args.root, args.target)
    print(f"Prepared isolated test configuration: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
