from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from tradingview_zy.base import Market
from tradingview_zy.domain import (
    Capability,
    ProviderResponseError,
    UnsupportedCapabilityError,
)
from tradingview_zy.exchange.contracted import ContractedExchange
from tradingview_zy.exchange.exchange import Exchange
from tradingview_zy.market_registry import MARKET_REGISTRY, ProviderSpec

ROOT = Path(__file__).resolve().parents[1]
EXCHANGE_ROOT = ROOT / "src" / "tradingview_zy" / "exchange"

OPTIONAL_CAPABILITY_METHODS = {
    "all_stocks": Capability.CATALOG,
    "now_trading": Capability.SESSION_STATUS,
    "ticks": Capability.TICKS,
    "stock_info": Capability.CATALOG,
    "stock_owner_plate": Capability.PLATES,
    "plate_stocks": Capability.PLATES,
    "balance": Capability.ACCOUNT_BALANCE,
    "positions": Capability.POSITIONS,
}


class _MinimalExchange(Exchange):
    def default_code(self) -> str:
        return "X"

    def support_frequencys(self) -> dict[str, str]:
        return {"d": "Day"}

    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str | None = None,
        end_date: str | None = None,
        args=None,
    ) -> pd.DataFrame:
        return pd.DataFrame()


def _call_optional(provider: _MinimalExchange, method: str) -> object:
    if method in {"all_stocks", "balance"}:
        return getattr(provider, method)()
    if method == "now_trading":
        return provider.now_trading(code="X")
    if method == "ticks":
        return provider.ticks(["X"])
    if method in {"stock_info", "stock_owner_plate", "plate_stocks"}:
        return getattr(provider, method)("X")
    if method == "positions":
        return provider.positions("X")
    raise AssertionError(method)


@pytest.mark.parametrize("method,capability", OPTIONAL_CAPABILITY_METHODS.items())
def test_optional_exchange_capabilities_share_one_stable_unsupported_error(
    method: str, capability: Capability
) -> None:
    provider = _MinimalExchange()

    with pytest.raises(UnsupportedCapabilityError) as exc_info:
        _call_optional(provider, method)

    payload = exc_info.value.to_dict()
    assert payload == {
        "code": "unsupported_capability",
        "message": f"_MinimalExchange 不支持能力 {capability.value}",
        "retryable": False,
        "provider": "_MinimalExchange",
    }


@pytest.mark.parametrize("capability", [Capability.TICKS, Capability.CATALOG])
def test_capability_facade_rejects_registry_overreport_when_provider_only_inherits_fallback(
    capability: Capability,
) -> None:
    provider = _MinimalExchange()
    spec = ProviderSpec(
        module="tests.fake",
        attribute="MinimalExchange",
        capabilities=frozenset(
            {Capability.METADATA, Capability.MARKET_DATA, capability}
        ),
    )

    with pytest.raises(ProviderResponseError) as exc_info:
        ContractedExchange(Market.A, "fake", provider, spec)

    assert exc_info.value.to_dict() == {
        "code": "provider_response_invalid",
        "message": "数据源实现与能力声明不一致",
        "retryable": False,
        "provider": "fake",
    }


def _without_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def _is_speculative_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = _without_docstring(node.body)
    if len(body) != 1:
        return False
    statement = body[0]
    if isinstance(statement, ast.Pass):
        return True
    if isinstance(statement, ast.Raise):
        error = statement.exc
        return (
            isinstance(error, ast.Call)
            and isinstance(error.func, ast.Name)
            and error.func.id
            in {"Exception", "RuntimeError", "RuntimeWarning", "NotImplementedError"}
        )
    if isinstance(statement, ast.Return):
        value = statement.value
        if value is None:
            return True
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return not value.elts
        if isinstance(value, ast.Dict):
            return not value.keys
        if isinstance(value, ast.Constant):
            return value.value is None
    return False


def test_runtime_exchange_adapters_do_not_redeclare_optional_capability_stubs() -> None:
    offenders: list[str] = []
    for path in sorted(EXCHANGE_ROOT.glob("exchange_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not node.name.startswith("Exchange"):
                continue
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name in OPTIONAL_CAPABILITY_METHODS
                    and _is_speculative_stub(member)
                ):
                    offenders.append(f"{path.relative_to(ROOT)}:{member.lineno}:{member.name}")
    assert offenders == []


def test_deleted_tombstones_and_dead_compatibility_shells_do_not_return() -> None:
    for relative in (
        "src/tradingview_zy/monitor.py",
        "src/tradingview_zy/others/cache_a_cal_cds.py",
        "src/tradingview_zy/tools/ai_analyse.py",
    ):
        assert not (ROOT / relative).exists(), relative

    file_db = ast.parse(
        (ROOT / "src/tradingview_zy/file_db.py").read_text(encoding="utf-8")
    )
    file_db_methods = {
        node.name
        for node in ast.walk(file_db)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {
        "get_web_cl_data",
        "clear_web_cl_data",
        "clear_old_web_cl_data",
        "clear_all_cl_data",
        "get_low_to_high_cl_data",
    }.isdisjoint(file_db_methods)

    backtest = ast.parse(
        (ROOT / "src/tradingview_zy/backtesting/backtest.py").read_text(
            encoding="utf-8"
        )
    )
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "show_charts"
        for node in ast.walk(backtest)
    )


def test_intentional_optional_backtest_hooks_are_explicit_noops_not_pass_stubs() -> None:
    path = ROOT / "src/tradingview_zy/backtesting/base.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    methods = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"on_bt_loop_start", "clear"}
    }
    assert set(methods) == {"on_bt_loop_start", "clear"}
    for name, node in methods.items():
        body = _without_docstring(node.body)
        assert len(body) == 1, name
        assert isinstance(body[0], ast.Return), name
        assert isinstance(body[0].value, ast.Constant), name
        assert body[0].value.value is None, name


def test_ib_registry_does_not_claim_catalogue_or_security_master() -> None:
    ib = MARKET_REGISTRY[Market.US].providers["ib"]
    assert Capability.CATALOG not in ib.capabilities
    assert Capability.SECURITY_MASTER not in ib.capabilities
    assert Capability.TICKS in ib.capabilities
    assert Capability.ACCOUNT_BALANCE in ib.capabilities
    assert Capability.POSITIONS in ib.capabilities
