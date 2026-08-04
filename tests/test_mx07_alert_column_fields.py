from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALERT_JS = ROOT / "web/tradingview_zy_chart/cl_app/static/js/alert.js"


def _task_columns_source() -> str:
    source = ALERT_JS.read_text(encoding="utf-8")
    start = source.index('elem: "#table_alerts"')
    end = source.index('// 行双击事件', start)
    return source[start:end]


def test_alert_task_columns_use_layui_field_key() -> None:
    source = ALERT_JS.read_text(encoding="utf-8")
    assert "filed:" not in source
    columns = _task_columns_source()
    expected = {
        "task_name",
        "zx_group",
        "frequency",
        "interval_minutes",
        "strategy_config",
        "strategy_kwargs",
        "strategy_memo",
        "is_send_msg",
        "is_run",
    }
    fields = re.findall(r'\bfield:\s*"([^"]+)"', columns)
    assert set(fields) == expected
    assert len(fields) == len(expected)


def test_sortable_columns_have_their_own_field_binding() -> None:
    columns = _task_columns_source()
    for field in ("interval_minutes", "is_send_msg", "is_run"):
        pattern = rf'\{{\s*field:\s*"{field}"[\s\S]*?sort:\s*true[\s\S]*?\}}'
        assert re.search(pattern, columns), field


def test_alert_javascript_syntax() -> None:
    subprocess.run(["node", "--check", str(ALERT_JS)], check=True, capture_output=True)
