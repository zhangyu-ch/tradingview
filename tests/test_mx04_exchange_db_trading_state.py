from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCHANGE_DB = ROOT / "src/tradingview_zy/exchange/exchange_db.py"


def _now_trading_node() -> ast.FunctionDef:
    tree = ast.parse(EXCHANGE_DB.read_text(encoding="utf-8"))
    exchange_db = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ExchangeDB"
    )
    return next(
        node
        for node in exchange_db.body
        if isinstance(node, ast.FunctionDef) and node.name == "now_trading"
    )


def test_exchange_db_now_trading_is_a_strict_bool_contract() -> None:
    node = _now_trading_node()
    assert node.returns is not None
    assert ast.unparse(node.returns) == "bool"
    returns = [child for child in ast.walk(node) if isinstance(child, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Constant)
    assert returns[0].value.value is False

    isolated = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(isolated)
    namespace: dict[str, object] = {}
    exec(compile(isolated, str(EXCHANGE_DB), "exec"), namespace)
    result = namespace["now_trading"](object())
    assert result is False
    assert type(result) is bool


def test_exchange_db_no_longer_exposes_none_or_pass() -> None:
    node = _now_trading_node()
    assert not any(isinstance(child, ast.Pass) for child in ast.walk(node))
    assert not any(
        isinstance(child, ast.Return)
        and (
            child.value is None
            or (isinstance(child.value, ast.Constant) and child.value.value is None)
        )
        for child in ast.walk(node)
    )


def test_callers_share_the_same_false_semantics() -> None:
    alert_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/alert_tasks.py"
    ).read_text(encoding="utf-8")
    web_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
    ).read_text(encoding="utf-8")
    frontend_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/static/js/zixuan.js"
    ).read_text(encoding="utf-8")

    assert "ex.now_trading() is False" in alert_source
    assert "ex.now_trading() is False" in web_source
    assert "now_trading !== true" in frontend_source
