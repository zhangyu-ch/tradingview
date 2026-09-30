import ast
import datetime
import importlib
import inspect
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.backtesting.base import MarketDatas, Operation, POSITION, Strategy
from tradingview_zy.backtesting.backtest import BackTest
from tradingview_zy.backtesting.backtest_trader import BackTestTrader


def test_backtesting_base_import_does_not_load_hidden_config_or_fun():
    repo_root = Path(__file__).resolve().parents[1]
    script = "\n".join(
        [
            "import sys",
            "from pathlib import Path",
            "sys.path.insert(0, str(Path.cwd() / 'src'))",
            "import tradingview_zy.backtesting.base",
            "assert 'tradingview_zy.fun' not in sys.modules",
            "assert 'tradingview_zy.config' not in sys.modules",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def test_backtesting_base_source_does_not_import_fun():
    repo_root = Path(__file__).resolve().parents[1]
    source = (repo_root / "src" / "tradingview_zy" / "backtesting" / "base.py").read_text(
        encoding="utf-8"
    )

    assert "tradingview_zy.fun" not in source
    assert "get_logger" not in source


def test_strategy_close_signature_uses_signal_not_mmd():
    parameters = inspect.signature(Strategy.close).parameters

    assert "signal" in parameters
    assert "mmd" not in parameters


def test_backtesting_key_modules_import_smoke():
    for module_name in [
        "tradingview_zy.backtesting.base",
        "tradingview_zy.backtesting.backtest",
        "tradingview_zy.backtesting.backtest_klines",
    ]:
        assert importlib.import_module(module_name) is not None
    opt = Operation(code="SH.000001", opt="open", signal="breakout", msg="突破")
    assert opt.opt == "buy"
    assert opt.signal == "breakout"
    assert opt.open_uid == "SH.000001:breakout"


def test_position_accepts_generic_signal_name():
    pos = POSITION(code="SH.000001", signal="breakout")
    assert pos.signal == "breakout"
    assert pos.amount == 0


def test_market_datas_no_longer_exposes_get_cl_data():
    assert not hasattr(MarketDatas, "get_cl_data")


def test_runtime_operation_position_calls_use_generic_keywords():
    repo_root = Path(__file__).resolve().parents[1]
    search_roots = [
        repo_root / "src" / "tradingview_zy" / "backtesting",
        repo_root / "src" / "tradingview_zy" / "trader",
    ]
    bad_calls = []

    for root in search_roots:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Name) or node.func.id not in {
                    "Operation",
                    "POSITION",
                }:
                    continue
                bad_keywords = [
                    kw.arg for kw in node.keywords if kw.arg in {"mmd", "direction"}
                ]
                if bad_keywords:
                    bad_calls.append(
                        f"{path.relative_to(repo_root)}:{node.lineno} {node.func.id}({', '.join(bad_keywords)})"
                    )

    assert bad_calls == []


def test_backtest_trader_execute_uses_operation_opt_for_generic_signal():
    trader = BackTestTrader("test", mode="signal", market="us")
    trader.datas = type(
        "Datas",
        (),
        {
            "now_date": datetime.datetime(2024, 1, 2, 9, 30),
            "last_k_info": lambda self, code: {
                "date": datetime.datetime(2024, 1, 2, 9, 30),
                "open": 100,
                "close": 100,
                "high": 101,
                "low": 99,
            },
        },
    )()

    assert trader.execute("SH.000001", Operation(code="SH.000001", opt="buy", signal="breakout")) is True
    pos = trader.positions["SH.000001:breakout"]
    assert pos.type == "做多"

    assert trader.execute(
        "SH.000001",
        Operation(code="SH.000001", opt="sell", signal="breakout"),
        pos,
    ) is True
    assert "breakout" in trader.results


def test_backtest_result_accepts_unknown_signal_key():
    bt = BackTest()
    bt.mode = "signal"
    bt.init_balance = 100000
    bt.trader = BackTestTrader("test", mode="signal", market="us")
    bt.trader.results = {
        "breakout": {
            "win_num": 1,
            "loss_num": 0,
            "win_balance": 1200,
            "loss_balance": 0,
        }
    }

    result = bt.result(is_print=False)

    assert "breakout" in result["mmd_infos"].get_string()


def test_trade_result_annualizes_by_market_trading_days():
    import pandas as pd
    import pytest

    def annual_return(market):
        bt = BackTest()
        bt.mode = "trade"
        bt.market = market
        bt.base_code = "BASE"
        bt.frequencys = ["d"]
        bt.start_datetime = "2024-01-02 00:00:00"
        bt.end_datetime = "2024-01-04 23:59:59"
        bt.init_balance = 100000
        bt.datas = type(
            "Datas",
            (),
            {
                "ex": type(
                    "Ex",
                    (),
                    {"klines": lambda self, *a, **k: pd.DataFrame({"open": [1.0], "close": [1.0]})},
                )()
            },
        )()
        bt.trader = BackTestTrader("test", mode="trade", market="a")
        bt.trader.balance_history = {
            "2024-01-02 15:00:00": 100000,
            "2024-01-03 15:00:00": 90000,
            "2024-01-04 15:00:00": 110000,
        }
        return bt.result(is_print=False)["annual_return"]

    for market in ("a", "us", "hk", "futures"):
        assert annual_return(market) == pytest.approx(10 / 3 * 240)
    assert annual_return("currency") == pytest.approx(10 / 3 * 365)


def test_run_optimization_returns_results_sorted_by_end_balance(monkeypatch, tmp_path):
    class InlineExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def map(self, fn, items):
            return [fn(item) for item in items]

    # 其他测试会重新导入 backtest 模块，这里直接替换 BackTest 实际使用的全局名
    monkeypatch.setitem(
        BackTest.run_optimization.__globals__, "ProcessPoolExecutor", InlineExecutor
    )
    bt = BackTest()
    bt.run_params = lambda setting: {
        "end_balance": setting["x"],
        "params": setting,
        "save_file": str(tmp_path / f"missing_{setting['x']}.pkl"),
    }
    setting = type(
        "Setting", (), {"generate_settings": lambda self: [{"x": 1}, {"x": 3}, {"x": 2}]}
    )()

    results = bt.run_optimization(setting, max_workers=1)

    assert [r["end_balance"] for r in results] == [3, 2, 1]
