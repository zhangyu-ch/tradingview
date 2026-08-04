from __future__ import annotations

import ast
import copy
import datetime as dt
import json
import math
import textwrap
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies import (
    BatchRunResult,
    StrategyAction,
    StrategyPurpose,
    StrategySignal,
)
from tradingview_zy.strategies.base import (
    MAX_METADATA_BYTES,
    MAX_SIGNALS_PER_TARGET,
    SIGNAL_SCHEMA_VERSION,
    StrategyOutputError,
    StrategyRunTarget,
    validate_strategy_signals,
)

ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = ZoneInfo("Asia/Shanghai")
UTC = dt.timezone.utc
CONTEXT_NOW = dt.datetime(2026, 5, 4, 15, 0, tzinfo=SHANGHAI)
TARGET = StrategyRunTarget("a", "SH.600000", "浦发银行", "d")


def _signal(**overrides) -> StrategySignal:
    values = {
        "code": TARGET.code,
        "name": TARGET.name,
        "action": StrategyAction.SELECT,
        "score": 1.0,
        "message": "signal",
        "frequency": TARGET.frequency,
        "event_time": CONTEXT_NOW,
        "metadata": {},
        "schema_version": SIGNAL_SCHEMA_VERSION,
    }
    values.update(overrides)
    return StrategySignal(**values)


def _validate(
    result,
    *,
    purpose: StrategyPurpose = StrategyPurpose.SELECTION,
    now: dt.datetime = CONTEXT_NOW,
):
    return validate_strategy_signals(
        result,
        TARGET,
        purpose=purpose,
        context_now=now,
    )


def _frame(code: str = TARGET.code) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2026-05-04 09:30:00"),
                "code": code,
                "frequency": "d",
                "open": 10.0,
                "close": 11.0,
                "high": 11.5,
                "low": 9.5,
                "volume": 100,
            }
        ]
    )


class Exchange:
    def klines(self, code, frequency):
        return _frame(code)


class StaticStrategy:
    def __init__(self, value):
        self.value = value

    def run(self, context):
        if callable(self.value):
            return self.value(context)
        return self.value


def _load_static_batch_method(path: Path, class_name: str):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    method_source = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == "_batch_result":
                    method_source = ast.get_source_segment(source, child)
                    decorators = [ast.get_source_segment(source, item) for item in child.decorator_list]
                    if decorators:
                        method_source = "\n".join(f"@{item}" for item in decorators) + "\n" + method_source
                    break
    assert method_source is not None
    namespace = {"BatchRunResult": BatchRunResult}
    exec("class Holder:\n" + textwrap.indent(textwrap.dedent(method_source), "    "), namespace)
    return namespace["Holder"]._batch_result


def test_domain_enums_and_schema_are_stable() -> None:
    assert StrategyAction.SELECT.value == "select"
    assert StrategyAction.WATCH.value == "watch"
    assert StrategyPurpose.SELECTION.value == "selection"
    assert StrategyPurpose.MONITORING.value == "monitoring"
    assert SIGNAL_SCHEMA_VERSION == 1


def test_canonical_payload_is_json_round_trip_safe() -> None:
    signal = _validate(
        _signal(
            metadata={"source": "demo", "nested": [1, True, None]},
            action="select",
        )
    )[0]
    payload = signal.to_payload()
    assert json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False)) == payload
    assert payload["action"] == "select"
    assert payload["schema_version"] == 1
    assert payload["event_time"].endswith("+08:00")


@pytest.mark.parametrize(
    ("purpose", "action"),
    [
        (StrategyPurpose.SELECTION, StrategyAction.SELECT),
        (StrategyPurpose.MONITORING, StrategyAction.WATCH),
        (StrategyPurpose.MONITORING, StrategyAction.BUY),
        (StrategyPurpose.MONITORING, StrategyAction.SELL),
        (StrategyPurpose.MONITORING, StrategyAction.OPEN),
        (StrategyPurpose.MONITORING, StrategyAction.CLOSE),
    ],
)
def test_purpose_specific_actions_are_accepted(purpose, action) -> None:
    result = _validate(_signal(action=action), purpose=purpose)
    assert result[0].action is action


