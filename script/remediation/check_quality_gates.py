#!/usr/bin/env python3
"""Validate the repository's executable quality-gate contract."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

UV_PIN = 'python -m pip install "uv==0.10.0"'
REQUIRED_JOBS = (
    "unit-contracts",
    "provider-contracts",
    "mysql-contracts",
    "browser-contracts",
    "windows-contracts",
    "supply-chain-contracts",
)
REQUIRED_PROVIDER_TESTS = (
    "test_hi13_binance_pagination.py",
    "test_hi14_tq_lifecycle.py",
    "test_me11_baostock_reliability.py",
    "test_me12_tdx_contracts.py",
    "test_me14_tdx_us_timezone.py",
    "test_me15_futu_context_lifecycle.py",
    "test_me16_ib_rpc_timeout.py",
    "test_me17_qmt_contracts.py",
    "test_mx17_tdx_node_selection.py",
    "test_nx20_tdx_bounded_retry.py",
    "test_footprint.py",
)


def _job_segment(text: str, job: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [a-z0-9][a-z0-9-]*:\n|\Z)",
        text,
    )
    return match.group("body") if match else ""


def find_quality_gate_violations(root: Path) -> list[str]:
    root = root.resolve()
    workflow_path = root / ".github/workflows/tests.yml"
    hygiene_path = root / ".github/workflows/repository-hygiene.yml"
    docs_path = root / "docs/quality-gates.md"
    violations: list[str] = []

    if not workflow_path.is_file():
        return ["missing .github/workflows/tests.yml"]
    workflow = workflow_path.read_text(encoding="utf-8", errors="replace")

    if not re.search(r"(?m)^permissions:\n\s+contents:\s+read\s*$", workflow):
        violations.append("tests workflow must use read-only contents permission")
    if "cancel-in-progress: true" not in workflow:
        violations.append("tests workflow must cancel superseded runs")
    if not re.search(r'(?m)^env:\n\s+UV_PYTHON_DOWNLOADS:\s+never\s*$', workflow):
        violations.append("tests workflow must set UV_PYTHON_DOWNLOADS=never")

    for job in REQUIRED_JOBS:
        segment = _job_segment(workflow, job)
        if not segment:
            violations.append(f"missing stable job: {job}")
            continue
        if "timeout-minutes:" not in segment:
            violations.append(f"job {job} must define timeout-minutes")
        if 'python-version: "3.11"' not in segment:
            violations.append(f"job {job} must run Python 3.11")
        if UV_PIN not in segment:
            violations.append(f"job {job} must install exact uv 0.10.0")
        if "uv sync --locked" not in segment:
            violations.append(f"job {job} must install from uv.lock")

    if re.search(r"python -m pip install uv(?:\s|$)", workflow):
        violations.append("tests workflow must not install unpinned uv")

    unit = _job_segment(workflow, "unit-contracts")
    if "uv run pytest -q" not in unit:
        violations.append("unit-contracts must run the complete pytest suite")
    for bypass in ("--ignore", "--deselect", "--continue-on-collection-errors", " -k "):
        if bypass in unit:
            violations.append(f"unit-contracts must not bypass tests with {bypass.strip()}")

    provider = _job_segment(workflow, "provider-contracts")
    if "-W error" not in provider:
        violations.append("provider-contracts must treat warnings as errors")
    for filename in REQUIRED_PROVIDER_TESTS:
        if filename not in provider:
            violations.append(f"provider-contracts missing {filename}")

    mysql = _job_segment(workflow, "mysql-contracts")
    if "image: mysql:8.0" not in mysql:
        violations.append("mysql-contracts must use a real MySQL 8.0 service")
    if 'RUN_MYSQL_TESTS: "1"' not in mysql:
        violations.append("mysql-contracts must enable RUN_MYSQL_TESTS")
    if "tests/test_me29_mysql_gate.py" not in mysql:
        violations.append("mysql-contracts must execute the MySQL gate test")

    browser = _job_segment(workflow, "browser-contracts")
    if "playwright install --with-deps chromium" not in browser:
        violations.append("browser-contracts must install real Chromium")
    if 'RUN_BROWSER_TESTS: "1"' not in browser:
        violations.append("browser-contracts must enable RUN_BROWSER_TESTS")
    if "tests/test_me29_browser_dom.py" not in browser:
        violations.append("browser-contracts must execute the DOM gate test")

    windows = _job_segment(workflow, "windows-contracts")
    if "runs-on: windows-latest" not in windows:
        violations.append("windows-contracts must run on windows-latest")
    for filename in (
        "tests/test_me25_supply_chain.py",
        "tests/test_me26_scheduler_lifecycle.py",
        "tests/test_me27_secret_management.py",
        "tests/test_me29_quality_gates.py",
    ):
        if filename not in windows:
            violations.append(f"windows-contracts missing {filename}")

    supply = _job_segment(workflow, "supply-chain-contracts")
    for command in (
        "uv lock --check",
        "python script/remediation/check_supply_chain.py",
        "python script/remediation/generate_supply_chain_artifacts.py --check",
        "python script/remediation/scan_osv.py",
        "actions/upload-artifact@v4",
    ):
        if command not in supply:
            violations.append(f"supply-chain-contracts missing {command}")

    if not hygiene_path.is_file():
        violations.append("missing repository-hygiene workflow")
    else:
        hygiene = hygiene_path.read_text(encoding="utf-8", errors="replace")
        hygiene_commands = (
            "python script/remediation/check_quality_gates.py",
            "python script/remediation/check_readability_contract.py",
            "python script/remediation/check_supply_chain.py",
            "python script/remediation/generate_supply_chain_artifacts.py --check",
            "python script/remediation/generate_provider_support_matrix.py --check",
        )
        for command in hygiene_commands:
            if command not in hygiene:
                if command.endswith("check_quality_gates.py"):
                    violations.append("repository hygiene must bootstrap the quality-gate checker")
                else:
                    violations.append(f"repository hygiene must run {command}")

    if not docs_path.is_file():
        violations.append("missing docs/quality-gates.md")
    else:
        docs = docs_path.read_text(encoding="utf-8", errors="replace")
        for job in REQUIRED_JOBS:
            if f"`{job}`" not in docs:
                violations.append(f"quality-gate documentation missing {job}")
        if "branch protection" not in docs.lower():
            violations.append("quality-gate documentation must describe branch protection")
        if "sandbox" not in docs.lower():
            violations.append("quality-gate documentation must preserve real-provider sandbox limits")
        if "osv" not in docs.lower() or "cyclonedx" not in docs.lower():
            violations.append("quality-gate documentation must describe OSV and CycloneDX evidence")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    violations = find_quality_gate_violations(args.root)
    if violations:
        print("Quality-gate contract failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Quality-gate contract passed: six stable executable jobs are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
