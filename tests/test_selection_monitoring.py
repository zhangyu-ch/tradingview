import datetime as dt
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "web" / "tradingview_zy_chart"))

from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.base import BatchRunResult, StrategyContext, StrategySignal


class FakeExchange:
    def __init__(self):
        self.requested = []

    def klines(self, code, frequency):
        self.requested.append((code, frequency))
        return pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-05-03 09:30:00"),
                    "frequency": frequency,
                    "code": code,
                    "open": 10.0,
                    "close": 11.0,
                    "high": 11.5,
                    "low": 9.8,
                    "volume": 1000,
                }
            ]
        )


class PositiveCloseStrategy:
    name = "positive_close"

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) > float(last["open"]):
            return [
                StrategySignal(
                    code=context.code,
                    name=context.name,
                    action="select",
                    score=1.0,
                    message="close > open",
                    frequency=context.frequency,
                    event_time=context.now,
                )
            ]
        return []


def test_selection_runner_uses_plain_klines_only():
    exchange = FakeExchange()
    runner = SelectionRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    results = runner.run(
        market="a",
        stocks=[{"code": "SH.000001", "name": "上证指数"}],
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert exchange.requested == [("SH.000001", "d")]
    assert results.ok is True
    assert results.failures == []
    assert results.misses == []
    assert results.hits[0].code == "SH.000001"
    assert results.hits[0].message == "close > open"


def test_monitoring_runner_returns_events_without_chanlun_data():
    exchange = FakeExchange()
    runner = MonitoringRunner(exchange=exchange, strategy=PositiveCloseStrategy())

    events = runner.run_code(
        market="a",
        code="SH.000001",
        name="上证指数",
        frequency="d",
        now=dt.datetime(2026, 5, 3, 15, 0, 0),
    )

    assert events.ok is True
    assert events.failures == []
    assert len(events.hits) == 1
    assert events.hits[0].action == "select"
    assert events.hits[0].frequency == "d"


def test_alert_template_uses_strategy_form_without_legacy_fields():
    template = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "templates" / "alert.html"
    ).read_text(encoding="utf-8")

    assert "strategy_path" in template
    assert "strategy_kwargs" in template
    assert "strategy_memo" in template
    for legacy_text in ["笔", "线段", "买卖点", "背驰", "check_bi", "check_xd", "macd"]:
        assert legacy_text not in template


def test_alert_js_task_list_uses_strategy_columns_without_legacy_fields():
    alert_js = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "static" / "js" / "alert.js"
    ).read_text(encoding="utf-8")

    for legacy_field in [
        "line_type",
        "check_bi_",
        "check_xd_",
    ]:
        assert legacy_field not in alert_js
    for legacy_title in ["笔方向", "笔背驰", "笔买卖点", "线段方向", "线段背驰", "线段买卖点"]:
        assert legacy_title not in alert_js
    for strategy_text in ["strategy_config", "strategy_kwargs", "strategy_memo", "策略路径", "策略参数", "策略备注"]:
        assert strategy_text in alert_js
    for event_text in ["event_type", "action", "score"]:
        assert event_text in alert_js


def test_db_alert_models_expose_generic_properties():
    from tradingview_zy.db import TableByAlertRecord, TableByAlertTask

    task = TableByAlertTask(check_idx_ma_info=None, check_idx_macd_info=None)
    assert task.strategy_config == "{}"
    assert task.strategy_memo == ""

    task.check_idx_ma_info = '{"strategy_path": "demo"}'
    task.check_idx_macd_info = "memo"
    assert task.strategy_config == '{"strategy_path": "demo"}'
    assert task.strategy_memo == "memo"

    event_time = dt.datetime(2026, 5, 3, 15, 0, 0)
    record = TableByAlertRecord(
        line_type=None,
        bi_is_done=None,
        bi_is_td=None,
        line_dt=event_time,
    )
    assert record.event_type == ""
    assert record.action == ""
    assert record.score == ""
    assert record.event_time == event_time

    record.line_type = "sig"
    record.bi_is_done = "watch"
    record.bi_is_td = "0.9877"
    assert record.event_type == "sig"
    assert record.action == "watch"
    assert record.score == "0.9877"