@pytest.mark.parametrize(
    ("purpose", "action"),
    [
        (StrategyPurpose.SELECTION, StrategyAction.WATCH),
        (StrategyPurpose.SELECTION, StrategyAction.BUY),
        (StrategyPurpose.MONITORING, StrategyAction.SELECT),
    ],
)
def test_cross_purpose_actions_fail_closed(purpose, action) -> None:
    with pytest.raises(StrategyOutputError, match="invalid for"):
        _validate(_signal(action=action), purpose=purpose)


def test_ignore_is_a_versioned_miss_not_a_persisted_hit() -> None:
    assert _validate(_signal(action=StrategyAction.IGNORE)) == []
    batch = SelectionRunner(Exchange(), StaticStrategy(_signal(action="ignore"))).run(
        "a", [{"code": TARGET.code, "name": TARGET.name}], "d", now=CONTEXT_NOW
    )
    assert batch.hits == []
    assert [item.code for item in batch.misses] == [TARGET.code]
    assert batch.failures == []


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"schema_version": True}, "schema_version"),
        ({"action": "execute_everything"}, "unsupported"),
        ({"code": "SH.600001"}, "code does not match"),
        ({"name": "其他名称"}, "name does not match"),
        ({"frequency": "60m"}, "frequency does not match"),
    ],
)
def test_schema_action_and_target_binding_are_strict(overrides, match) -> None:
    with pytest.raises(StrategyOutputError, match=match):
        _validate(_signal(**overrides))


@pytest.mark.parametrize("score", [True, "1", None])
def test_score_must_be_numeric_not_bool(score) -> None:
    with pytest.raises(TypeError, match="score must be numeric"):
        _validate(_signal(score=score))


@pytest.mark.parametrize("score", [math.nan, math.inf, -math.inf])
def test_score_must_be_finite(score) -> None:
    with pytest.raises(StrategyOutputError, match="finite"):
        _validate(_signal(score=score))


@pytest.mark.parametrize(
    "message",
    [None, "", "   ", "bad\nmessage", "x" * 2_001, "bad\ud800"],
)
def test_message_boundary_rejects_invalid_values(message) -> None:
    with pytest.raises((TypeError, ValueError, StrategyOutputError)):
        _validate(_signal(message=message))


def test_naive_event_time_is_bound_to_market_timezone() -> None:
    signal = _validate(_signal(event_time=dt.datetime(2026, 5, 4, 14, 59)))[0]
    assert signal.event_time.tzinfo == SHANGHAI
    assert signal.event_time.utcoffset() == dt.timedelta(hours=8)


def test_aware_event_time_is_converted_to_market_timezone() -> None:
    signal = _validate(
        _signal(event_time=dt.datetime(2026, 5, 4, 7, 0, tzinfo=UTC))
    )[0]
    assert signal.event_time == CONTEXT_NOW
    assert signal.event_time.tzinfo == SHANGHAI


def test_event_time_more_than_five_minutes_in_future_is_rejected() -> None:
    with pytest.raises(StrategyOutputError, match="future"):
        _validate(_signal(event_time=CONTEXT_NOW + dt.timedelta(minutes=6)))


def test_metadata_is_json_safe_preserved_and_deep_copied() -> None:
    metadata = {
        "empty": "",
        "spaced": "  keep me  ",
        "nested": {"values": [1, 2.5, True, None]},
    }
    signal = _validate(_signal(metadata=metadata))[0]
    assert signal.metadata == metadata
    assert signal.metadata is not metadata
    metadata["nested"]["values"].append("mutated")
    assert signal.metadata["nested"]["values"] == [1, 2.5, True, None]


@pytest.mark.parametrize(
    "metadata",
    [
        [],
        {"bad": b"bytes"},
        {"bad": (1, 2)},
        {"bad": {1, 2}},
        {"bad": object()},
        {"bad": math.nan},
        {"bad": math.inf},
        {1: "non-string key"},
        {"": "empty key"},
        {"   ": "whitespace key"},
        {"bad\nkey": "value"},
        {"bad": "value\u0000"},
        {"bad": "bad\ud800"},
    ],
)
def test_metadata_rejects_non_json_or_unsafe_values(metadata) -> None:
    with pytest.raises((TypeError, ValueError, StrategyOutputError)):
        _validate(_signal(metadata=metadata))


