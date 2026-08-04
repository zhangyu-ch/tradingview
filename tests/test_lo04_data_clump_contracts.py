from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pandas as pd
import pytest

from tradingview_zy.alert_strategy_storage import (
    StrategyStorageValidationError,
    build_strategy_config,
    normalize_strategy_config,
    parse_strategy_parameters,
)
from tradingview_zy.base import Market
from tradingview_zy.data_contracts import (
    DataContractError,
    Fill,
    KlineBar,
    OrderRequest,
    OrderState,
    ProviderBarPayload,
    StrategyParameters,
)
from tradingview_zy.domain import OrderOffset, OrderSide, OrderStatus
from tradingview_zy.strategies.base import StrategyAction, StrategySignal
from tradingview_zy.strategy_bridge import (
    BRIDGE_INFO_KEY,
    signal_to_trade_decision,
    trade_decision_to_order_request,
)

ROOT = Path(__file__).resolve().parents[1]
_US_HISTORY_SPEC = importlib.util.spec_from_file_location(
    "lo04_us_history",
    ROOT / "src/tradingview_zy/exchange/us_history.py",
)
assert _US_HISTORY_SPEC is not None and _US_HISTORY_SPEC.loader is not None
_US_HISTORY = importlib.util.module_from_spec(_US_HISTORY_SPEC)
sys.modules[_US_HISTORY_SPEC.name] = _US_HISTORY
_US_HISTORY_SPEC.loader.exec_module(_US_HISTORY)
build_us_history_frame = _US_HISTORY.build_us_history_frame
ALERT_TASKS = ROOT / "web/tradingview_zy_chart/cl_app/alert_tasks.py"
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"


def test_provider_bar_payload_replaces_repeated_ohlcv_dicts_and_is_immutable() -> None:
    payload = ProviderBarPayload(
        timestamp="2026-08-03T13:30:00Z",
        open=10,
        close=11,
        high=12,
        low=9,
        volume=100,
    )
    assert payload.to_mapping()["close"] == 11.0
    with pytest.raises(FrozenInstanceError):
        payload.close = 99  # type: ignore[misc]
    with pytest.raises(DataContractError, match="high"):
        ProviderBarPayload(
            timestamp="2026-08-03T13:30:00Z",
            open=10,
            close=11,
            high=10,
            low=9,
            volume=100,
        )
    with pytest.raises(DataContractError, match="volume"):
        ProviderBarPayload(
            timestamp="2026-08-03T13:30:00Z",
            open=10,
            close=10,
            high=10,
            low=10,
            volume=-1,
        )


def test_us_history_materializes_canonical_kline_bars_from_payload_objects() -> None:
    first = ProviderBarPayload(
        timestamp="2026-08-03T13:30:00Z", open=10, close=11, high=12, low=9, volume=100
    )
    replacement = ProviderBarPayload(
        timestamp="2026-08-03T13:30:00Z", open=11, close=12, high=13, low=10, volume=110
    )
    second = ProviderBarPayload(
        timestamp="2026-08-03T13:31:00Z", open=12, close=13, high=14, low=11, volume=120
    )
    frame = build_us_history_frame(
        [second, first, replacement], code="aapl", frequency="1m"
    )
    assert frame.columns.tolist() == ["code", "date", "open", "close", "high", "low", "volume"]
    assert frame["code"].tolist() == ["AAPL", "AAPL"]
    assert frame["open"].tolist() == [11.0, 12.0]
    assert str(frame.iloc[0]["date"].tzinfo) == "America/New_York"

    bar = KlineBar(**frame.iloc[0].to_dict())
    assert bar.to_mapping()["code"] == "AAPL"


def test_us_providers_build_typed_payloads_instead_of_duplicate_dict_groups() -> None:
    for filename in ("exchange_alpaca.py", "exchange_polygon.py"):
        source = (ROOT / "src/tradingview_zy/exchange" / filename).read_text(
            encoding="utf-8"
        )
        assert "ProviderBarPayload(" in source
        assert '"timestamp":' not in source
        assert '"open": bar.open' not in source
        assert '"open": aggregate.open' not in source


def test_strategy_parameters_are_versioned_canonical_and_defensively_copied() -> None:
    params = StrategyParameters.create(
        strategy_id="demo", kwargs={"window": 20, "nested": {"enabled": True}}
    )
    payload = params.to_mapping()
    assert payload == {
        "schema_version": 1,
        "strategy_id": "demo",
        "strategy_kwargs": {"nested": {"enabled": True}, "window": 20},
    }
    payload["strategy_kwargs"]["nested"]["enabled"] = False
    assert params.kwargs["nested"]["enabled"] is True
    assert StrategyParameters.from_json(params.to_json()) == params
    with pytest.raises(DataContractError, match="unknown fields"):
        StrategyParameters.from_mapping({"strategy_id": "demo", "kwargs": {}})
    with pytest.raises(DataContractError, match="mutually exclusive"):
        StrategyParameters.create(
            strategy_id="demo", strategy_path="pkg:Demo", kwargs={}
        )