def test_alert_tasks_use_generic_db_methods(monkeypatch):
    import cl_app.alert_tasks as alert_tasks

    saved = {}

    class FakeAlertDb:
        def alert_event_save(self, **kwargs):
            saved.update(kwargs)

    event = StrategySignal(
        code="SH.000001",
        name="上证指数",
        action="watch",
        score=123456789.123456,
        message="watch signal",
        frequency="d",
        event_time=dt.datetime(2026, 5, 3, 15, 0, 0),
    )
    alert_config = SimpleNamespace(
        market="a",
        task_name="task1",
        zx_group="source",
        frequency="d",
        strategy_config='{"strategy_id": "demo", "strategy_kwargs": {}}',
    )

    monkeypatch.setattr(alert_tasks.AlertTasks, "alert_get", lambda self, alert_id: alert_config)
    monkeypatch.setattr(alert_tasks, "get_exchange", lambda market: SimpleNamespace(now_trading=lambda code=None, at=None: True))
    monkeypatch.setattr(
        alert_tasks,
        "ZiXuan",
        lambda market: SimpleNamespace(
            zx_stocks=lambda group: [{"code": "SH.000001", "name": "上证指数"}]
        ),
    )
    monkeypatch.setattr(alert_tasks.AlertTasks, "strategy_registry", staticmethod(lambda: {"demo": {"strategy_path": "trusted:Demo"}}))
    monkeypatch.setattr(alert_tasks, "load_registered_strategy", lambda registry, strategy_id, kwargs: object())
    monkeypatch.setattr(
        alert_tasks,
        "MonitoringRunner",
        lambda exchange, strategy: SimpleNamespace(
            run=lambda *args, **kwargs: BatchRunResult(hits=[event])
        ),
    )
    monkeypatch.setattr(alert_tasks, "db", FakeAlertDb())

    assert alert_tasks.AlertTasks(None).alert_run("1") is True

    assert saved["event_type"] == "sig"
    assert saved["action"] == "watch"
    assert saved["score"] == "1.235e+08"
    assert len(saved["score"]) <= 10
    assert "line_type" not in saved
    assert "bi_is_done" not in saved
    assert "bi_is_td" not in saved


def test_alert_save_uses_generic_task_methods(monkeypatch):
    import cl_app.alert_tasks as alert_tasks

    calls = []

    class FakeAlertDb:
        def task_save_strategy(self, **kwargs):
            calls.append(("save", kwargs.copy()))

        def task_update_strategy(self, **kwargs):
            calls.append(("update", kwargs.copy()))

    monkeypatch.setattr(alert_tasks, "db", FakeAlertDb())
    monkeypatch.setattr(alert_tasks.AlertTasks, "run", lambda self: True)

    tasks = alert_tasks.AlertTasks(None)
    base_config = {
        "id": "",
        "market": "a",
        "task_name": "task1",
        "interval_minutes": 5,
        "zx_group": "source",
        "frequency": "d",
        "strategy_config": '{"strategy_path": "unused"}',
        "strategy_memo": "memo",
        "is_send_msg": 1,
        "is_run": 1,
    }

    assert tasks.alert_save(base_config.copy()) is True
    assert calls[-1] == (
        "save",
        {
            "market": "a",
            "task_name": "task1",
            "interval_minutes": 5,
            "zx_group": "source",
            "frequency": "d",
            "strategy_config": '{"strategy_path": "unused"}',
            "strategy_memo": "memo",
            "is_send_msg": 1,
            "is_run": 1,
        },
    )

    update_config = {**base_config, "id": "7"}
    assert tasks.alert_save(update_config) is True
    assert calls[-1][0] == "update"
    assert calls[-1][1]["id"] == 7
    assert "check_bi_type" not in calls[-1][1]
    assert "check_idx_ma_info" not in calls[-1][1]


def test_alert_routes_use_generic_fields_without_legacy_payload_keys():
    app_source = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "__init__.py"
    ).read_text(encoding="utf-8")
    alert_section = app_source[app_source.index('    @app.route("/alert_list/<market>")'):app_source.index('    @app.route("/jobs")')]

    for generic_text in [
        "strategy_config",
        "strategy_memo",
        "event_type",
        "action",
        "score",
        "event_time",
    ]:
        assert generic_text in alert_section
    for legacy_text in [
        '"check_bi_type"',
        '"check_bi_beichi"',
        '"check_bi_mmd"',
        '"check_xd_type"',
        '"check_xd_beichi"',
        '"check_xd_mmd"',
        '"check_idx_ma_info"',
        '"check_idx_macd_info"',
        '"check_idx_ma_info_enable"',
        '"check_idx_macd_info_enable"',
        '"line_type"',
        '"is_done"',
        '"is_td"',
        ".check_idx_ma_info",
        ".check_idx_macd_info",
        ".line_type",
        ".bi_is_done",
        ".bi_is_td",
    ]:
        assert legacy_text not in alert_section


