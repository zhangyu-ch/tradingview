from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import math
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ALERT_TASKS_PATH = ROOT / "web/tradingview_zy_chart/cl_app/alert_tasks.py"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.base import (
    BatchRunResult,
    StrategyContext,
    StrategySignal,
)


def _frame(
    code: str,
    frequency: str = "d",
    *,
    close: float = 11.0,
    dates: list[str] | None = None,
) -> pd.DataFrame:
    dates = dates or ["2026-05-04 09:30:00", "2026-05-04 09:31:00"]
    rows = []
    for index, date in enumerate(dates):
        open_value = 10.0 + index
        close_value = close + index
        rows.append(
            {
                "date": pd.Timestamp(date),
                "code": code,
                "frequency": frequency,
                "open": open_value,
                "close": close_value,
                "high": max(open_value, close_value) + 0.5,
                "low": min(open_value, close_value) - 0.5,
                "volume": 100 + index,
            }
        )
    return pd.DataFrame(rows)


class PositiveStrategy:
    def __init__(self, action: str = "select"):
        self.action = action

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) <= float(last["open"]):
            return []
        return StrategySignal(
            code=context.code,
            name=context.name,
            action=self.action,
            score=1.0,
            message="positive",
            frequency=context.frequency,
            event_time=context.now,
        )


class MappingExchange:
    def __init__(self, values):
        self.values = values
        self.requested: list[tuple[str, str]] = []

    def klines(self, code, frequency):
        self.requested.append((code, frequency))
        value = self.values[code]
        if isinstance(value, BaseException):
            raise value
        return value


def test_selection_batch_separates_hit_miss_and_provider_failure() -> None:
    exchange = MappingExchange(
        {
            "HIT": _frame("HIT"),
            "MISS": _frame("MISS", close=9.0),
            "TIMEOUT": TimeoutError("provider deadline exceeded"),
        }
    )
    batch = SelectionRunner(exchange, PositiveStrategy()).run(
        "a",
        [
            {"code": "HIT", "name": "Hit"},
            {"code": "MISS", "name": "Miss"},
            {"code": "TIMEOUT", "name": "Timeout"},
        ],
        "d",
        now=dt.datetime(2026, 5, 4, 15, 0),
    )

    assert isinstance(batch, BatchRunResult)
    assert [signal.code for signal in batch.hits] == ["HIT"]
    assert [target.code for target in batch.misses] == ["MISS"]
    assert [(failure.code, failure.stage, failure.error_type) for failure in batch.failures] == [
        ("TIMEOUT", "provider", "TimeoutError")
    ]
    assert exchange.requested == [("HIT", "d"), ("MISS", "d"), ("TIMEOUT", "d")]
    assert batch.ok is False


def test_monitoring_batch_continues_after_input_failure() -> None:
    bad = _frame("BAD").drop(columns=["volume"])
    exchange = MappingExchange({"BAD": bad, "GOOD": _frame("GOOD")})
    batch = MonitoringRunner(exchange, PositiveStrategy("watch")).run(
        "a",
        [{"code": "BAD", "name": "Bad"}, {"code": "GOOD", "name": "Good"}],
        "d",
    )

    assert [signal.code for signal in batch.hits] == ["GOOD"]
    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("BAD", "input")
    ]
    assert exchange.requested == [("BAD", "d"), ("GOOD", "d")]


def test_malformed_target_isolated_before_provider_call() -> None:
    exchange = MappingExchange({"GOOD": _frame("GOOD")})
    batch = SelectionRunner(exchange, PositiveStrategy()).run(
        "a",
        [{"name": "missing code"}, {"code": "GOOD", "name": "Good"}],
        "d",
    )

    assert [signal.code for signal in batch.hits] == ["GOOD"]
    assert len(batch.failures) == 1
    assert batch.failures[0].stage == "target"
    assert batch.failures[0].code == "<invalid>"
    assert exchange.requested == [("GOOD", "d")]


def test_non_dataframe_empty_and_missing_column_fail_at_input_stage() -> None:
    exchange = MappingExchange(
        {
            "NOT_FRAME": [{"close": 1}],
            "EMPTY": pd.DataFrame(),
            "MISSING": _frame("MISSING").drop(columns=["low"]),
        }
    )
    batch = SelectionRunner(exchange, PositiveStrategy()).run(
        "a",
        [{"code": code, "name": code} for code in exchange.values],
        "d",
    )

    assert batch.hits == []
    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("NOT_FRAME", "input"),
        ("EMPTY", "input"),
        ("MISSING", "input"),
    ]


