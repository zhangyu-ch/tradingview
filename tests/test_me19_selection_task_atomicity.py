from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
import types
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradingview_zy.strategies.base import (
    BatchRunResult,
    StrategyRunFailure,
    StrategyRunTarget,
)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
XUANGU_TASKS_PATH = ROOT / "web/tradingview_zy_chart/cl_app/xuangu_tasks.py"


def _load_db(tmp_path):
    for name in ["tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config"]:
        sys.modules.pop(name, None)
    tzlocal = types.ModuleType("tzlocal")
    tzlocal.get_localzone = lambda: timezone.utc
    sys.modules["tzlocal"] = tzlocal

    config = types.ModuleType("tradingview_zy.config")
    config.DB_TYPE = "sqlite"
    config.DB_DATABASE = "me19"
    config.DB_HOST = "127.0.0.1"
    config.DB_PORT = 3306
    config.DB_USER = "user"
    config.DB_PWD = "password"
    config.get_data_path = lambda: tmp_path
    sys.modules["tradingview_zy.config"] = config
    package = importlib.import_module("tradingview_zy")
    package.config = config
    return importlib.import_module("tradingview_zy.db")


def _rows(module, market: str, group: str = "target"):
    with module.db.Session() as session:
        return [
            (
                row.stock_code,
                row.stock_name,
                row.stock_memo,
                row.stock_color,
                row.position,
            )
            for row in session.query(module.TableByZixuan)
            .filter(module.TableByZixuan.market == market)
            .filter(module.TableByZixuan.zx_group == group)
            .order_by(module.TableByZixuan.position, module.TableByZixuan.id)
            .all()
        ]


