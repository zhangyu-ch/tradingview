import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.backtesting.base import MarketDatas, Operation, POSITION


def test_operation_uses_generic_signal_name():
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