def test_duplicate_and_descending_timestamps_fail_closed() -> None:
    duplicate = _frame(
        "DUP",
        dates=["2026-05-04 09:30:00", "2026-05-04 09:30:00"],
    )
    descending = _frame(
        "DESC",
        dates=["2026-05-04 09:31:00", "2026-05-04 09:30:00"],
    )
    batch = SelectionRunner(
        MappingExchange({"DUP": duplicate, "DESC": descending}), PositiveStrategy()
    ).run(
        "a",
        [{"code": "DUP", "name": "D"}, {"code": "DESC", "name": "D"}],
        "d",
    )

    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("DUP", "input"),
        ("DESC", "input"),
    ]
    assert "unique" in batch.failures[0].message
    assert "ascending" in batch.failures[1].message


def test_nonfinite_negative_volume_and_inconsistent_ohlc_fail_closed() -> None:
    nonfinite = _frame("INF")
    nonfinite.loc[0, "close"] = math.inf
    negative = _frame("NEG")
    negative.loc[0, "volume"] = -1
    inconsistent = _frame("OHLC")
    inconsistent.loc[0, "high"] = 1
    batch = SelectionRunner(
        MappingExchange({"INF": nonfinite, "NEG": negative, "OHLC": inconsistent}),
        PositiveStrategy(),
    ).run(
        "a",
        [
            {"code": "INF", "name": "Inf"},
            {"code": "NEG", "name": "Negative"},
            {"code": "OHLC", "name": "OHLC"},
        ],
        "d",
    )

    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("INF", "input"),
        ("NEG", "input"),
        ("OHLC", "input"),
    ]


def test_optional_code_and_frequency_columns_must_match_target() -> None:
    wrong_code = _frame("TARGET")
    wrong_code["code"] = "OTHER"
    wrong_frequency = _frame("FREQ", frequency="60m")
    batch = SelectionRunner(
        MappingExchange({"TARGET": wrong_code, "FREQ": wrong_frequency}),
        PositiveStrategy(),
    ).run(
        "a",
        [{"code": "TARGET", "name": "Target"}, {"code": "FREQ", "name": "Freq"}],
        "d",
    )

    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("TARGET", "input"),
        ("FREQ", "input"),
    ]
    assert "code" in batch.failures[0].message
    assert "frequency" in batch.failures[1].message


def test_unknown_market_fails_at_target_stage_without_running_strategy() -> None:
    calls = []

    class Strategy:
        def run(self, context):
            calls.append(context)
            return []

    batch = SelectionRunner(MappingExchange({"X": _frame("X")}), Strategy()).run(
        "unknown", [{"code": "X", "name": "X"}], "d"
    )

    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("X", "target")
    ]
    assert calls == []


def test_strategy_exception_isolated_and_next_target_runs() -> None:
    class Strategy:
        def run(self, context):
            if context.code == "BAD":
                raise RuntimeError("strategy exploded")
            return PositiveStrategy().run(context)

    batch = SelectionRunner(
        MappingExchange({"BAD": _frame("BAD"), "GOOD": _frame("GOOD")}), Strategy()
    ).run(
        "a",
        [{"code": "BAD", "name": "Bad"}, {"code": "GOOD", "name": "Good"}],
        "d",
    )

    assert [signal.code for signal in batch.hits] == ["GOOD"]
    assert [(failure.code, failure.stage, failure.error_type) for failure in batch.failures] == [
        ("BAD", "strategy", "RuntimeError")
    ]


def test_invalid_strategy_output_is_reported_at_output_stage() -> None:
    class Strategy:
        def run(self, context):
            if context.code == "TYPE":
                return {"not": "a signal"}
            return StrategySignal(
                code="OTHER",
                name=context.name,
                action="watch",
                score=1.0,
                message="wrong code",
                frequency=context.frequency,
                event_time=context.now,
            )

    batch = SelectionRunner(
        MappingExchange({"TYPE": _frame("TYPE"), "MISMATCH": _frame("MISMATCH")}),
        Strategy(),
    ).run(
        "a",
        [
            {"code": "TYPE", "name": "Type"},
            {"code": "MISMATCH", "name": "Mismatch"},
        ],
        "d",
    )

    assert [(failure.code, failure.stage) for failure in batch.failures] == [
        ("TYPE", "output"),
        ("MISMATCH", "output"),
    ]


