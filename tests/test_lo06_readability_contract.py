from __future__ import annotations

import importlib.util
import logging
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "script/remediation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_readability_contract import find_readability_violations  # noqa: E402
from tradingview_zy.domain import ProviderResponseError, ProviderUnavailableError

_PROVIDER_SPEC = importlib.util.spec_from_file_location(
    "lo06_provider_observability",
    ROOT / "src/tradingview_zy/exchange/provider_observability.py",
)
assert _PROVIDER_SPEC is not None and _PROVIDER_SPEC.loader is not None
_PROVIDER_MODULE = importlib.util.module_from_spec(_PROVIDER_SPEC)
_PROVIDER_SPEC.loader.exec_module(_PROVIDER_MODULE)
call_provider = _PROVIDER_MODULE.call_provider


def test_current_repository_satisfies_readability_contract() -> None:
    assert find_readability_violations(ROOT) == []


def test_wildcard_import_is_rejected(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "src", tmp_path / "src")
    shutil.copytree(ROOT / "script", tmp_path / "script")
    shutil.copytree(ROOT / "web", tmp_path / "web")
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    target = tmp_path / "src/tradingview_zy/exchange/exchange_alpaca.py"
    target.write_text("from package import *\n", encoding="utf-8")
    assert any("wildcard import" in item for item in find_readability_violations(tmp_path))


def test_unexplained_broad_exception_and_mysterious_name_are_rejected(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "src", tmp_path / "src")
    shutil.copytree(ROOT / "script", tmp_path / "script")
    shutil.copytree(ROOT / "web", tmp_path / "web")
    shutil.copytree(ROOT / ".github", tmp_path / ".github")
    shutil.copy2(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    target = tmp_path / "src/tradingview_zy/exchange/exchange_polygon.py"
    target.write_text(
        "def run(req):\n    try:\n        return req()\n    except Exception:\n        return None\n",
        encoding="utf-8",
    )
    violations = find_readability_violations(tmp_path)
    assert any("broad exception" in item for item in violations)
    assert any("mysterious" in item for item in violations)


def test_provider_boundary_logs_stable_context_and_maps_network_failure(caplog) -> None:
    logger = logging.getLogger("test.provider")
    with caplog.at_level(logging.WARNING):
        with pytest.raises(ProviderUnavailableError):
            call_provider(
                lambda: (_ for _ in ()).throw(TimeoutError("secret-token")),
                logger=logger,
                provider="alpaca",
                market="us",
                code="AAPL",
                operation_name="get_stock_bars",
                request_id="request-123",
            )
    text = caplog.text
    assert "market=us" in text
    assert "code=AAPL" in text
    assert "request_id=request-123" in text
    assert "operation=get_stock_bars" in text
    assert "secret-token" not in text


def test_provider_boundary_maps_unknown_sdk_error_without_leaking_message(caplog) -> None:
    logger = logging.getLogger("test.provider")
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ProviderResponseError):
            call_provider(
                lambda: (_ for _ in ()).throw(RuntimeError("api_key=top-secret")),
                logger=logger,
                provider="polygon",
                market="us",
                code="MSFT",
                operation_name="get_aggs",
            )
    assert "api_key=top-secret" not in caplog.text
    assert "error_type=RuntimeError" in caplog.text
