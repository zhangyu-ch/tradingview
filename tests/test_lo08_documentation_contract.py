from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "script" / "remediation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_quality_gates import find_quality_gate_violations  # noqa: E402
from generate_provider_support_matrix import (  # noqa: E402
    render_support_matrix,
)


def _load_check_env():
    spec = importlib.util.spec_from_file_location("lo08_check_env", ROOT / "check_env.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(spec.name, None)


def test_environment_documentation_is_derived_from_pyproject_contract() -> None:
    module = _load_check_env()
    assert module.project_python_spec() == ">=3.11,<3.12"
    assert module._python_version_supported((3, 11, 0), ">=3.11,<3.12")
    assert not module._python_version_supported((3, 12, 0), ">=3.11,<3.12")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "项目只支持 Python 3.11" in readme
    assert "uv 0.10.0" in readme
    assert 'uv sync --locked' in readme
    assert "check_env.py" in readme


def test_readme_does_not_claim_live_order_execution_and_links_generated_matrix() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for stale_claim in ("交易执行工具", "trader 下单", "支持实盘下单"):
        assert stale_claim not in readme
    assert "不声明实盘下单能力" in readme
    assert "docs/live-trading-disabled.md" in readme
    assert "docs/provider-support-matrix.md" in readme
    assert "archive/joinquant-legacy.zip" in readme

    about_page = (
        ROOT / "web/tradingview_zy_chart/cl_app/templates/index.html"
    ).read_text(encoding="utf-8")
    assert "交易执行工具" not in about_page
    assert "多市场行情、TradingView 图表、选股监控和回测工具" in about_page


def test_joinquant_research_tree_is_archived_not_active_runtime() -> None:
    assert not (ROOT / "joinquant").exists()
    archive = ROOT / "archive" / "joinquant-legacy.zip"
    assert archive.is_file()
    assert (ROOT / "archive" / "README.md").is_file()

    expected = {
        "joinquant/#U6570#U636e#U4e0b#U8f7d.ipynb",
        "joinquant/A#U80a1#U52a8#U91cf#U6392#U884c#U9009#U80a1#U62e9#U65f6.ipynb",
        "joinquant/README.md",
        "joinquant/fun.py",
    }
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == expected
        for info in bundle.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.external_attr >> 16 == 0o100644
        legacy_source = bundle.read("joinquant/fun.py").decode("utf-8")
    assert "from jqdata import *" in legacy_source
    assert "import cl" in legacy_source


def test_provider_support_matrix_is_an_exact_registry_projection() -> None:
    output = ROOT / "docs" / "provider-support-matrix.md"
    actual = output.read_text(encoding="utf-8")
    assert actual == render_support_matrix()

    from tradingview_zy.domain import Capability
    from tradingview_zy.market_registry import MARKET_REGISTRY

    for market, spec in MARKET_REGISTRY.items():
        assert f"| `{market.value}` | {spec.ui_label} | `{spec.default_provider}` |" in actual
        for provider_name, provider in spec.providers.items():
            assert f"| `{market.value}` | `{provider_name}` |" in actual
            for capability in provider.capabilities:
                assert f"`{capability.value}`" in actual
            assert Capability.LIVE_ORDERS not in provider.capabilities


def test_support_matrix_cli_rejects_stale_output(tmp_path: Path) -> None:
    output = tmp_path / "provider-support-matrix.md"
    output.write_text(render_support_matrix() + "\nmanual drift\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "generate_provider_support_matrix.py"),
            "--check",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "stale" in result.stdout.lower()


def _copy_quality_contract(destination: Path) -> None:
    for relative in (
        ".github/workflows/tests.yml",
        ".github/workflows/repository-hygiene.yml",
        "docs/quality-gates.md",
    ):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_repository_hygiene_requires_generated_support_matrix_check(tmp_path: Path) -> None:
    assert find_quality_gate_violations(ROOT) == []
    _copy_quality_contract(tmp_path)
    hygiene = tmp_path / ".github/workflows/repository-hygiene.yml"
    hygiene.write_text(
        hygiene.read_text(encoding="utf-8").replace(
            "      - name: Reject stale generated provider support documentation\n"
            "        run: python script/remediation/generate_provider_support_matrix.py --check\n",
            "",
        ),
        encoding="utf-8",
    )
    violations = find_quality_gate_violations(tmp_path)
    assert any("generate_provider_support_matrix.py --check" in value for value in violations)


def test_removed_licensing_and_packaging_drift_does_not_return() -> None:
    assert not (ROOT / "setup.py").exists()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "Apache-2.0"' in pyproject

    active_docs = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in active_docs)
    assert "PyArmor" not in combined
    assert "pyarmor" not in combined