def test_valid_naive_market_time_is_localized_without_mutating_provider_frame() -> None:
    source = _frame("A")
    original = source.copy(deep=True)
    seen = []

    class Strategy:
        def run(self, context):
            seen.append(context.klines)
            return []

    batch = SelectionRunner(MappingExchange({"A": source}), Strategy()).run(
        "a", [{"code": "A", "name": "A"}], "d"
    )

    assert batch.ok is True
    assert [target.code for target in batch.misses] == ["A"]
    assert str(seen[0]["date"].dt.tz) == "Asia/Shanghai"
    pd.testing.assert_frame_equal(source, original)
    assert source["date"].dt.tz is None


def test_monitoring_run_code_returns_structured_result_with_signal_list_compatibility() -> None:
    batch = MonitoringRunner(
        MappingExchange({"A": _frame("A")}), PositiveStrategy("watch")
    ).run_code("a", "A", "A", "d")

    assert isinstance(batch, BatchRunResult)
    assert len(batch) == 1
    assert batch[0] is batch.hits[0]
    assert list(batch) == batch.hits


def test_alert_task_persists_good_hits_and_reports_partial_batch_failure(monkeypatch) -> None:
    logger_messages: list[str] = []
    saved: list[dict] = []

    class Logger:
        def info(self, message):
            logger_messages.append(str(message))

        def error(self, message):
            logger_messages.append(str(message))

    class Db:
        def alert_event_save(self, **kwargs):
            saved.append(kwargs)
            return True

    exchange_instance = MappingExchange(
        {"BAD": _frame("BAD").drop(columns=["volume"]), "GOOD": _frame("GOOD")}
    )
    exchange_instance.now_trading = lambda code=None, at=None: True

    config_module = types.ModuleType("tradingview_zy.config")
    config_module.ALERT_STRATEGIES = {"demo": {"strategy_path": "trusted:Demo"}}
    fun_module = types.ModuleType("tradingview_zy.fun")
    fun_module.get_logger = lambda: Logger()
    db_module = types.ModuleType("tradingview_zy.db")
    db_module.TableByAlertTask = object
    db_module.db = Db()
    exchange_module = types.ModuleType("tradingview_zy.exchange")
    exchange_module.Market = lambda value: value
    exchange_module.get_exchange = lambda market: exchange_instance
    loader_module = types.ModuleType("tradingview_zy.strategies.loader")
    loader_module.StrategyRegistryError = ValueError
    loader_module.find_registered_strategy_id_by_path = lambda registry, path: "demo"
    loader_module.load_registered_strategy = lambda registry, strategy_id, kwargs: PositiveStrategy("watch")
    zixuan_module = types.ModuleType("tradingview_zy.zixuan")
    zixuan_module.ZiXuan = lambda market: SimpleNamespace(
        zx_stocks=lambda group: [
            {"code": "BAD", "name": "Bad"},
            {"code": "GOOD", "name": "Good"},
        ]
    )

    package = importlib.import_module("tradingview_zy")
    monkeypatch.setattr(package, "config", config_module, raising=False)
    monkeypatch.setattr(package, "fun", fun_module, raising=False)
    for name, module in {
        "tradingview_zy.config": config_module,
        "tradingview_zy.fun": fun_module,
        "tradingview_zy.db": db_module,
        "tradingview_zy.exchange": exchange_module,
        "tradingview_zy.strategies.loader": loader_module,
        "tradingview_zy.zixuan": zixuan_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "test_me18_alert_tasks"
    spec = importlib.util.spec_from_file_location(module_name, ALERT_TASKS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)

    alert_config = SimpleNamespace(
        market="a",
        task_name="task",
        zx_group="source",
        frequency="d",
        strategy_config='{"strategy_id":"demo","strategy_kwargs":{}}',
    )
    monkeypatch.setattr(module.AlertTasks, "alert_get", lambda self, alert_id: alert_config)

    tasks = module.AlertTasks(None)
    assert tasks.alert_run("1") is False
    assert [item["stock_code"] for item in saved] == ["GOOD"]
    assert saved[0]["event_type"].value == "strategy_signal"
    assert saved[0]["action"].value == "watch"
    assert saved[0]["score"] == 1.0
    assert isinstance(saved[0]["score"], float)
    assert tasks.last_batch_result is not None
    assert [(failure.code, failure.stage) for failure in tasks.last_batch_result.failures] == [
        ("BAD", "input")
    ]
    assert any("code=BAD" in message and "stage=input" in message for message in logger_messages)
