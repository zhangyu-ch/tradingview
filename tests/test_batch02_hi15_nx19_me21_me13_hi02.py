from __future__ import annotations

import ast
import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _module_nodes(path: Path, names: set[str], namespace: dict):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = []
    for node in tree.body:
        node_name = getattr(node, "name", None)
        if node_name in names:
            nodes.append(node)
    missing = names - {getattr(node, "name", None) for node in nodes}
    if missing:
        raise AssertionError(f"missing definitions in {path}: {sorted(missing)}")
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _class_with_methods(path: Path, class_name: str, method_names: set[str], namespace: dict):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    original = next(
        node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    methods = [
        node
        for node in original.body
        if isinstance(node, ast.FunctionDef) and node.name in method_names
    ]
    missing = method_names - {node.name for node in methods}
    if missing:
        raise AssertionError(f"missing methods in {path}: {sorted(missing)}")
    replacement = ast.ClassDef(
        name=class_name,
        bases=[],
        keywords=[],
        body=methods,
        decorator_list=[],
    )
    module = ast.fix_missing_locations(ast.Module(body=[replacement], type_ignores=[]))
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[class_name]


class _DateFun:
    @staticmethod
    def str_to_datetime(value: str, fmt: str | None = None) -> dt.datetime:
        return dt.datetime.strptime(value, fmt) if fmt else dt.datetime.fromisoformat(value)


def test_hi15_shared_date_parser_supports_documented_types():
    path = ROOT / "src/tradingview_zy/exchange/date_utils.py"
    namespace = {"dt": dt, "fun": _DateFun}
    _module_nodes(path, {"parse_optional_datetime"}, namespace)
    parse = namespace["parse_optional_datetime"]

    aware = dt.datetime(2024, 1, 2, 3, 4, tzinfo=dt.timezone(dt.timedelta(hours=8)))
    assert parse(None, field_name="value") is None
    assert parse(aware, field_name="value") is aware
    assert parse(dt.date(2024, 1, 2), field_name="value") == dt.datetime(2024, 1, 2)
    assert parse("2024-01-02", field_name="value") == dt.datetime(2024, 1, 2)
    assert parse("2024-01-02 03:04:05", field_name="value") == dt.datetime(
        2024, 1, 2, 3, 4, 5
    )
    assert parse("2024-01-02T03:04:05+08:00", field_name="value").utcoffset() == dt.timedelta(
        hours=8
    )
    with pytest.raises(TypeError, match="must be str, date, datetime, or None"):
        parse(123, field_name="value")
    with pytest.raises(ValueError, match="cannot be empty"):
        parse("  ", field_name="value")


def test_hi15_both_us_adapters_parse_start_and_end_without_len_datetime():
    for relative in [
        "src/tradingview_zy/exchange/exchange_alpaca.py",
        "src/tradingview_zy/exchange/exchange_polygon.py",
    ]:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "from tradingview_zy.exchange.date_utils import parse_optional_datetime" in source
        assert "parse_optional_datetime(end_date" in source
        assert "parse_optional_datetime(\n                    start_date" in source
        assert "len(end_date)" not in source


def _load_tdx_selector(stock_ip, future_ip, ping):
    path = ROOT / "src/tradingview_zy/tools/tdx_best_ip.py"
    namespace = {
        "datetime": dt,
        "stock_ip": stock_ip,
        "future_ip": future_ip,
        "ping": ping,
    }
    _module_nodes(path, {"TdxServerUnavailable", "select_best_ip"}, namespace)
    return namespace


def test_nx19_empty_tdx_probe_has_descriptive_error():
    endpoints = [
        {"ip": "10.0.0.1", "port": 7709},
        {"ip": "10.0.0.2", "port": 7709},
    ]
    namespace = _load_tdx_selector(
        endpoints,
        [],
        lambda *_args: dt.timedelta(9, 9, 0),
    )
    with pytest.raises(namespace["TdxServerUnavailable"], match="已检查 2 个候选节点"):
        namespace["select_best_ip"]("stock")


def test_nx19_returns_fastest_healthy_tdx_probe_and_rejects_unknown_type():
    endpoints = [
        {"ip": "slow", "port": 7709},
        {"ip": "fast", "port": 7709},
        {"ip": "dead", "port": 7709},
    ]
    latency = {
        "slow": dt.timedelta(milliseconds=20),
        "fast": dt.timedelta(milliseconds=5),
        "dead": dt.timedelta(9, 9, 0),
    }
    namespace = _load_tdx_selector(
        endpoints,
        [],
        lambda ip, _port, _type: latency[ip],
    )
    assert namespace["select_best_ip"]("stock") == endpoints[1]
    with pytest.raises(ValueError, match="unsupported TDX server type"):
        namespace["select_best_ip"]("invalid")


def _signal_window_class():
    return _class_with_methods(
        ROOT / "src/tradingview_zy/backtesting/signal_to_trade.py",
        "SignalToTrade",
        {"_parse_trade_boundary", "_apply_trade_window"},
        {"datetime": dt},
    )


def test_me21_start_and_end_boundaries_apply_independently():
    cls = _signal_window_class()

    start_only = cls()
    start_only.trade_start_date = "2024-01-02"
    start_only.trade_end_date = None
    bt = SimpleNamespace(start_datetime="2024-01-01", end_datetime="2024-01-31")
    start_only._apply_trade_window(bt)
    assert bt.start_datetime == "2024-01-02"
    assert bt.end_datetime == "2024-01-31"

    end_only = cls()
    end_only.trade_start_date = None
    end_only.trade_end_date = dt.date(2024, 1, 20)
    bt = SimpleNamespace(start_datetime="2024-01-01", end_datetime="2024-01-31")
    end_only._apply_trade_window(bt)
    assert bt.start_datetime == "2024-01-01"
    assert bt.end_datetime == dt.date(2024, 1, 20)


def test_me21_rejects_reversed_or_mixed_timezone_window():
    cls = _signal_window_class()

    reversed_window = cls()
    reversed_window.trade_start_date = "2024-02-01"
    reversed_window.trade_end_date = "2024-01-01"
    with pytest.raises(ValueError, match="must not be later"):
        reversed_window._apply_trade_window(
            SimpleNamespace(start_datetime=None, end_datetime=None)
        )

    mixed_timezone = cls()
    mixed_timezone.trade_start_date = "2024-01-01T00:00:00+08:00"
    mixed_timezone.trade_end_date = "2024-01-02T00:00:00"
    with pytest.raises(ValueError, match="same timezone style"):
        mixed_timezone._apply_trade_window(
            SimpleNamespace(start_datetime=None, end_datetime=None)
        )


def test_me13_tdx_futures_cache_uses_versioned_key_with_legacy_fallback():
    path = ROOT / "src/tradingview_zy/exchange/exchange_tdx_futures.py"
    source = path.read_text(encoding="utf-8")
    namespace = {}
    _module_nodes(path, {"tdx_futures_cache_code"}, namespace)

    assert namespace["tdx_futures_cache_code"]("rb2409") == "v1_rb2409"
    assert "cache_code = tdx_futures_cache_code(code)" in source
    assert "Market.FUTURES.value, cache_code, frequency" in source
    assert "legacy_klines = self.fdb.get_tdx_klines(" in source
    assert "Market.FUTURES.value, code, frequency" in source
    assert "self.fdb.save_tdx_klines(\n                Market.FUTURES.value, cache_code" in source


class _FakeLogger:
    def __init__(self):
        self.errors = []

    def info(self, _message):
        return None

    def error(self, message):
        self.errors.append(message)


class _AlertTaskValidationError(ValueError):
    pass


def _load_alert_module(sent_messages=None, saved_events=None):
    sent_messages = [] if sent_messages is None else sent_messages
    saved_events = [] if saved_events is None else saved_events
    path = ROOT / "web/tradingview_zy_chart/cl_app/alert_tasks.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    body = [
        node
        for node in tree.body
        if not isinstance(node, (ast.Import, ast.ImportFrom))
        and not (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and "__name__" in ast.unparse(node.test)
        )
    ]
    module = ast.fix_missing_locations(ast.Module(body=body, type_ignores=[]))

    fake_db = SimpleNamespace(
        task_query=lambda **_kwargs: [],
        task_save_strategy=lambda **_kwargs: None,
        task_update_strategy=lambda **_kwargs: None,
        task_delete=lambda _id: None,
        alert_event_save=lambda **kwargs: saved_events.append(kwargs),
    )
    namespace = {
        "json": json,
        "Dict": Dict,
        "List": List,
        "BackgroundScheduler": object,
        "tqdm": lambda values: values,
        "config": SimpleNamespace(ALERT_STRATEGIES={}),
        "fun": SimpleNamespace(get_logger=_FakeLogger),
        "utils": SimpleNamespace(
            send_fs_msg=lambda market, title, contents: sent_messages.append(
                (market, title, contents)
            )
        ),
        "AlertTaskValidationError": _AlertTaskValidationError,
        "TableByAlertTask": object,
        "db": fake_db,
        "Market": lambda value: value,
        "get_exchange": lambda _market: SimpleNamespace(now_trading=lambda: True),
        "MonitoringRunner": lambda **_kwargs: None,
        "StrategyRegistryError": RuntimeError,
        "find_registered_strategy_id_by_path": lambda _registry, _path: None,
        "load_registered_strategy": lambda _registry, _id, _kwargs: object(),
        "ZiXuan": lambda _market: SimpleNamespace(
            zx_stocks=lambda _group: [{"code": "AAPL", "name": "Apple"}]
        ),
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace, sent_messages, saved_events


def test_hi02_interval_validation_and_scheduler_are_exact():
    namespace, _, _ = _load_alert_module()
    validate = namespace["validate_interval_minutes"]
    assert [validate(value) for value in (1, "90", 1440)] == [1, 90, 1440]
    for value in (0, 1441, True, 1.5, "abc", None):
        with pytest.raises(_AlertTaskValidationError):
            validate(value)

    class Scheduler:
        def __init__(self):
            self.jobs = []

        def remove_job(self, _job_id):
            return None

        def add_job(self, **kwargs):
            self.jobs.append(kwargs)
            return SimpleNamespace(id=kwargs["id"])

    scheduler = Scheduler()
    task_runner = namespace["AlertTasks"](scheduler)
    task_runner.task_list = lambda: [
        SimpleNamespace(id=7, task_name="90分钟", interval_minutes=90, is_run=1),
        SimpleNamespace(id=8, task_name="非法", interval_minutes=0, is_run=1),
        SimpleNamespace(id=9, task_name="停用", interval_minutes=5, is_run=0),
    ]
    assert task_runner.run() is True
    assert scheduler.jobs == [
        {
            "func": task_runner.alert_run,
            "trigger": "interval",
            "args": (7,),
            "id": "7",
            "name": "监控-90分钟",
            "minutes": 90,
        }
    ]
    assert any("配置无效" in message for message in task_runner.log.errors)


def test_hi02_message_switch_controls_one_aggregated_notification():
    sent_messages = []
    saved_events = []
    namespace, _, _ = _load_alert_module(sent_messages, saved_events)
    event = SimpleNamespace(
        code="AAPL",
        name="Apple",
        frequency="5m",
        message="breakout",
        action="buy",
        score=0.9,
        event_time=dt.datetime(2024, 1, 1),
    )
    namespace["MonitoringRunner"] = lambda **_kwargs: SimpleNamespace(
        run_code=lambda *_args: [event]
    )
    task_runner = namespace["AlertTasks"](SimpleNamespace())
    base = dict(
        id=1,
        market="us",
        task_name="突破",
        zx_group="关注",
        frequency="5m",
        strategy_config='{"strategy_id":"safe","strategy_kwargs":{}}',
    )

    task_runner.alert_get = lambda _id: SimpleNamespace(**base, is_send_msg=0)
    assert task_runner.alert_run(1) is True
    assert len(saved_events) == 1
    assert sent_messages == []

    task_runner.alert_get = lambda _id: SimpleNamespace(**base, is_send_msg=1)
    assert task_runner.alert_run(1) is True
    assert len(saved_events) == 2
    assert len(sent_messages) == 1
    assert sent_messages[0][0] == "us"
    assert sent_messages[0][1] == "突破 监控提醒"
    assert sent_messages[0][2] == ["Apple(AAPL) 5m buy: breakout"]


def test_hi02_form_allows_non_hour_intervals_and_rejects_out_of_range():
    source = (
        ROOT / "web/tradingview_zy_chart/cl_app/templates/alert.html"
    ).read_text(encoding="utf-8")
    assert "1-1440分钟" in source
    assert "支持90、150等非整小时" in source
    assert "interval > 1440" in source
    assert "interval % 60" not in source
    assert "60分钟以上必须是60的整数倍" not in source
