"""Behavior regressions for internal validation and batch boundaries."""
from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from test_support.isolated_web_app import run_web_app_script
from tradingview_zy.alert_strategy_storage import (
    STRATEGY_CONFIG_MAX_BYTES,
    StrategyStorageValidationError,
    build_strategy_config,
    normalize_strategy_config,
)
from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.base import (
    StrategyPurpose,
    StrategyRunTarget,
    StrategySignal,
    run_strategy_target,
)


def _bars():
    return pd.DataFrame({
        "date": ["2026-05-04 09:30:00", "2026-05-04 09:31:00"],
        "open": [10, 11], "close": [11, 12], "high": [12, 13],
        "low": [9, 10], "volume": [100, 200],
    })


@pytest.mark.parametrize("kind", ["chart", "chart-update", "template", "drawing"])
def test_storage_http_preserves_database_validation_and_owner_boundary(tmp_path, kind):
    run_web_app_script(tmp_path, """
        from dataclasses import replace
        from sqlalchemy import event

        app = cl_app.create_app(app_config)
        services = app.extensions["tradingview_zy.web_services"]
        database = services.database
        database.tv_storage_policy = replace(
            database.tv_storage_policy,
            chart_max_bytes=8, template_max_bytes=8, drawing_max_bytes=8,
            max_charts=1, max_templates=1, max_drawings=1,
        )
        client = app.test_client()
        owner = services.storage_principal
        with client.session_transaction() as session:
            session["_user_id"] = owner
            session["_csrf_token"] = "boundary-token" * 3
        headers = {"X-CSRF-Token": "boundary-token" * 3}
        query = {"client": " client ", "user": "untrusted-protocol-user"}
        kind = parameters["kind"]
        if kind == "drawing":
            endpoint = "/tv/1.1/drawings"
            query.update(layout=" layout ", chart=" chart ", symbol=" A ")
            form = {"state": "{}"}
            blob_field = "state"
        else:
            endpoint = "/tv/1.1/study_templates" if kind == "template" else "/tv/1.1/charts"
            form = {"name": " saved ", "content": "{}", "symbol": " A ", "resolution": " D "}
            blob_field = "content"
        def post(data=form, args=query):
            return client.post(endpoint, query_string=args, data=data, headers=headers)
        saved = post()
        assert saved.status_code == 200, saved.get_json()
        assert saved.get_json()["status"] == "ok"
        if kind == "chart-update":
            query["chart"] = saved.get_json()["id"]

        transactions = []
        def began(connection):
            transactions.append(connection)
        event.listen(database.engine, "begin", began)
        try:
            response = post({**form, blob_field: "中" * 3})
            assert response.status_code == 422
            assert response.get_json()["error"] == "storage_field_too_large"
            assert transactions == [], "invalid fields must fail before a transaction"
            if kind == "drawing":
                for field in ("client", "user", "chart", "layout"):
                    response = post(args={key: value for key, value in query.items() if key != field})
                    assert response.status_code == 422
                    assert response.get_json()["error"] == "invalid_drawing_request"
                assert post({}).status_code == 422
                assert transactions == []
        finally:
            event.remove(database.engine, "begin", began)

        if kind == "drawing":
            assert database.tv_drawing_get("client", owner, "layout", "chart", "A") == "{}"
            assert database.tv_drawing_get("client", query["user"], "layout", "chart", "A") is None
            quota = post(args={**query, "chart": "another"})
        else:
            chart_type = "template" if kind == "template" else "chart"
            rows = database.tv_chart_list(chart_type, "client", owner)
            assert len(rows) == 1
            assert (rows[0].name, rows[0].content) == ("saved", "{}")
            assert rows[0].symbol == ("" if kind == "template" else "A")
            assert database.tv_chart_list(chart_type, "client", query["user"]) == []
            if kind == "chart-update":
                response = post({**form, "content": "updated"})
                assert response.get_json() == {"status": "ok"}
                assert database.tv_chart_get("chart", rows[0].id, "client", owner).content == "updated"
            quota = post({**form, "name": "another"}, {key: value for key, value in query.items() if key != "chart"})
        assert quota.status_code == 422
        assert quota.get_json()["error"] == "storage_quota_exceeded"
    """, kind=kind)


