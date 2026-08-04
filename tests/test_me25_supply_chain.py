from __future__ import annotations

import copy
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "script" / "remediation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from supply_chain_lib import (  # noqa: E402
    artifact_bytes,
    build_osv_report,
    load_json,
    validate_generated_artifacts,
    validate_local_artifacts,
    validate_supply_chain,
    validate_vulnerability_policy,
)


def _copy_supply_inputs(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for relative in ("pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / relative, destination / relative)
    shutil.copytree(ROOT / "package", destination / "package")
    target = destination / "audit" / "supply-chain"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "audit" / "supply-chain", target)
    return destination


def test_current_repository_supply_chain_contract_and_generation_are_deterministic() -> None:
    assert validate_supply_chain(ROOT, today=dt.date(2026, 8, 4)) == []
    first = artifact_bytes(ROOT)
    second = artifact_bytes(ROOT)
    assert first == second
    assert len(load_json(ROOT / "audit/supply-chain/sbom.cdx.json")["components"]) == 155


@pytest.mark.parametrize("mutation", ["tamper", "untracked", "missing-provenance"])
def test_local_artifact_gate_rejects_tamper_untracked_and_missing_provenance(
    tmp_path: Path, mutation: str
) -> None:
    root = _copy_supply_inputs(tmp_path / mutation)
    manifest_path = root / "audit/supply-chain/local-artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_path = root / manifest["artifacts"][0]["path"]

    if mutation == "tamper":
        with first_path.open("ab") as handle:
            handle.write(b"tamper")
    elif mutation == "untracked":
        (root / "package/untracked-1.0-py3-none-any.whl").write_bytes(b"not-a-wheel")
    else:
        manifest["artifacts"][0].pop("origin")
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    errors = validate_local_artifacts(root)
    joined = "\n".join(errors)
    if mutation == "tamper":
        assert "sha256 mismatch" in joined
    elif mutation == "untracked":
        assert "untracked local artifact" in joined
    else:
        assert "missing provenance field origin" in joined


def test_generated_artifact_gate_rejects_stale_evidence(tmp_path: Path) -> None:
    root = _copy_supply_inputs(tmp_path / "stale")
    sbom = root / "audit/supply-chain/sbom.cdx.json"
    sbom.write_text(sbom.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert validate_generated_artifacts(root) == [
        "stale generated artifact: audit/supply-chain/sbom.cdx.json"
    ]


def test_vulnerability_policy_rejects_expired_duplicate_and_incomplete_waivers() -> None:
    policy = {
        "schema_version": 1,
        "exceptions": [
            {
                "id": "OSV-TEST",
                "package": "Example_Package",
                "owner": "security@example.invalid",
                "reason": "temporary mitigation",
                "expires": "2026-08-03",
            },
            {
                "id": "OSV-TEST",
                "package": "example-package",
                "owner": "",
                "reason": "duplicate",
                "expires": "not-a-date",
            },
        ],
    }
    errors = validate_vulnerability_policy(policy, today=dt.date(2026, 8, 4))
    joined = "\n".join(errors)
    assert "expired" in joined
    assert "duplicate vulnerability exception" in joined
    assert ".owner is required" in joined
    assert "must be YYYY-MM-DD" in joined


def test_osv_response_is_fail_closed_and_honours_only_valid_waivers() -> None:
    packages = [
        {"name": "alpha", "version": "1.0"},
        {"name": "beta", "version": "2.0"},
    ]
    clean, unwaived = build_osv_report(
        packages,
        {"results": [{}, {}]},
        {"schema_version": 1, "exceptions": []},
        scanned_at="2026-08-04T12:00:00+00:00",
        today=dt.date(2026, 8, 4),
    )
    assert clean["scan_completed"] is True
    assert clean["unwaived_advisory_count"] == 0
    assert unwaived == []

    response = {
        "results": [
            {"vulns": [{"id": "OSV-TEST", "summary": "test advisory"}]},
            {},
        ]
    }
    vulnerable, unwaived = build_osv_report(
        packages,
        response,
        {"schema_version": 1, "exceptions": []},
        scanned_at="2026-08-04T12:00:00+00:00",
        today=dt.date(2026, 8, 4),
    )
    assert vulnerable["unwaived_advisory_count"] == 1
    assert unwaived[0]["id"] == "OSV-TEST"

    policy = {
        "schema_version": 1,
        "exceptions": [
            {
                "id": "OSV-TEST",
                "package": "alpha",
                "owner": "security@example.invalid",
                "reason": "temporary controlled acceptance",
                "expires": "2026-08-05",
            }
        ],
    }
    waived, unwaived = build_osv_report(
        packages,
        response,
        policy,
        scanned_at="2026-08-04T12:00:00+00:00",
        today=dt.date(2026, 8, 4),
    )
    assert waived["advisories"][0]["waived"] is True
    assert unwaived == []

    with pytest.raises(ValueError, match="count mismatch"):
        build_osv_report(
            packages,
            {"results": [{}]},
            policy,
            scanned_at="2026-08-04T12:00:00+00:00",
            today=dt.date(2026, 8, 4),
        )
