"""Run the bundled PineJS runtime against historical and realtime indicator bars."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("indicator", ["rsx", "hdly", "ama", "cdbb", "macdbl"])
def test_indicator_series_preserve_history_and_realtime_updates(indicator):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the shipped PineJS runtime regression")
    result = subprocess.run(
        [node, str(ROOT / "tests/js/indicator_realtime.cjs"), f"--indicator={indicator}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "B20 passed:" in result.stdout
    if indicator == "ama":
        assert "AMA N=1 passed: numerical oracle" in result.stdout
