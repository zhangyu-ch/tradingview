from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from test_support.web_routes import route_node, route_source

from tradingview_zy.web_payloads import KlinePayloadError, prepare_klines_for_market

ROOT = Path(__file__).resolve().parents[1]


def frame(**overrides):
    data = {
        "date": ["2026-05-04 09:30:00", "2026-05-04 09:31:00"],
        "open": [10.0, 11.0],
        "close": [11.0, 10.5],
        "high": [12.0, 12.0],
        "low": [9.0, 10.0],
        "volume": [100, 200],
    }
    data.update(overrides)
    return pd.DataFrame(data)


def test_prepares_market_timezone_and_binds_request_identity():
    source = frame()
    result = prepare_klines_for_market(
        source, "a", expected_code="SH.600000", expected_frequency="1m"
    )
    assert str(result.iloc[0]["date"].tzinfo) == "Asia/Shanghai"
    assert result["code"].tolist() == ["SH.600000", "SH.600000"]
    assert result["frequency"].tolist() == ["1m", "1m"]
    assert "code" not in source.columns


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda value: value.drop(columns=["volume"]), "missing"),
        (lambda value: value.assign(volume=[-1, 2]), "negative"),
        (lambda value: value.assign(open=[float("nan"), 1]), "finite"),
        (lambda value: value.assign(high=[8, 12]), "OHLC"),
        (lambda value: value.iloc[[1, 0]], "increasing"),
        (lambda value: pd.concat([value.iloc[[0]], value.iloc[[0]]]), "unique"),
    ],
)
def test_rejects_malformed_provider_frames(mutator, match):
    with pytest.raises(KlinePayloadError, match=match):
        prepare_klines_for_market(mutator(frame()), "a")


def test_rejects_provider_identity_mismatch():
    with pytest.raises(KlinePayloadError, match="requested code"):
        prepare_klines_for_market(
            frame(code=["OTHER", "OTHER"]), "a", expected_code="SH.600000"
        )


def test_history_route_prepares_before_epoch_and_returns_stable_payload_error():
    route = route_node("tv_history")
    calls = [
        node.func.id
        for node in ast.walk(route)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert calls.index("prepare_klines_for_market") < calls.index(
        "datetime_to_timestamp_seconds"
    )
    source = route_source("tv_history")
    assert "invalid_kline_payload" in source
    assert "expected_code=code" in source
    assert "expected_frequency=frequency" in source
