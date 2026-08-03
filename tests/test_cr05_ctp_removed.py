from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# The offline verification image lacks this otherwise-unrelated runtime dependency.
if "tzlocal" not in sys.modules:
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: "UTC"
    sys.modules["tzlocal"] = tzlocal

from tradingview_zy import config  # noqa: E402
from tradingview_zy.base import Market  # noqa: E402
from tradingview_zy.exchange import (  # noqa: E402
    UnsupportedProviderError,
    g_exchange_obj,
    get_exchange,
)


def test_ctp_runtime_implementation_and_dependency_are_removed() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_ctp.py").exists()
    assert not (ROOT / "src/tradingview_zy/trader/trader_ctp.py").exists()

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    lock = (ROOT / "uv.lock").read_text(encoding="utf-8").lower()
    assert "openctp-ctp" not in pyproject
    assert "openctp-ctp" not in lock

    config_template = (ROOT / "src/tradingview_zy/config.py.demo").read_text(
        encoding="utf-8"
    )
    assert "CTP_" not in config_template


def test_factory_rejects_removed_ctp_before_import_or_cache(monkeypatch) -> None:
    g_exchange_obj.clear()
    monkeypatch.setattr(config, "EXCHANGE_FUTURES", "ctp")
    sys.modules.pop("tradingview_zy.exchange.exchange_ctp", None)

    with pytest.raises(UnsupportedProviderError, match="已从运行包移除"):
        get_exchange(Market.FUTURES)

    assert Market.FUTURES.value not in g_exchange_obj
    assert "tradingview_zy.exchange.exchange_ctp" not in sys.modules


def test_runtime_tree_contains_no_openctp_imports() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "openctp_ctp" in text or "exchange_ctp" in text or "trader_ctp" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