def test_metadata_depth_limit_is_enforced() -> None:
    value = 0
    for _ in range(7):
        value = {"level": value}
    with pytest.raises(StrategyOutputError, match="deeply nested"):
        _validate(_signal(metadata=value))


def test_metadata_node_limit_is_enforced() -> None:
    metadata = {"items": [[0] * 128, [0] * 128]}
    with pytest.raises(StrategyOutputError, match="too many nodes"):
        _validate(_signal(metadata=metadata))


def test_metadata_utf8_byte_limit_is_enforced() -> None:
    metadata = {f"k{i}": "界" * 1_900 for i in range(4)}
    assert len(json.dumps(metadata, ensure_ascii=False).encode("utf-8")) > MAX_METADATA_BYTES
    with pytest.raises(StrategyOutputError, match="UTF-8 byte limit"):
        _validate(_signal(metadata=metadata))


@pytest.mark.parametrize(
    "result",
    [
        (_signal(),),
        {"signal"},
        (item for item in [_signal()]),
        [SimpleNamespace(code=TARGET.code)],
    ],
)
def test_output_container_and_member_types_are_strict(result) -> None:
    with pytest.raises(TypeError):
        _validate(result)


def test_signal_count_limit_is_enforced_before_persistence() -> None:
    with pytest.raises(StrategyOutputError, match=str(MAX_SIGNALS_PER_TARGET)):
        _validate([_signal(message=f"s{i}") for i in range(MAX_SIGNALS_PER_TARGET + 1)])


def test_duplicate_signals_are_rejected() -> None:
    signal = _signal()
    with pytest.raises(StrategyOutputError, match="duplicate"):
        _validate([signal, copy.deepcopy(signal)])


def test_output_failure_is_structured_and_next_target_continues() -> None:
    class MultiExchange:
        def klines(self, code, frequency):
            return _frame(code)

    class Strategy:
        def run(self, context):
            action = "watch" if context.code == "GOOD" else "select"
            return StrategySignal(
                code=context.code,
                name=context.name,
                action=action,
                score=1,
                message="event",
                frequency=context.frequency,
                event_time=context.now,
            )

    batch = MonitoringRunner(MultiExchange(), Strategy()).run(
        "a",
        [{"code": "BAD", "name": "Bad"}, {"code": "GOOD", "name": "Good"}],
        "d",
        now=CONTEXT_NOW,
    )
    assert [item.code for item in batch.hits] == ["GOOD"]
    assert [(item.code, item.stage, item.error_type) for item in batch.failures] == [
        ("BAD", "output", "StrategyOutputError")
    ]


def test_context_now_is_market_aware_before_strategy_runs() -> None:
    seen = []

    def strategy(context):
        seen.append(context.now)
        return StrategySignal(
            code=context.code,
            name=context.name,
            action="select",
            score=1,
            message="ok",
            frequency=context.frequency,
            event_time=context.now,
        )

    batch = SelectionRunner(Exchange(), StaticStrategy(strategy)).run(
        "a",
        [{"code": TARGET.code, "name": TARGET.name}],
        "d",
        now=dt.datetime(2026, 5, 4, 15, 0),
    )
    assert batch.ok is True
    assert seen == [CONTEXT_NOW]
    assert batch.hits[0].event_time == CONTEXT_NOW


@pytest.mark.parametrize(
    ("relative_path", "class_name", "message"),
    [
        ("web/tradingview_zy_chart/cl_app/xuangu_tasks.py", "XuanguTasks", "selection"),
        ("web/tradingview_zy_chart/cl_app/alert_tasks.py", "AlertTasks", "monitoring"),
    ],
)
def test_task_boundaries_reject_legacy_raw_signal_lists(relative_path, class_name, message) -> None:
    method = _load_static_batch_method(ROOT / relative_path, class_name)
    with pytest.raises(TypeError, match=f"{message} runner must return BatchRunResult"):
        method([_signal()])
    batch = BatchRunResult(hits=[_signal()])
    assert method(batch) is batch
