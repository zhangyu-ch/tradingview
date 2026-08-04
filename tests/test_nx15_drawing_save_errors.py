from __future__ import annotations

import ast
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from tradingview_zy.tv_storage import (
    TVStorageError,
    TVStoragePolicy,
    normalize_drawing_payload,
    resolve_storage_owner,
)


def _load_route(request, db, logger):
    source = Path("web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    create_app = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "create_app")
    route = next(node for node in create_app.body if isinstance(node, ast.FunctionDef) and node.name == "tv_drawings")
    route.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[route], type_ignores=[]))
    namespace = {
        "request": request,
        "db": db,
        "json": json,
        "uuid": uuid,
        "__log": logger,
        "TVStorageError": TVStorageError,
        "normalize_drawing_payload": normalize_drawing_payload,
        "resolve_storage_owner": resolve_storage_owner,
        "current_user": SimpleNamespace(get_id=lambda: "session-user"),
    }
    exec(compile(module, "tv_drawings", "exec"), namespace)
    return namespace["tv_drawings"]


def _db(save=None, get=None):
    return SimpleNamespace(
        tv_storage_policy=TVStoragePolicy(),
        tv_drawing_save_or_update=save or (lambda **kwargs: True),
        tv_drawing_get=get or (lambda *args: None),
    )


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
    db = _db(save=lambda **kwargs: calls.append(kwargs) or True)
    logger = FakeLogger()
    route = _load_route(
        _request(args={"client": "c", "user": "u", "chart": "1", "layout": "2", "symbol": "a:1"}, form={"state": "{}"}),
        db,
        logger,
    )
    assert route("1.1") == {"status": "ok"}
    assert calls == [{"client_id": "c", "user_id": "session-user", "layout_id": "2", "chart_id": "1", "symbol": "a:1", "state": "{}"}]
    assert logger.errors == logger.exceptions == []


def test_drawing_save_exception_returns_500_and_correlated_request_id():
    def fail(**kwargs):
        raise RuntimeError("sensitive database detail")

    logger = FakeLogger()
    route = _load_route(
        _request(args={"client": "c", "user": "u", "chart": "1", "layout": "2"}, json_data={"state": {"symbol": "a:1"}}),
        _db(save=fail),
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
            _db(save=lambda _result=result, **kwargs: _result),
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
        _db(save=lambda **kwargs: calls.append(kwargs)),
        FakeLogger(),
    )
    payload, status = route("1.1")
    assert status == 422
    assert payload["error"] == "invalid_drawing_request"
    assert calls == []


def test_drawing_get_contract_is_unchanged():
    route = _load_route(
        _request(method="GET", args={"client": "c", "user": "u", "chart": "1", "layout": "2", "symbol": "a:1"}),
        _db(get=lambda *args: "saved-state"),
        FakeLogger(),
    )
    assert route("1.1") == {"status": "ok", "data": {"state": "saved-state"}}