def test_history_rejects_bad_rows_even_outside_the_requested_window(tmp_path):
    run_web_app_script(tmp_path, """
        from types import SimpleNamespace
        import pandas as pd

        source = pd.DataFrame(parameters["bars"])
        exchange = SimpleNamespace(klines=lambda code, frequency: source, now_trading=lambda code: True)
        cl_app.get_exchange = lambda market: exchange
        app = cl_app.create_app(app_config)
        client = app.test_client()
        last = int(pd.Timestamp(source.iloc[-1]["date"], tz="Asia/Shanghai").timestamp())
        faults = [
            ("volume", -1), ("open", float("inf")), ("high", 0),
            ("code", "OTHER"), ("frequency", "5m"),
            ("date", source.iloc[-1]["date"]),
        ]
        for column, value in faults:
            source = pd.DataFrame(parameters["bars"])
            source["code"] = "SH.600000"
            source["frequency"] = "1m"
            source.loc[0, column] = value
            for first in ("true", "false"):
                for timestamp in (last, last - 3600):
                    response = client.get("/tv/history", query_string={
                        "symbol": "a:SH.600000", "resolution": "1",
                        "from": timestamp, "to": timestamp, "firstDataRequest": first,
                    })
                    assert response.status_code == 200
                    assert response.get_json() == {"s": "error", "errmsg": "invalid_kline_payload"}, (column, first, timestamp)
    """, bars=_bars().to_dict(orient="list"))


def test_history_helpers_remain_independent_and_preserve_order_and_source():
    from tradingview_zy.web_payloads import (
        KlinePayloadError,
        filter_klines_by_timestamp_range,
        klines_to_tv_history,
    )

    source = _bars().set_axis([8, 3])
    original = source.copy(deep=True)
    timestamps = [int(pd.Timestamp(value, tz="Asia/Shanghai").timestamp()) for value in source["date"]]
    filtered = filter_klines_by_timestamp_range(source, timestamps[1], timestamps[1], market="a")
    assert filtered.index.tolist() == [3]
    payload = klines_to_tv_history(source, False, market="a")
    assert payload["t"] == timestamps
    assert payload["o"] == [10, 11]
    assert payload["v"] == [100, 200]
    assert klines_to_tv_history(filtered, True, market="a")["t"] == timestamps[1:]
    window = (timestamps[1], timestamps[1])
    assert klines_to_tv_history(source, True, market="a", timestamp_range=window)["t"] == timestamps[1:]
    assert klines_to_tv_history(source, False, market="a", timestamp_range=window)["t"] == timestamps
    for update in (False, True):
        assert klines_to_tv_history(
            source, update, market="a", timestamp_range=(0, timestamps[0] - 1)
        ) == {"s": "no_data"}
    assert klines_to_tv_history(
        source, True, market="a", timestamp_range=(timestamps[1] + 1, timestamps[1] + 60)
    ) == {"s": "no_data"}
    pd.testing.assert_frame_equal(source, original)
    with pytest.raises(KlinePayloadError):
        klines_to_tv_history(source.assign(volume=[-1, 200]), True, market="a")
    with pytest.raises(KlinePayloadError):
        filter_klines_by_timestamp_range(source.assign(date=["2026-05-04 09:30:00", "bad"]), 0, 1, market="a")


