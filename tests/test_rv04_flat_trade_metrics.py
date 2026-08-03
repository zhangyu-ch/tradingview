from __future__ import annotations

import ast

from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.base import POSITION


def _position(profit: float, *, code: str = "TEST", balance: float = 100) -> POSITION:
    position = POSITION(code=code, signal="signal", balance=balance)
    position.profit = profit
    position.fee = 1
    return position


def test_closed_positions_split_win_loss_and_flat_with_epsilon():
    trader = BackTestTrader("test", mode="signal")
    for profit in (10, -5, 0, 0.5e-9, -0.5e-9):
        trader._record_closed_position(_position(profit), "signal")
    result = trader.results["signal"]
    assert result == {
        "win_num": 1,
        "loss_num": 1,
        "flat_num": 3,
        "win_balance": 10,
        "loss_balance": 5,
    }


def test_old_result_dictionary_is_upgraded_without_losing_counts():
    trader = BackTestTrader("test", mode="signal")
    trader.results["legacy"] = {
        "win_num": 2,
        "loss_num": 3,
        "win_balance": 20,
        "loss_balance": 15,
    }
    trader._record_closed_position(_position(0), "legacy")
    assert trader.results["legacy"]["win_num"] == 2
    assert trader.results["legacy"]["loss_num"] == 3
    assert trader.results["legacy"]["flat_num"] == 1


def test_trade_mode_flat_close_releases_principal_without_changing_profit():
    trader = BackTestTrader("test", mode="trade", init_balance=1000)
    before = trader.balance
    trader._record_closed_position(_position(0, balance=250), "signal")
    assert trader.balance == before + 250
    assert trader.results["signal"]["flat_num"] == 1
    assert trader.fee_total == 1


def test_result_report_includes_flat_but_win_rate_denominator_does_not():
    source = open("src/tradingview_zy/backtesting/backtest.py", encoding="utf-8").read()
    tree = ast.parse(source)
    constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    assert "持平" in constants
    result_source = source[source.index("    def result("):source.index("    @staticmethod\n    def print_result")]
    assert 'flat_num = result_stats.get("flat_num", 0)' in result_source
    assert "total_trade_num += win_num + loss_num + flat_num" in result_source
    assert "win_num / (win_num + loss_num)" in result_source
    assert "win_num + loss_num + flat_num" not in result_source[result_source.index("shenglv ="):result_source.index("win_balance =")]