def _load_xuangu_module(monkeypatch):
    config = types.ModuleType("tradingview_zy.config")
    config.XUANGU_STRATEGIES = {"task1": {"name": "Task 1"}}
    exchange = types.ModuleType("tradingview_zy.exchange")
    exchange.Market = lambda value: value
    exchange.get_exchange = lambda market: object()
    selection = types.ModuleType("tradingview_zy.selection")
    selection.SelectionRunner = object
    loader = types.ModuleType("tradingview_zy.strategies.loader")
    loader.load_registered_strategy = lambda registry, task_name: object()
    zixuan = types.ModuleType("tradingview_zy.zixuan")
    zixuan.ZiXuan = object

    package = importlib.import_module("tradingview_zy")
    monkeypatch.setattr(package, "config", config, raising=False)
    for name, module in {
        "tradingview_zy.config": config,
        "tradingview_zy.exchange": exchange,
        "tradingview_zy.selection": selection,
        "tradingview_zy.strategies.loader": loader,
        "tradingview_zy.zixuan": zixuan,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "test_me19_xuangu_tasks"
    spec = importlib.util.spec_from_file_location(module_name, XUANGU_TASKS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _event(code: str, *, name: str | None = None, message: str = "hit"):
    return SimpleNamespace(code=code, name=name or code, message=message)


def test_atomic_replace_rolls_back_delete_and_partial_inserts(tmp_path) -> None:
    module = _load_db(tmp_path)
    module.db.zx_add_group_stock("a", "target", "OLD1", "Old 1")
    module.db.zx_add_group_stock("a", "target", "OLD2", "Old 2")
    module.db.zx_add_group_stock("hk", "target", "HK1", "HK 1")
    before_a = _rows(module, "a")
    before_hk = _rows(module, "hk")
    with module.db.engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TRIGGER fail_second_snapshot_row
            BEFORE INSERT ON cl_zixuan_watchlist
            WHEN NEW.stock_code = 'FAIL'
            BEGIN
              SELECT RAISE(ABORT, 'injected insert failure');
            END;
            """
        )

    with pytest.raises(Exception):
        module.db.zx_replace_group_stocks(
            "a",
            "target",
            [
                {"code": "NEW1", "name": "New 1", "memo": "first"},
                {"code": "FAIL", "name": "Fail", "memo": "second"},
            ],
        )

    assert _rows(module, "a") == before_a
    assert _rows(module, "hk") == before_hk


def test_successful_replace_deduplicates_by_first_position_and_last_content(tmp_path) -> None:
    module = _load_db(tmp_path)
    module.db.zx_add_group_stock("hk", "target", "HK1", "HK 1")
    hk_before = _rows(module, "hk")

    assert module.db.zx_replace_group_stocks(
        "a",
        "target",
        [
            {"code": "A1", "name": "First", "memo": "d", "color": "red"},
            {"code": "A2", "name": "Second", "memo": "d"},
            {"code": "A1", "name": "Latest", "memo": "60m", "color": "blue"},
        ],
    ) is True

    assert _rows(module, "a") == [
        ("A1", "Latest", "60m", "blue", 0),
        ("A2", "Second", "d", "", 1),
    ]
    assert _rows(module, "hk") == hk_before


def test_snapshot_validation_happens_before_the_old_group_is_deleted(tmp_path) -> None:
    module = _load_db(tmp_path)
    module.db.zx_add_group_stock("a", "target", "KEEP", "Keep")
    before = _rows(module, "a")

    for invalid in (
        [{"name": "missing code"}],
        [{"code": "", "name": "empty code"}],
        [{"code": "X" * 21, "name": "too long"}],
        "not-a-list",
    ):
        with pytest.raises((TypeError, ValueError)):
            module.db.zx_replace_group_stocks("a", "target", invalid)
        assert _rows(module, "a") == before


def test_task_replaces_target_once_after_all_frequencies_and_deduplicates(monkeypatch) -> None:
    module = _load_xuangu_module(monkeypatch)
    replacements = []

    class FakeZiXuan:
        def __init__(self, market):
            self.market = market

        def zx_stocks(self, group):
            return [{"code": "SRC", "name": "Source"}]

        def replace_stocks(self, group, snapshot):
            replacements.append((self.market, group, snapshot))
            return True

    class FakeRunner:
        def __init__(self, exchange, strategy):
            pass

        def run(self, market, stocks, frequency):
            if frequency == "d":
                return [_event("A1", name="Daily", message="d"), _event("A2", message="d")]
            return [_event("A1", name="Latest", message="60m")]

    monkeypatch.setattr(module, "ZiXuan", FakeZiXuan)
    monkeypatch.setattr(module, "SelectionRunner", FakeRunner)
    tasks = module.XuanguTasks(None)

    assert tasks.run_xuangu("a", "task1", ["d", "60m"], "source", "target") is True
    assert replacements == [
        (
            "a",
            "target",
            [
                {"code": "A1", "name": "Latest", "memo": "60m"},
                {"code": "A2", "name": "A2", "memo": "d"},
            ],
        )
    ]
    assert [event.code for event in tasks.running_tasks[("a", "task1")]] == ["A1", "A2", "A1"]


def test_strategy_failure_performs_no_replace_and_keeps_previous_running_result(monkeypatch) -> None:
    module = _load_xuangu_module(monkeypatch)
    calls = []

    class FakeZiXuan:
        def __init__(self, market):
            pass

        def zx_stocks(self, group):
            return [{"code": "SRC", "name": "Source"}]

        def replace_stocks(self, group, snapshot):
            calls.append((group, snapshot))
            return True

    class FailingRunner:
        def __init__(self, exchange, strategy):
            pass

        def run(self, market, stocks, frequency):
            if frequency == "60m":
                target = StrategyRunTarget(market, "A2", "A2", frequency)
                return BatchRunResult(
                    failures=[
                        StrategyRunFailure(
                            target=target,
                            stage="strategy",
                            error_type="RuntimeError",
                            message="strategy failure",
                        )
                    ]
                )
            return BatchRunResult(hits=[_event("A1")])

    monkeypatch.setattr(module, "ZiXuan", FakeZiXuan)
    monkeypatch.setattr(module, "SelectionRunner", FailingRunner)
    tasks = module.XuanguTasks(None)
    previous = [_event("OLD")]
    tasks.running_tasks[("a", "task1")] = previous

    assert tasks.run_xuangu("a", "task1", ["d", "60m"], "source", "target") is False

    assert calls == []
    assert tasks.running_tasks[("a", "task1")] is previous
    attempt = tasks.last_run_results[("a", "task1")]
    assert [event.code for event in attempt.hits] == ["A1"]
    assert [(failure.code, failure.stage) for failure in attempt.failures] == [
        ("A2", "strategy")
    ]


def test_replace_failure_keeps_previous_running_result(monkeypatch) -> None:
    module = _load_xuangu_module(monkeypatch)

    class FakeZiXuan:
        def __init__(self, market):
            pass

        def zx_stocks(self, group):
            return [{"code": "SRC", "name": "Source"}]

        def replace_stocks(self, group, snapshot):
            raise RuntimeError("database replacement failed")

    class Runner:
        def __init__(self, exchange, strategy):
            pass

        def run(self, market, stocks, frequency):
            return [_event("A1")]

    monkeypatch.setattr(module, "ZiXuan", FakeZiXuan)
    monkeypatch.setattr(module, "SelectionRunner", Runner)
    tasks = module.XuanguTasks(None)
    previous = [_event("OLD")]
    tasks.running_tasks[("a", "task1")] = previous

    with pytest.raises(RuntimeError, match="database replacement failed"):
        tasks.run_xuangu("a", "task1", ["d"], "source", "target")
    assert tasks.running_tasks[("a", "task1")] is previous


def test_opt_type_is_removed_and_running_results_are_scoped_by_market(monkeypatch) -> None:
    module = _load_xuangu_module(monkeypatch)
    run_signature = inspect.signature(module.XuanguTasks.run_xuangu)
    worker_signature = inspect.signature(module.XuanguTasks._run_xuangu_job)
    app_source = (ROOT / "web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    template = (ROOT / "web/tradingview_zy_chart/cl_app/templates/xuangu_list.html").read_text(encoding="utf-8")
    route = app_source[
        app_source.index('    @app.route("/xuangu/task_add"') :
        app_source.index('    @app.route("/setting"')
    ]

    assert "opt_type" not in run_signature.parameters
    assert "opt_type" not in worker_signature.parameters
    assert "opt_type" not in route
    assert "opt_type" not in template
    assert "选股方向" not in template

    class FakeZiXuan:
        def __init__(self, market):
            pass

        def zx_stocks(self, group):
            return [{"code": "SRC", "name": "Source"}]

    class Runner:
        def __init__(self, exchange, strategy):
            pass

        def run(self, market, stocks, frequency):
            return [_event(f"{market}-result")]

    monkeypatch.setattr(module, "ZiXuan", FakeZiXuan)
    monkeypatch.setattr(module, "SelectionRunner", Runner)
    tasks = module.XuanguTasks(None)
    tasks.run_xuangu("a", "task1", ["d"], "source")
    tasks.run_xuangu("hk", "task1", ["d"], "source")
    assert set(tasks.running_tasks) == {("a", "task1"), ("hk", "task1")}
