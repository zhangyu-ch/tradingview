#!/usr/bin/env python3
"""Update one issue's remediation record and regenerate the Markdown report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from parse_issue_report import render_markdown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("issue_id")
    parser.add_argument("--state", type=Path, default=Path("audit/remediation_state.json"))
    parser.add_argument("--report", type=Path, default=Path("remediation_report.md"))
    parser.add_argument("--data", type=Path, required=True, help="JSON object with remediation fields")
    args = parser.parse_args()

    ledger = json.loads(args.state.read_text(encoding="utf-8"))
    update = json.loads(args.data.read_text(encoding="utf-8"))
    matches = [item for item in ledger if item["issue_id"] == args.issue_id]
    if len(matches) != 1:
        raise SystemExit(f"expected one issue {args.issue_id!r}, found {len(matches)}")

    remediation = matches[0]["remediation"]
    unknown = sorted(set(update) - set(remediation) - {"commit_subject"})
    if unknown:
        raise SystemExit(f"unknown remediation fields: {unknown}")
    remediation.update(update)
    remediation.setdefault("commit_subject", "")

    args.state.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(
        render_markdown(ledger, "audit/tradingview_current_open_issues_v1.md"),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
