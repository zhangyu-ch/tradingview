from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script" / "remediation"))

from check_repository_hygiene import find_violations  # noqa: E402


def test_current_repository_contains_no_temporary_remediation_transport():
    assert find_violations(ROOT) == []


def test_hygiene_check_rejects_write_force_workflow_and_patch_parts(tmp_path):
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "apply-current-comprehensive-remediation.yml").write_text(
        "permissions:\n  contents: write\nsteps:\n  - run: git push --force-with-lease\n",
        encoding="utf-8",
    )
    remediation_dir = tmp_path / ".github" / "remediation"
    remediation_dir.mkdir(parents=True)
    (remediation_dir / "current-remediation.part.001").write_text("patch", encoding="utf-8")

    violations = find_violations(tmp_path)
    assert any("contents" in violation or "write/force" in violation for violation in violations)
    assert any("remediation transport" in violation for violation in violations)


def test_read_only_hygiene_workflow_is_allowed(tmp_path):
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "repository-hygiene.yml").write_text(
        "permissions:\n  contents: read\nsteps:\n  - run: python script/remediation/check_repository_hygiene.py\n",
        encoding="utf-8",
    )
    assert find_violations(tmp_path) == []
