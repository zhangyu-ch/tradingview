import sys
from pathlib import Path

import pytest

from tradingview_zy import config
from tradingview_zy.base import Market
from tradingview_zy.exchange import (
    CTP_UNAVAILABLE_MESSAGE,
    g_exchange_obj,
    get_exchange,
)


def test_ctp_configuration_fails_closed_without_importing_unfinished_adapter(monkeypatch):
    monkeypatch.setattr(config, "EXCHANGE_FUTURES", "ctp")
    monkeypatch.delitem(g_exchange_obj, Market.FUTURES.value, raising=False)
    monkeypatch.delitem(
        sys.modules, "tradingview_zy.exchange.exchange_ctp", raising=False
    )

    with pytest.raises(RuntimeError, match="CTP 适配器当前不可用"):
        get_exchange(Market.FUTURES)

    assert "CR-05" in CTP_UNAVAILABLE_MESSAGE
    assert "tradingview_zy.exchange.exchange_ctp" not in sys.modules
    assert Market.FUTURES.value not in g_exchange_obj


def test_ctp_unavailable_notice_is_present_in_operator_docs():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    config_demo = (root / "src/tradingview_zy/config.py.demo").read_text(encoding="utf-8")

    assert "CTP 当前不可用" in readme
    assert "CTP 适配器当前不可用" in config_demo
