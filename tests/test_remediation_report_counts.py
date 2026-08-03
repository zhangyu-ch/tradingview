from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_report_module():
    module_path = Path(__file__).parents[1] / "script" / "remediation" / "parse_issue_report.py"
    spec = importlib.util.spec_from_file_location("parse_issue_report", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _issue(index: int, status: str) -> dict:
    return {
        "index": index,
        "issue_id": f"TEST-{index}",
        "severity": "低",
        "domain": "Test",
        "status": "待处理",
        "title": "fixture",
        "latest_conclusion": "fixture",
        "next_step": "fixture",
        "remediation": {
            "status": status,
            "problem_verified": True,
            "problem_summary": "fixture",
            "fix_summary": "fixture",
            "verification_performed": True,
            "verification_method": ["fixture"],
            "verification_result": "通过",
            "commit": "",
            "commit_subject": "",
            "files_changed": [],
            "limitations": [],
        },
    }


def test_render_markdown_counts_all_completed_status_variants() -> None:
    module = _load_report_module()
    ledger = [
        _issue(1, "已完成"),
        _issue(2, "已完成（通过移除不支持能力）"),
        _issue(3, "已完成（共享修复已复验）"),
        _issue(4, "待处理"),
    ]

    report = module.render_markdown(ledger, "issues.md")

    assert "- **已完成：** 3" in report
    assert "- **待处理：** 1" in report
