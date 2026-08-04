from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_support.web_routes import compile_route

from tradingview_zy.tv_storage import (
    TVStorageFieldError,
    resolve_storage_owner,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DEMO = ROOT / "src/tradingview_zy/config.py.demo"


def _route(name: str, namespace: dict):
    return compile_route(name, namespace)


class FakeArgs(dict):
    def get(self, key, default=None):
        return super().get(key, default)


def _request(*, method="GET", args=None, form=None):
    return SimpleNamespace(
        method=method,
        args=FakeArgs(args or {}),
        form=form or {},
        get_json=lambda silent=True: None,
    )


def test_request_user_is_validated_but_never_becomes_database_owner() -> None:
    assert resolve_storage_owner(" client ", "999", "session-user") == (
        "client",
        "session-user",
    )
    assert resolve_storage_owner("client", "forged-other-user", "session-user") == (
        "client",
        "session-user",
    )
    with pytest.raises(TVStorageFieldError):
        resolve_storage_owner("client", "bad\nuser", "session-user")
    with pytest.raises(TVStorageFieldError):
        resolve_storage_owner("client", "999", "")


def test_all_three_real_routes_bind_database_calls_to_current_user() -> None:
    principal = SimpleNamespace(get_id=lambda: "session-user")
    calls: list[tuple] = []
    policy = SimpleNamespace()

    chart_db = SimpleNamespace(
        tv_storage_policy=policy,
        tv_chart_list=lambda *args: calls.append(("charts", *args)) or [],
    )
    charts = _route(
        "tv_charts",
        {
            "request": _request(args={"client": "client-a", "user": "forged"}),
            "current_user": principal,
            "db": chart_db,
            "resolve_storage_owner": resolve_storage_owner,
            "TVStorageError": Exception,
        },
    )
    assert charts("1.1") == {"status": "ok", "data": []}

    template_db = SimpleNamespace(
        tv_storage_policy=policy,
        tv_chart_list=lambda *args: calls.append(("templates", *args)) or [],
    )
    templates = _route(
        "tv_study_templates",
        {
            "request": _request(args={"client": "client-b", "user": "another"}),
            "current_user": principal,
            "db": template_db,
            "resolve_storage_owner": resolve_storage_owner,
            "TVStorageError": Exception,
        },
    )
    assert templates("1.1") == {"status": "ok", "data": []}

    drawing_db = SimpleNamespace(
        tv_storage_policy=policy,
        tv_drawing_get=lambda *args: calls.append(("drawing", *args)) or "state",
    )
    drawings = _route(
        "tv_drawings",
        {
            "request": _request(
                args={
                    "client": "client-c",
                    "user": "attacker-selected",
                    "layout": "layout",
                    "chart": "chart",
                    "symbol": "a:1",
                }
            ),
            "current_user": principal,
            "db": drawing_db,
            "resolve_storage_owner": resolve_storage_owner,
            "TVStorageError": Exception,
        },
    )
    assert drawings("1.1") == {"status": "ok", "data": {"state": "state"}}

    assert calls == [
        ("charts", "chart", "client-a", "session-user"),
        ("templates", "template", "client-b", "session-user"),
        ("drawing", "client-c", "session-user", "layout", "chart", "a:1"),
    ]


@contextmanager
def _isolated_db(tmp_path: Path):
    module_names = ("tradingview_zy.db", "tradingview_zy.fun", "tradingview_zy.config")
    original_modules = {name: sys.modules.get(name) for name in module_names}
    package = importlib.import_module("tradingview_zy")
    original_config = getattr(package, "config", None)

    try:
        for name in module_names:
            sys.modules.pop(name, None)
        tzlocal = types.ModuleType("tzlocal")
        tzlocal.get_localzone = lambda: timezone.utc
        sys.modules["tzlocal"] = tzlocal

        config = types.ModuleType("tradingview_zy.config")
        config.DB_TYPE = "sqlite"
        config.DB_DATABASE = "me01"
        config.DB_HOST = "127.0.0.1"
        config.DB_PORT = 3306
        config.DB_USER = "user"
        config.DB_PWD = "password"
        config.get_data_path = lambda: tmp_path
        sys.modules["tradingview_zy.config"] = config
        package.config = config

        module = importlib.import_module("tradingview_zy.db")
        yield module
        module.db.engine.dispose()
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        for name, module in original_modules.items():
            if module is not None:
                sys.modules[name] = module
        if original_config is None:
            try:
                delattr(package, "config")
            except AttributeError:
                pass
        else:
            package.config = original_config


def test_legacy_owner_migration_is_allowlisted_deduplicated_and_idempotent(tmp_path) -> None:
    with _isolated_db(tmp_path) as module:
        legacy_chart = module.db.tv_chart_save(
            "chart", "client", "999", "same", "legacy-new", "A", "D"
        )
        authenticated_chart = module.db.tv_chart_save(
            "chart", "client", "session-user", "same", "authenticated-old", "A", "D"
        )
        module.db.tv_chart_save(
            "template", "client", "999", "legacy-only", "template", "", ""
        )
        module.db.tv_chart_save(
            "chart", "client", "unknown-owner", "same", "unknown", "A", "D"
        )

        module.db.tv_drawing_save_or_update(
            "client", "999", "layout", "chart", "a:1", "legacy-old"
        )
        module.db.tv_drawing_save_or_update(
            "client", "session-user", "layout", "chart", "a:1", "auth-new"
        )
        module.db.tv_drawing_save_or_update(
            "client", "unknown-owner", "layout", "chart", "a:1", "unknown"
        )

        with module.db.Session() as session:
            session.query(module.TableByTVCharts).filter(
                module.TableByTVCharts.id == legacy_chart
            ).update({"timestamp": 30})
            session.query(module.TableByTVCharts).filter(
                module.TableByTVCharts.id == authenticated_chart
            ).update({"timestamp": 10})
            drawings = session.query(module.TableByTVDrawings).filter(
                module.TableByTVDrawings.client_id == "client",
                module.TableByTVDrawings.layout_id == "layout",
                module.TableByTVDrawings.chart_id == "chart",
            ).all()
            for drawing in drawings:
                if drawing.user_id == "999":
                    drawing.timestamp = 10
                elif drawing.user_id == "session-user":
                    drawing.timestamp = 30
            session.commit()

        result = module.db.migrate_tv_storage_legacy_owners(
            "session-user", ["999"]
        )
        assert result == {
            "charts_moved": 2,
            "drawings_moved": 0,
            "records_deleted": 2,
        }

        charts = module.db.tv_chart_list("chart", "client", "session-user")
        assert [(row.name, row.content) for row in charts] == [("same", "legacy-new")]
        templates = module.db.tv_chart_list("template", "client", "session-user")
        assert [(row.name, row.content) for row in templates] == [
            ("legacy-only", "template")
        ]
        assert module.db.tv_chart_list("chart", "client", "999") == []
        assert [
            row.content
            for row in module.db.tv_chart_list("chart", "client", "unknown-owner")
        ] == ["unknown"]

        assert (
            module.db.tv_drawing_get(
                "client", "session-user", "layout", "chart", "a:1"
            )
            == "auth-new"
        )
        assert module.db.tv_drawing_get("client", "999", "layout", "chart", "a:1") is None
        assert (
            module.db.tv_drawing_get(
                "client", "unknown-owner", "layout", "chart", "a:1"
            )
            == "unknown"
        )

        with module.db.Session() as session:
            owner_ids = {
                row.user_id
                for row in session.query(module.TableByTVStorageOwner).filter(
                    module.TableByTVStorageOwner.client_id == "client"
                )
            }
        assert owner_ids == {"session-user", "unknown-owner"}

        assert module.db.migrate_tv_storage_legacy_owners(
            "session-user", ["999"]
        ) == {
            "charts_moved": 0,
            "drawings_moved": 0,
            "records_deleted": 0,
        }


def test_config_and_startup_migration_are_explicit() -> None:
    config_source = CONFIG_DEMO.read_text(encoding="utf-8")
    factory_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
    ).read_text(encoding="utf-8")
    auth_source = (
        ROOT / "web/tradingview_zy_chart/cl_app/blueprints/auth.py"
    ).read_text(encoding="utf-8")
    assert "WEB_AUTH_PRINCIPAL = 'tradingview_zy'" in config_source
    assert "TV_STORAGE_LEGACY_USER_IDS = ['999']" in config_source
    assert "db.migrate_tv_storage_legacy_owners(" in factory_source
    assert "LoginUser(services.storage_principal)" in auth_source
    assert "user_id == services.storage_principal" in auth_source
