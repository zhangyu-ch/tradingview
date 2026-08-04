from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web/tradingview_zy_chart/cl_app"


def test_unloaded_ai_stub_and_noop_other_tasks_are_removed() -> None:
    assert not (WEB / "static/js/ai.js").exists()
    assert not (WEB / "other_tasks.py").exists()


def test_app_factory_no_longer_registers_other_tasks_proxy() -> None:
    source = (WEB / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "_other_tasks" not in source
    assert '"other_tasks", "OtherTasks"' not in source
    assert not any(
        isinstance(node, ast.Constant) and node.value == "OtherTasks"
        for node in ast.walk(tree)
    )


def test_runtime_templates_and_scripts_do_not_reference_removed_ai_asset() -> None:
    runtime_roots = [WEB / "templates", WEB / "static", ROOT / "src", ROOT / "script"]
    references: list[str] = []
    for runtime_root in runtime_roots:
        if not runtime_root.exists():
            continue
        for path in runtime_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".js", ".html", ".css"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "ai.js" in text or "OtherTasks" in text or "other_tasks" in text:
                references.append(str(path.relative_to(ROOT)))
    assert references == []
