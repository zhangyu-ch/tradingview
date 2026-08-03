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


def test_zb_runtime_and_configuration_contract_are_removed() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_zb.py").exists()

    config_paths = [ROOT / "src/tradingview_zy/config.py.demo"]
    local_config = ROOT / "src/tradingview_zy/config.py"
    if local_config.exists():
        config_paths.append(local_config)

    for config_path in config_paths:
        text = config_path.read_text(encoding="utf-8").lower()
        assert " / zb" not in text
        assert "zb_apikey" not in text
        assert "zb_secret" not in text


def test_factory_rejects_legacy_zb_before_import_or_cache(monkeypatch) -> None:
    g_exchange_obj.clear()
    monkeypatch.setattr(config, "EXCHANGE_CURRENCY", "zb")
    sys.modules.pop("tradingview_zy.exchange.exchange_zb", None)

    with pytest.raises(UnsupportedProviderError, match="ZB provider 已从运行包移除"):
        get_exchange(Market.CURRENCY)

    assert Market.CURRENCY.value not in g_exchange_obj
    assert "tradingview_zy.exchange.exchange_zb" not in sys.modules


def test_runtime_tree_has_no_zb_adapter_references() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "exchange_zb" in text or "ccxt.zb" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_removed_provider_is_documented() -> None:
    text = (ROOT / "docs/unsupported-providers.md").read_text(encoding="utf-8")
    assert "## ZB cryptocurrency provider (`MX-02`)" in text
    assert "Supported built-in cryptocurrency-futures providers are `binance` and `db`" in text
