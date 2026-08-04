#!/usr/bin/env python3
"""Run a fail-closed OSV batch query for every locked Python component."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from supply_chain_lib import (
    build_osv_report,
    canonical_json_bytes,
    load_vulnerability_policy,
    osv_packages,
)

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"


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


def query_osv(packages: list[dict[str, str]], *, timeout: float) -> Any:
    payload = {
        "queries": [
            {
                "package": {"ecosystem": "PyPI", "name": package["name"]},
                "version": package["version"],
            }
            for package in packages
        ]
    }
    request = urllib.request.Request(
        OSV_BATCH_URL,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "tradingview-zy-supply-chain/1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"OSV returned HTTP {response.status}")
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(f"OSV query failed: {error}") from error
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"OSV returned invalid JSON: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".artifacts/supply-chain/vulnerability-report.json"),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--response-fixture", type=Path)
    parser.add_argument("--scanned-at")
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    packages = osv_packages(root)
    policy = load_vulnerability_policy(root)
    if args.response_fixture:
        response = json.loads(args.response_fixture.read_text(encoding="utf-8"))
    else:
        response = query_osv(packages, timeout=args.timeout)
    scanned_at = args.scanned_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    report, unwaived = build_osv_report(
        packages,
        response,
        policy,
        scanned_at=scanned_at,
    )
    _atomic_write(output, canonical_json_bytes(report))
    print(output)
    if unwaived:
        print(f"OSV scan found {len(unwaived)} unwaived advisory record(s):")
        for advisory in unwaived:
            print(f"- {advisory['id']} {advisory['package']} {advisory['version']}")
        return 1
    print(f"OSV scan completed for {len(packages)} locked package/version pairs with no unwaived advisories.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
