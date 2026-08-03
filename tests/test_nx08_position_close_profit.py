from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradingview_zy.backtesting.base import POSITION


def _position() -> POSITION:
    position = POSITION("SH.000001", "breakout")
    position.close_uid_profit = {
        "partial": {
            "close_datetime": dt.datetime(2024, 1, 2, 9, 30),
            "profit": 10.0,
            "profit_rate": 0.01,
            "max_profit_rate": 0.02,
            "max_loss_rate": -0.005,
            "close_msg": "partial close",
        },
        "clear": {
            "close_datetime": dt.datetime(2024, 1, 3, 9, 30),
            "profit": 20.0,
            "profit_rate": 0.02,
            "max_profit_rate": 0.03,
            "max_loss_rate": -0.01,
            "close_msg": "clear",
        },
    }
    return position


def test_get_close_profit_does_not_mutate_caller_list() -> None:
    position = _position()
    requested = ["partial"]
    before = requested.copy()

    result = position.get_close_profit(requested)

    assert result["profit"] == 10.0
    assert requested == before


def test_clear_fallback_is_local_and_does_not_leak_to_reused_list() -> None:
    position = _position()
    requested = ["missing"]

    first = position.get_close_profit(requested)
    second = position.get_close_profit(requested)

    assert first["profit"] == second["profit"] == 20.0
    assert requested == ["missing"]


def test_missing_requested_and_clear_records_raise_without_mutation() -> None:
    position = _position()
    del position.close_uid_profit["clear"]
    requested = ["missing"]

    with pytest.raises(Exception, match=r"missing.*clear|clear.*missing"):
        position.get_close_profit(requested)

    assert requested == ["missing"]
