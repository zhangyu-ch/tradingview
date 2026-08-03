from __future__ import annotations

import ast
import json
import uuid
from types import SimpleNamespace


def _load_route(request, db, logger):
    source = open("web/tradingview_zy_chart/cl_app/__init__.py", encoding="utf-8").read()
    tree = ast.parse(source)
    create_app = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_app")
    route = next(node for node in create_app.body if isinstance(node, ast.FunctionDef) and node.name == "tv_drawings")
    route.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[route], type_ignores=[]))
    namespace = {"request": request, "db": db, "json": json, "uuid": uuid, "__log": logger}
    exec(compile(module, "tv_drawings", "exec"), namespace)
    return namespace["tv_drawings"]


class FakeLogger:
    def __init__(self):
        self.exceptions = []
        self.errors = []

    def exception(self, message, *args):
        self.exceptions.append((message, args))

    def error(self, message, *args):
        self.errors.append((message, args))


def _request(*, method="POST", args=None, form=None, json_data=None):
    return SimpleNamespace(
        method=method,
        args=args or {},
        form=form or {},
        get_json=lambda silent=True: json_data,
    )


def test_drawing_save_returns_ok_only_for_strict_true():
    calls = []
    db = SimpleNamespace(tv_drawing_save_or_update=lambda *args: calls.append(args) or True)
    logger = FakeLogger()
    route = _load_route(
        _request(args={"client": "c", "user": "u", "chart": "1", "layout": "2", "symbol": "a:1"}, form={"state": "{}"}),
        db,
        logger,
    )
    assert route("1.1") == {"status": "ok"}
    assert calls == [("c", "u", "2", "1", "a:1", "{}")]
    assert logger.errors == logger.exceptions == []


def test_drawing_save_exception_returns_500_and_correlated_request_id():
    def fail(*args):
        raise RuntimeError("sensitive database detail")

    logger = FakeLogger()
    route = _load_route(
        _request(args={"client": "c", "user": "u", "chart": "1", "layout": "2"}, json_data={"state": {"symbol": "a:1"}}),
        SimpleNamespace(tv_drawing_save_or_update=fail),
        logger,
    )
    payload, status = route("1.1")
    assert status == 500
    assert payload["status"] == "error"
    assert payload["error"] == "drawing_save_failed"
    assert len(payload["request_id"]) == 32
    assert "sensitive" not in str(payload)
    assert logger.exceptions and payload["request_id"] in logger.exceptions[0][1]


def test_drawing_save_false_or_none_is_not_success():
    for result in (False, None):
        logger = FakeLogger()
        route = _load_route(
            _request(args={"client": "c", "user": "u", "chart": "1", "layout": "2", "symbol": "a:1"}, form={"state": "{}"}),
            SimpleNamespace(tv_drawing_save_or_update=lambda *args, _result=result: _result),
            logger,
        )
        payload, status = route("1.1")
        assert status == 500
        assert payload["error"] == "drawing_save_failed"
        assert logger.errors


def test_drawing_save_missing_required_fields_returns_422_without_db_call():
    calls = []
    route = _load_route(
        _request(args={"client": "c", "user": "u", "chart": "1"}, form={"state": "{}"}),
        SimpleNamespace(tv_drawing_save_or_update=lambda *args: calls.append(args)),
        FakeLogger(),
    )
    payload, status = route("1.1")
    assert status == 422
    assert payload["error"] == "invalid_drawing_request"
    assert calls == []


def test_drawing_get_contract_is_unchanged():
    route = _load_route(
        _request(method="GET", args={"client": "c", "user": "u", "chart": "1", "layout": "2", "symbol": "a:1"}),
        SimpleNamespace(tv_drawing_get=lambda *args: "saved-state"),
        FakeLogger(),
    )
    assert route("1.1") == {"status": "ok", "data": {"state": "saved-state"}}