def test_alert_run_rejects_non_object_strategy_config(monkeypatch):
    import cl_app.alert_tasks as alert_tasks

    errors = []
    alert_config = SimpleNamespace(
        market="a",
        task_name="task1",
        zx_group="source",
        frequency="d",
        strategy_config="[]",
    )

    monkeypatch.setattr(alert_tasks.AlertTasks, "alert_get", lambda self, alert_id: alert_config)
    monkeypatch.setattr(alert_tasks, "get_exchange", lambda market: SimpleNamespace(now_trading=lambda code=None, at=None: True))
    monkeypatch.setattr(
        alert_tasks,
        "ZiXuan",
        lambda market: SimpleNamespace(zx_stocks=lambda group: []),
    )

    tasks = alert_tasks.AlertTasks(None)
    tasks.log = SimpleNamespace(
        info=lambda msg: None,
        error=lambda msg: errors.append(msg),
    )

    assert tasks.alert_run("1") is False
    assert any("strategy_config" in msg and "JSON 对象" in msg for msg in errors)


class FakeZiXuan:
    instances = []

    def __init__(self, market):
        self.market = market
        self.cleared_groups = []
        self.added_stocks = []
        self.replaced_snapshots = []
        FakeZiXuan.instances.append(self)

    def zx_stocks(self, zx_group):
        return [{"code": "SH.000001", "name": "上证指数"}]

    def replace_stocks(self, zx_group, snapshot):
        self.replaced_snapshots.append((zx_group, snapshot))
        return True

    def clear_zx_stocks(self, zx_group):
        self.cleared_groups.append(zx_group)
        return True

    def add_stock(self, zx_group, code, name, memo=""):
        self.added_stocks.append((zx_group, code, name, memo))
        return True


class XuanguTaskStrategy:
    name = "xuangu_task_strategy"

    def run(self, context: StrategyContext):
        return [
            StrategySignal(
                code=context.code,
                name=context.name,
                action="select",
                score=0.98765,
                message="selected by task",
                frequency=context.frequency,
                event_time=context.now,
            )
        ]


def test_xuangu_task_add_without_target_group_passes_empty_target(monkeypatch):
    import cl_app

    calls = []

    class FakeXuanguTasks:
        def xuangu_task_config_list(self):
            return {"task1": {"frequency_num": 1}}

        def run_xuangu(self, market, task_name, frequencys, src_zx_group, target_zx_group):
            calls.append(
                {
                    "market": market,
                    "task_name": task_name,
                    "frequencys": frequencys,
                    "src_zx_group": src_zx_group,
                    "target_zx_group": target_zx_group,
                }
            )
            return True

    monkeypatch.setattr(cl_app.config, "LOGIN_PWD", "")
    fake_exchange = SimpleNamespace(
        support_frequencys=lambda: {"d": "日线"},
        default_code=lambda: "SH.000001",
    )
    monkeypatch.setattr(cl_app, "get_exchange", lambda market: fake_exchange)

    app = cl_app.create_app()
    route_view = app.view_functions["xuangu_task_add"]
    wrapped_view = route_view.__wrapped__
    closure_cells = dict(zip(wrapped_view.__code__.co_freevars, wrapped_view.__closure__))
    monkeypatch.setattr(closure_cells["_xuangu_tasks"].cell_contents, "_task_obj", FakeXuanguTasks())

    base_form = {
        "market": "a",
        "task_name": "task1",
        "frequencys": "d",
        "src_zx_group": "source",
    }
    for target_value, expected_target in [(None, ""), ("   ", ""), ("target", "target")]:
        form = base_form.copy()
        if target_value is not None:
            form["target_zx_group"] = target_value
        with app.test_request_context(
            "/xuangu/task_add",
            method="POST",
            data=form,
        ):
            response = wrapped_view()

        assert response["ok"] is True
        assert calls[-1]["src_zx_group"] == "source"
        assert calls[-1]["target_zx_group"] == expected_target


def test_tv_history_backfill_returns_ohlcv_when_market_is_closed(monkeypatch):
    import cl_app

    class ClosedMarketExchange:
        def support_frequencys(self):
            return {"d": "日线"}

        def default_code(self):
            return "SH.000001"

        def now_trading(self, code=None, at=None):
            return False

        def klines(self, code, frequency):
            return pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-05-03 09:30:00"),
                        "open": 10.0,
                        "close": 10.5,
                        "high": 10.8,
                        "low": 9.9,
                        "volume": 100,
                    }
                ]
            )

    monkeypatch.setattr(cl_app, "get_exchange", lambda market: ClosedMarketExchange())

    app = cl_app.create_app()
    view = app.view_functions["tv_history"].__wrapped__
    start_ts = int(pd.Timestamp("2026-05-03 09:00:00").timestamp())
    end_ts = int(pd.Timestamp("2026-05-03 10:00:00").timestamp())
    with app.test_request_context(
        f"/tv/history?symbol=a:SH.000001&resolution=1D&from={start_ts}&to={end_ts}&firstDataRequest=false"
    ):
        response = view()

    assert response["s"] == "ok"
    assert response["o"] == [10.0]
    assert response["c"] == [10.5]
    assert "bis" not in response
    assert "mmds" not in response


