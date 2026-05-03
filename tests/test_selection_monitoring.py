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
from tradingview_zy.strategies.base import StrategyContext, StrategySignal


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
    assert results[0].code == "SH.000001"
    assert results[0].message == "close > open"


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

    assert len(events) == 1
    assert events[0].action == "select"
    assert events[0].frequency == "d"


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
        "check_bi_type",
        "check_bi_beichi",
        "check_bi_mmd",
        "check_xd_type",
        "check_xd_beichi",
        "check_xd_mmd",
    ]:
        assert legacy_field not in alert_js
    for legacy_title in ["笔方向", "笔背驰", "笔买卖点", "线段方向", "线段背驰", "线段买卖点"]:
        assert legacy_title not in alert_js
    for strategy_text in ["strategy_config", "strategy_kwargs", "strategy_memo", "策略路径", "策略参数", "策略备注"]:
        assert strategy_text in alert_js


def test_alert_records_use_length_safe_strategy_fields(monkeypatch):
    import cl_app.alert_tasks as alert_tasks

    saved = {}

    class FakeAlertDb:
        def alert_record_save(self, **kwargs):
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
        check_idx_ma_info='{"strategy_path": "unused", "strategy_kwargs": {}}',
    )

    monkeypatch.setattr(alert_tasks.AlertTasks, "alert_get", lambda self, alert_id: alert_config)
    monkeypatch.setattr(alert_tasks, "get_exchange", lambda market: SimpleNamespace(now_trading=lambda: True))
    monkeypatch.setattr(
        alert_tasks,
        "ZiXuan",
        lambda market: SimpleNamespace(
            zx_stocks=lambda group: [{"code": "SH.000001", "name": "上证指数"}]
        ),
    )
    monkeypatch.setattr(alert_tasks, "load_strategy", lambda path, **kwargs: object())
    monkeypatch.setattr(
        alert_tasks,
        "MonitoringRunner",
        lambda exchange, strategy: SimpleNamespace(
            run_code=lambda *args, **kwargs: [event]
        ),
    )
    monkeypatch.setattr(alert_tasks, "db", FakeAlertDb())

    assert alert_tasks.AlertTasks(None).alert_run("1") is True

    assert saved["line_type"] == "sig"
    assert saved["bi_is_td"] == "1.235e+08"
    assert len(saved["bi_is_td"]) <= 10


class FakeZiXuan:
    instances = []

    def __init__(self, market):
        self.market = market
        self.cleared_groups = []
        self.added_stocks = []
        FakeZiXuan.instances.append(self)

    def zx_stocks(self, zx_group):
        return [{"code": "SH.000001", "name": "上证指数"}]

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
    monkeypatch.setattr(xuangu_tasks, "load_strategy", lambda path, **kwargs: XuanguTaskStrategy())
    monkeypatch.setattr(xuangu_tasks, "get_exchange", lambda market: FakeExchange())
    monkeypatch.setattr(xuangu_tasks, "ZiXuan", FakeZiXuan)

    tasks = xuangu_tasks.XuanguTasks(None)
    assert tasks.run_xuangu("a", "task1", ["d"], ["long"], "source", "target") is True

    zx = FakeZiXuan.instances[0]
    assert zx.cleared_groups == ["target"]
    assert zx.added_stocks == [("target", "SH.000001", "上证指数", "selected by task")]
    assert tasks.running_tasks["task1"][0].code == "SH.000001"
