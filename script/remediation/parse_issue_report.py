#!/usr/bin/env python3
"""Parse the immutable Markdown issue report into a compact remediation ledger."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

INDEX_ROW_RE = re.compile(
    r"^\|(?P<index>\d+)\|\[`(?P<issue_id>[^`]+)`\]\(#[^)]+\)\|(?P<status>[^|]+)\|"
    r"(?P<severity>[^|]+)\|(?P<domain>[^|]+)\|(?P<title>[^|]+)\|$"
)
SECTION_RE = re.compile(
    r"<a id=\"(?P<anchor>[^\"]+)\"></a>\s*\n\s*###\s+(?P<issue_id>[^\s]+)\s+·\s+(?P<title>[^\n]+)\n(?P<body>.*?)(?=\n<a id=\"|\Z)",
    re.S,
)
FIELD_PATTERNS = {
    "v7_status": re.compile(r"^- \*\*V7 状态：\*\*\s*(.+)$", re.M),
    "severity_confidence": re.compile(r"^- \*\*严重程度 / 可信度：\*\*\s*(.+)$", re.M),
    "latest_conclusion": re.compile(r"^- \*\*最新结论：\*\*\s*(.+)$", re.M),
    "basis": re.compile(r"^- \*\*(?:影响与)?判定依据：\*\*\s*(.+)$", re.M),
    "next_step": re.compile(r"^- \*\*(?:仍有什么问题 / 下一步|修复建议 / 关闭条件)：\*\*\s*(.+)$", re.M),
    "minimum_reproduction": re.compile(r"^- \*\*最小复现：\*\*\s*(.+)$", re.M),
}
EVIDENCE_RE = re.compile(r"^- \[`?([^\]`]+)`?\]\(([^)]+)\)\s*—\s*(.+)$", re.M)


def parse_report(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    index_entries: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = INDEX_ROW_RE.match(line.strip())
        if not match:
            continue
        item = {key: value.strip() for key, value in match.groupdict().items()}
        item["index"] = int(item["index"])
        index_entries.append(item)

    sections: dict[str, dict[str, Any]] = {}
    for match in SECTION_RE.finditer(text):
        issue_id = match.group("issue_id").strip()
        body = match.group("body")
        # Only the current V7 block is authoritative; nested historical details are preserved in source.
        current_body = body.split("\n<details>", 1)[0]
        fields: dict[str, Any] = {
            "source_title": match.group("title").strip(),
            "source_anchor": match.group("anchor").strip(),
        }
        for name, pattern in FIELD_PATTERNS.items():
            field_match = pattern.search(current_body)
            fields[name] = field_match.group(1).strip() if field_match else ""
        fields["evidence"] = [
            {"label": label.strip(), "url": url.strip(), "note": note.strip()}
            for label, url, note in EVIDENCE_RE.findall(current_body)
        ]
        sections[issue_id] = fields

    if len(index_entries) != 81:
        raise ValueError(f"expected 81 index entries, found {len(index_entries)}")

    missing_sections = [entry["issue_id"] for entry in index_entries if entry["issue_id"] not in sections]
    if missing_sections:
        raise ValueError(f"missing detail sections for: {missing_sections}")

    ledger = []
    for entry in index_entries:
        issue_id = entry["issue_id"]
        ledger.append(
            {
                **entry,
                **sections[issue_id],
                "remediation": {
                    "status": "待处理",
                    "problem_verified": None,
                    "problem_summary": "",
                    "fix_summary": "",
                    "verification_performed": None,
                    "verification_method": [],
                    "verification_result": "",
                    "commit": "",
                    "commit_subject": "",
                    "files_changed": [],
                    "limitations": [],
                },
            }
        )
    return ledger


def render_markdown(ledger: list[dict[str, Any]], source_path: str) -> str:
    completed = sum(
        1 for item in ledger if item["remediation"]["status"].startswith("已完成")
    )
    lines = [
        "# TradingView 当前开放问题逐条修复记录",
        "",
        f"- **原始问题清单：** `{source_path}`（只读保留）",
        f"- **问题总数：** {len(ledger)}",
        f"- **已完成：** {completed}",
        f"- **待处理：** {len(ledger) - completed}",
        "- **提交规则：** 每个问题一个本地 Git 提交，直接落在 `main`，不推送远程。",
        "- **判定规则：** 仅在根因修复且自动化验证通过后标记“已完成”；真实外部系统未联调的限制会单独列出。",
        "",
        "## 总览",
        "",
        "|序号|编号|严重度|领域|原状态|本轮状态|验证结果|提交|",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for item in ledger:
        remediation = item["remediation"]
        commit_value = remediation.get("commit") or remediation.get("commit_subject") or ""
        commit_table = (
            f"`{commit_value[:12]}`" if remediation.get("commit") else
            (f"`{commit_value.split(':', 1)[0]}`" if commit_value else "—")
        )
        lines.append(
            "|{index}|`{issue_id}`|{severity}|{domain}|{status}|{rstatus}|{vresult}|{commit}|".format(
                index=item["index"],
                issue_id=item["issue_id"],
                severity=item["severity"],
                domain=item["domain"].replace("|", "\\|"),
                status=item["status"].replace("|", "\\|"),
                rstatus=remediation["status"],
                vresult=(remediation["verification_result"] or "—").replace("|", "\\|"),
                commit=commit_table,
            )
        )

    lines.extend(["", "## 逐条记录", ""])
    for item in ledger:
        remediation = item["remediation"]
        commit_detail = (
            f"`{remediation['commit']}`"
            if remediation.get("commit")
            else (remediation.get("commit_subject") or "待提交")
        )
        lines.extend(
            [
                f"### {item['index']:02d}. {item['issue_id']} · {item['title']}",
                "",
                f"- **原始状态 / 严重度 / 领域：** {item['status']} / {item['severity']} / {item['domain']}",
                f"- **本轮状态：** {remediation['status']}",
                f"- **问题是否存在：** {_bool_text(remediation['problem_verified'])}",
                f"- **a. 这个问题是什么？** {remediation['problem_summary'] or '待验证'}",
                f"- **b. 我是怎么修复的？** {remediation['fix_summary'] or '待处理'}",
                f"- **c. 修复后是否验证？** {_bool_text(remediation['verification_performed'])}",
                "- **d. 怎么验证的？**",
            ]
        )
        methods = remediation["verification_method"] or ["待处理"]
        lines.extend([f"  - {method}" for method in methods])
        lines.extend(
            [
                f"- **e. 验证是否通过？** {remediation['verification_result'] or '待处理'}",
                f"- **提交：** {commit_detail}",
                f"- **修改文件：** {', '.join(f'`{p}`' for p in remediation['files_changed']) if remediation['files_changed'] else '待处理'}",
            ]
        )
        if remediation["limitations"]:
            lines.append("- **验证限制：**")
            lines.extend([f"  - {limitation}" for limitation in remediation["limitations"]])
        lines.extend(
            [
                "- **原报告最新结论：** " + (item.get("latest_conclusion") or "未提取"),
                "- **原报告建议：** " + (item.get("next_step") or "未提取"),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _bool_text(value: Any) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    return "待验证"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--markdown", dest="markdown_path", type=Path, required=True)
    args = parser.parse_args()
    ledger = parse_report(args.source)
    args.json_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_path.write_text(render_markdown(ledger, str(args.source)), encoding="utf-8")


if __name__ == "__main__":
    main()
