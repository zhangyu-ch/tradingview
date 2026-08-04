from __future__ import annotations

import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "script/remediation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_quality_gates import find_quality_gate_violations  # noqa: E402
from prepare_test_config import prepare_test_config  # noqa: E402


def _copy_gate_files(destination: Path) -> None:
    for relative in (
        ".github/workflows/tests.yml",
        ".github/workflows/repository-hygiene.yml",
        "docs/quality-gates.md",
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_current_repository_has_complete_quality_gate_contract() -> None:
    assert find_quality_gate_violations(ROOT) == []


def test_missing_tests_workflow_is_rejected(tmp_path: Path) -> None:
    assert find_quality_gate_violations(tmp_path) == [
        "missing .github/workflows/tests.yml"
    ]


def test_complete_unit_suite_cannot_be_weakened_with_ignore(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            "uv run pytest -q\n", "uv run pytest -q --ignore=tests/test_footprint.py\n", 1
        ),
        encoding="utf-8",
    )
    assert any("must not bypass" in value for value in find_quality_gate_violations(tmp_path))


def test_provider_matrix_rejects_removed_contract_test(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            "          tests/test_me15_futu_context_lifecycle.py\n", ""
        ),
        encoding="utf-8",
    )
    assert any("test_me15_futu_context_lifecycle.py" in value for value in find_quality_gate_violations(tmp_path))


def test_mysql_gate_requires_real_service_and_enable_flag(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    text = workflow.read_text(encoding="utf-8").replace("image: mysql:8.0", "image: sqlite")
    text = text.replace('RUN_MYSQL_TESTS: "1"', 'RUN_MYSQL_TESTS: "0"')
    workflow.write_text(text, encoding="utf-8")
    violations = find_quality_gate_violations(tmp_path)
    assert any("real MySQL 8.0" in value for value in violations)
    assert any("RUN_MYSQL_TESTS" in value for value in violations)


def test_browser_gate_requires_real_chromium_and_enable_flag(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    text = workflow.read_text(encoding="utf-8").replace(
        "playwright install --with-deps chromium", "echo browser omitted"
    )
    text = text.replace('RUN_BROWSER_TESTS: "1"', 'RUN_BROWSER_TESTS: "0"')
    workflow.write_text(text, encoding="utf-8")
    violations = find_quality_gate_violations(tmp_path)
    assert any("real Chromium" in value for value in violations)
    assert any("RUN_BROWSER_TESTS" in value for value in violations)


def test_read_only_permission_and_hygiene_bootstrap_are_required(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace("contents: read", "contents: write"),
        encoding="utf-8",
    )
    hygiene = tmp_path / ".github/workflows/repository-hygiene.yml"
    hygiene.write_text(
        hygiene.read_text(encoding="utf-8").replace(
            "      - name: Verify executable quality-gate contract\n"
            "        run: python script/remediation/check_quality_gates.py\n",
            "",
        ),
        encoding="utf-8",
    )
    violations = find_quality_gate_violations(tmp_path)
    assert any("read-only" in value for value in violations)
    assert any("bootstrap" in value for value in violations)


def test_prepare_test_config_is_atomic_private_and_uses_repo_runtime(tmp_path: Path) -> None:
    source = tmp_path / "src/tradingview_zy/config.py.demo"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import pathlib\nDATA_PATH = '.prod'\nDB_DATABASE = 'prod'\n",
        encoding="utf-8",
    )
    destination = prepare_test_config(tmp_path)
    text = destination.read_text(encoding="utf-8")

    assert str((tmp_path / ".ci-test-runtime").resolve()) in text
    assert "DB_DATABASE = 'ci_test'" in text
    if sys.platform != "win32":
        assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_footprint_uses_public_timestamp_api() -> None:
    source = (ROOT / "src/tradingview_zy/footprint.py").read_text(encoding="utf-8")
    assert "from tradingview_zy.web_payloads import datetime_to_timestamp_seconds" in source
    assert "_datetime_to_timestamp_seconds" not in source


def test_supply_chain_gate_requires_lock_evidence_osv_and_exact_uv_pin(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    text = workflow.read_text(encoding="utf-8")
    text = text.replace('python -m pip install "uv==0.10.0"', 'python -m pip install uv', 1)
    text = text.replace("      - name: Run live fail-closed OSV scan\n", "      - name: OSV scan removed\n", 1)
    text = text.replace(
        "        run: >-\n          python script/remediation/scan_osv.py\n          --output .artifacts/supply-chain/vulnerability-report.json\n",
        "        run: echo scan removed\n",
        1,
    )
    workflow.write_text(text, encoding="utf-8")
    violations = find_quality_gate_violations(tmp_path)
    assert any("exact uv 0.10.0" in value for value in violations)
    assert any("scan_osv.py" in value for value in violations)


def test_supply_chain_gate_and_uv_download_policy_are_documented_and_stable(tmp_path: Path) -> None:
    _copy_gate_files(tmp_path)
    workflow = tmp_path / ".github/workflows/tests.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8").replace(
            "env:\n  UV_PYTHON_DOWNLOADS: never\n", "", 1
        ),
        encoding="utf-8",
    )
    violations = find_quality_gate_violations(tmp_path)
    assert any("UV_PYTHON_DOWNLOADS" in value for value in violations)