def test_strategy_config_enforces_final_envelope_byte_limit():
    empty_size = len(build_strategy_config("demo", {"text": ""}).encode("utf-8"))
    remaining = STRATEGY_CONFIG_MAX_BYTES - empty_size
    value = "中" * (remaining // 3) + "x" * (remaining % 3)
    canonical = build_strategy_config(" demo ", {"text": value})
    assert len(canonical.encode("utf-8")) == STRATEGY_CONFIG_MAX_BYTES
    assert json.loads(canonical)["strategy_id"] == "demo"
    assert json.loads(canonical)["strategy_kwargs"] == {"text": value}
    assert normalize_strategy_config(canonical) == canonical
    with pytest.raises(StrategyStorageValidationError, match="strategy_config"):
        build_strategy_config("demo", {"text": value + "x"})


@pytest.mark.parametrize("strategy_id,kwargs", [
    ("bad\x00id", {}), ("bad\ud800", {}),
    ("demo", {"text": "\ud800"}), ("demo", {"score": float("nan")}),
    ("demo", {"value": object()}),
])
def test_strategy_config_maps_invalid_parameters_to_storage_error(strategy_id, kwargs):
    with pytest.raises(StrategyStorageValidationError):
        build_strategy_config(strategy_id, kwargs)


@pytest.mark.parametrize("target", [
    StrategyRunTarget("unknown", "A", "Name", "d"),
    StrategyRunTarget("a", "A", "Name", "invalid"),
    StrategyRunTarget("a", "", "Name", "d"),
    StrategyRunTarget("a", "A", "bad\x00name", "d"),
])
def test_public_target_runner_checks_manually_constructed_targets(target):
    calls = []
    result = run_strategy_target(
        SimpleNamespace(klines=lambda *args: calls.append(args)),
        SimpleNamespace(run=lambda context: calls.append(context)),
        target,
        purpose=StrategyPurpose.SELECTION,
    )
    assert calls == []
    assert result.hits == result.misses == []
    assert len(result.failures) == 1
    assert result.failures[0].stage == "target"


def test_public_target_runner_canonicalizes_valid_manual_target():
    target = StrategyRunTarget(" a ", " A ", " Name ", " d ")
    calls = []
    contexts = []

    def klines(code, frequency):
        calls.append((code, frequency))
        return _bars()

    result = run_strategy_target(
        SimpleNamespace(klines=klines),
        SimpleNamespace(run=lambda context: contexts.append(context)),
        target,
        purpose=StrategyPurpose.SELECTION,
    )
    assert result.ok
    assert calls == [("A", "d")]
    assert [(item.market, item.code, item.name, item.frequency) for item in contexts] == [
        ("a", "A", "Name", "d"),
    ]
    assert result.misses == [StrategyRunTarget("a", "A", "Name", "d")]
    assert target.code == " A "


@pytest.mark.parametrize("runner_type,action,wrong_action", [
    (SelectionRunner, "select", "watch"),
    (MonitoringRunner, "watch", "select"),
])
def test_batch_runners_keep_purpose_order_and_failure_isolation(runner_type, action, wrong_action):
    calls = []
    seen = []

    def klines(code, frequency):
        calls.append((code, frequency))
        if code == "TIMEOUT":
            raise TimeoutError("provider unavailable")
        return _bars()

    def run(context):
        seen.append(context.code)
        if context.code == "MISS":
            return None
        return StrategySignal(
            code=context.code, name=context.name,
            action=wrong_action if context.code == "WRONG_ACTION" else action,
            score=1, message="signal", frequency=context.frequency, event_time=context.now,
        )

    stocks = [
        {"code": " FIRST ", "name": " First "}, {"name": "missing code"},
        {"code": "TIMEOUT"}, {"code": "WRONG_ACTION"}, {"code": "MISS"}, {"code": "LAST"},
    ]
    result = runner_type(SimpleNamespace(klines=klines), SimpleNamespace(run=run)).run(
        " a ", iter(stocks), " d ", now=dt.datetime(2026, 5, 4, 15),
    )
    assert [signal.code for signal in result.hits] == ["FIRST", "LAST"]
    assert [signal.action for signal in result.hits] == [action, action]
    assert [target.code for target in result.misses] == ["MISS"]
    assert [(failure.code, failure.stage) for failure in result.failures] == [
        ("<invalid>", "target"), ("TIMEOUT", "provider"), ("WRONG_ACTION", "output"),
    ]
    assert calls == [(code, "d") for code in ("FIRST", "TIMEOUT", "WRONG_ACTION", "MISS", "LAST")]
    assert seen == ["FIRST", "WRONG_ACTION", "MISS", "LAST"]
    assert stocks[0] == {"code": " FIRST ", "name": " First "}


def test_alert_run_rejects_non_batch_result_before_persistence(tmp_path):
    run_web_app_script(tmp_path, """
        from types import SimpleNamespace
        import cl_app.alert_tasks as module

        task = module.AlertTasks()
        task.alert_get = lambda alert_id: SimpleNamespace(
            market="a", task_name="test", zx_group="watch", frequency="d",
            strategy_config='{"strategy_id":"demo","strategy_kwargs":{}}',
        )
        stocks = [{"code": "FIRST"}, {"code": "LAST"}]
        exchange = SimpleNamespace(now_trading=lambda code: True)
        module.get_exchange = lambda market: exchange
        module.ZiXuan = lambda market: SimpleNamespace(zx_stocks=lambda group: stocks)
        module.load_registered_strategy = lambda *args: object()
        saved = []
        module.db.alert_event_save = lambda **kwargs: saved.append(kwargs)
        calls = []
        def run(*args):
            calls.append(args)
            return []
        module.MonitoringRunner = lambda **kwargs: SimpleNamespace(run=run)
        try:
            task.alert_run(1)
        except TypeError as error:
            assert "BatchRunResult" in str(error)
        else:
            raise AssertionError("alert task accepted an unstructured runner result")
        assert calls == [("a", stocks, "d")]
        assert saved == []
        assert task.last_batch_result is None
    """)