def test_strategy_storage_and_runtime_share_one_strategy_parameter_contract() -> None:
    encoded = build_strategy_config("demo", {"window": 20})
    parsed = parse_strategy_parameters(encoded)
    assert parsed.strategy_id == "demo"
    assert parsed.kwargs == {"window": 20}
    assert json.loads(encoded)["schema_version"] == 1
    assert normalize_strategy_config(parsed.to_mapping()) == encoded
    assert parse_strategy_parameters(
        '{"strategy_path":"legacy.pkg:Strategy","strategy_kwargs":{}}'
    ).strategy_path == "legacy.pkg:Strategy"
    for invalid in (
        '{"strategy_id":"demo","extra":1}',
        '{"strategy_id":"demo","strategy_path":"pkg:Demo"}',
        "[]",
    ):
        with pytest.raises(StrategyStorageValidationError):
            parse_strategy_parameters(invalid)


def test_alert_runtime_and_web_edit_parse_strategy_parameters_once() -> None:
    task_source = ALERT_TASKS.read_text(encoding="utf-8")
    assert "parse_strategy_parameters(" in task_source
    assert "parameters.kwargs" in task_source
    assert "json.loads(alert_config.strategy_config" not in task_source
    web_source = WEB_APP.read_text(encoding="utf-8")
    assert "parameters = parse_strategy_parameters(" in web_source
    assert "parameters.kwargs" in web_source
    assert "strategy_config.get(\"strategy_kwargs\"" not in web_source


def test_order_request_has_stable_typed_payload_without_enabling_live_orders() -> None:
    request = OrderRequest.create(
        market="a",
        code="SH.600000",
        side="buy",
        offset="open",
        quantity=100,
        price=10.5,
        client_order_id="strategy-run-1",
        metadata={"trace_id": "trace-1"},
    )
    assert request.market is Market.A
    assert request.side is OrderSide.BUY
    assert request.offset is OrderOffset.OPEN
    assert request.to_payload()["metadata"] == {"trace_id": "trace-1"}
    with pytest.raises(FrozenInstanceError):
        request.quantity = 1  # type: ignore[misc]
    for values in (
        {"market": "unknown", "quantity": 1},
        {"market": "a", "quantity": 0},
        {"market": "a", "quantity": 1, "side": "hold"},
    ):
        candidate = {
            "market": values.get("market", "a"),
            "code": "SH.600000",
            "side": values.get("side", "buy"),
            "offset": "open",
            "quantity": values.get("quantity", 1),
        }
        with pytest.raises((DataContractError, TypeError, ValueError)):
            OrderRequest.create(**candidate)


def test_fill_and_order_state_form_an_immutable_validated_group() -> None:
    now = dt.datetime(2026, 8, 4, 14, 0, tzinfo=dt.timezone.utc)
    request = OrderRequest.create(
        market="us", code="AAPL", side="buy", offset="open", quantity=10
    )
    state = OrderState(
        request=request,
        order_id="broker-1",
        status=OrderStatus.SUBMITTED,
        filled_quantity=0,
        average_price=None,
        updated_at=now,
    )
    partial = state.apply_fill(
        Fill(
            order_id="broker-1",
            fill_id="fill-1",
            code="AAPL",
            side=OrderSide.BUY,
            quantity=4,
            price=100,
            fee=1,
            event_time=now + dt.timedelta(seconds=1),
        )
    )
    assert partial.status is OrderStatus.PARTIALLY_FILLED
    assert partial.filled_quantity == 4
    completed = partial.apply_fill(
        Fill(
            order_id="broker-1",
            fill_id="fill-2",
            code="AAPL",
            side=OrderSide.BUY,
            quantity=6,
            price=110,
            fee=1,
            event_time=now + dt.timedelta(seconds=2),
        )
    )
    assert completed.status is OrderStatus.FILLED
    assert completed.average_price == pytest.approx(106.0)
    with pytest.raises(DataContractError, match="belong"):
        state.apply_fill(
            Fill(
                order_id="other",
                fill_id="fill-x",
                code="AAPL",
                side=OrderSide.BUY,
                quantity=1,
                price=100,
                fee=0,
                event_time=now,
            )
        )


def test_trade_decision_requires_explicit_quantity_to_create_order_request() -> None:
    now = dt.datetime(2026, 8, 4, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=8)))
    signal = StrategySignal(
        code="SH.600000",
        name="浦发银行",
        action=StrategyAction.OPEN,
        score=0.9,
        message="breakout",
        frequency="30m",
        event_time=now,
        metadata={
            "trade": {
                "position_rate": 0.25,
                "loss_price": 9.5,
                "signal": "breakout",
                "key": "key-1",
                "open_uid": "open-1",
                "close_uid": "close-1",
            }
        },
    )
    decision = signal_to_trade_decision(signal, market="a", context_now=now)
    request = trade_decision_to_order_request(
        decision,
        market="a",
        quantity=100,
        price=10,
        client_order_id="order-1",
    )
    assert request.side is OrderSide.BUY
    assert request.offset is OrderOffset.OPEN
    assert request.metadata[BRIDGE_INFO_KEY]["code"] == "SH.600000"
    with pytest.raises(DataContractError, match="quantity"):
        trade_decision_to_order_request(decision, market="a", quantity=0)
