import ast
import importlib
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.backtesting.base import MarketDatas, Operation, POSITION, Strategy




def test_backtesting_base_import_does_not_load_hidden_config_or_fun():
    sys.modules.pop("tradingview_zy.backtesting.base", None)
    sys.modules.pop("tradingview_zy.fun", None)
    sys.modules.pop("tradingview_zy.config", None)

    module = importlib.import_module("tradingview_zy.backtesting.base")

    assert module is not None
    assert "tradingview_zy.fun" not in sys.modules
    assert "tradingview_zy.config" not in sys.modules


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


def test_position_accepts_type_keyword_for_direction_semantics():
    pos = POSITION(code="rb2210", signal="risk", type="long")
    assert pos.type == "long"
    assert pos.mmd == "risk"