def test_alert_js_strategy_config_parser_rejects_null_and_arrays():
    alert_js = (
        ROOT / "web" / "tradingview_zy_chart" / "cl_app" / "static" / "js" / "alert.js"
    ).read_text(encoding="utf-8")

    assert "function isPlainObject(value)" in alert_js
    assert "value !== null" in alert_js
    assert "!Array.isArray(value)" in alert_js
    assert "return isPlainObject(config) ? config : {};" in alert_js


def test_tv_history_first_request_returns_available_history_for_zoom_out(monkeypatch):
    import cl_app

    class HistoricalExchange:
        def support_frequencys(self):
            return {"d": "日线"}

        def default_code(self):
            return "SH.000001"

        def now_trading(self, code=None, at=None):
            return True

        def klines(self, code, frequency):
            return pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-04-29 09:30:00"),
                        "open": 8.0,
                        "close": 8.5,
                        "high": 8.8,
                        "low": 7.9,
                        "volume": 80,
                    },
                    {
                        "date": pd.Timestamp("2026-05-01 09:30:00"),
                        "open": 9.0,
                        "close": 9.5,
                        "high": 9.8,
                        "low": 8.9,
                        "volume": 90,
                    },
                    {
                        "date": pd.Timestamp("2026-05-03 09:30:00"),
                        "open": 10.0,
                        "close": 10.5,
                        "high": 10.8,
                        "low": 9.9,
                        "volume": 100,
                    },
                ]
            )

    monkeypatch.setattr(cl_app, "get_exchange", lambda market: HistoricalExchange())

    app = cl_app.create_app()
    view = app.view_functions["tv_history"].__wrapped__
    start_ts = int(pd.Timestamp("2026-05-03 09:00:00").timestamp())
    end_ts = int(pd.Timestamp("2026-05-03 10:00:00").timestamp())
    with app.test_request_context(
        f"/tv/history?symbol=a:SH.000001&resolution=1D&from={start_ts}&to={end_ts}&firstDataRequest=true"
    ):
        response = view()

    assert response["s"] == "ok"
    assert response["o"] == [8.0, 9.0, 10.0]
    assert response["update"] is False


def test_xuangu_task_without_target_group_only_updates_running_results(monkeypatch):
    import cl_app.xuangu_tasks as xuangu_tasks

    FakeZiXuan.instances = []
    monkeypatch.setattr(
        xuangu_tasks,
        "config",
        SimpleNamespace(
            XUANGU_STRATEGIES={
                "task1": {"strategy_path": "unused", "strategy_kwargs": {}}
            }
        ),
    )
    monkeypatch.setattr(xuangu_tasks, "load_registered_strategy", lambda registry, task_name: XuanguTaskStrategy())
    monkeypatch.setattr(xuangu_tasks, "get_exchange", lambda market: FakeExchange())
    monkeypatch.setattr(xuangu_tasks, "ZiXuan", FakeZiXuan)

    tasks = xuangu_tasks.XuanguTasks(None)
    assert tasks.run_xuangu("a", "task1", ["d"], "source") is True

    zx = FakeZiXuan.instances[0]
    assert zx.cleared_groups == []
    assert zx.added_stocks == []
    assert tasks.running_tasks[("a", "task1")][0].code == "SH.000001"


def test_xuangu_task_writes_results_to_target_zx_group(monkeypatch):
    import cl_app.xuangu_tasks as xuangu_tasks

    FakeZiXuan.instances = []
    monkeypatch.setattr(
        xuangu_tasks,
        "config",
        SimpleNamespace(
            XUANGU_STRATEGIES={
                "task1": {"strategy_path": "unused", "strategy_kwargs": {}}
            }
        ),
    )
    monkeypatch.setattr(xuangu_tasks, "load_registered_strategy", lambda registry, task_name: XuanguTaskStrategy())
    monkeypatch.setattr(xuangu_tasks, "get_exchange", lambda market: FakeExchange())
    monkeypatch.setattr(xuangu_tasks, "ZiXuan", FakeZiXuan)

    tasks = xuangu_tasks.XuanguTasks(None)
    assert tasks.run_xuangu("a", "task1", ["d"], "source", "target") is True

    zx = FakeZiXuan.instances[0]
    assert zx.cleared_groups == []
    assert zx.added_stocks == []
    assert zx.replaced_snapshots == [(
        "target",
        [{"code": "SH.000001", "name": "上证指数", "memo": "selected by task"}],
    )]
    assert tasks.running_tasks[("a", "task1")][0].code == "SH.000001"
