import ast
from datetime import timedelta
from pathlib import Path
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _project_config():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_dependency_ranges_bound_known_warning_sources_everywhere():
    dependencies = _project_config()["project"]["dependencies"]
    assert "flask-login>=0.6.3,<0.7" in dependencies
    assert "tornado>=6.5.1,<7" in dependencies

    requirements = set(
        (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    )
    assert "flask-login>=0.6.3,<0.7" in requirements
    assert "tornado>=6.5.1,<7" in requirements

    lock = (ROOT / "uv.lock").read_text(encoding="utf-8")
    assert '{ name = "flask-login", specifier = ">=0.6.3,<0.7" },' in lock
    assert '{ name = "tornado", specifier = ">=6.5.1,<7" },' in lock


def test_pytest_rejects_unexpected_warnings_and_tracks_only_flask_login():
    filters = _project_config()["tool"]["pytest"]["ini_options"]["filterwarnings"]
    assert filters[0] == "error"
    assert filters[1].startswith(
        r"ignore:datetime\.datetime\.utcnow\(\) is deprecated"
    )
    assert filters[1].endswith(
        r":DeprecationWarning:flask_login\.login_manager"
    )
    assert len(filters) == 2


def test_known_flask_login_warning_is_scoped_by_pytest_filter():
    pytest.importorskip("flask")
    pytest.importorskip("flask_login")
    from flask import Flask
    from flask_login import LoginManager, UserMixin, login_user

    class User(UserMixin):
        id = "pytest-warning-policy-user"

    app = Flask(__name__)
    app.config.update(SECRET_KEY="pytest-warning-policy-secret", TESTING=True)
    LoginManager(app)

    @app.get("/")
    def remember_login():
        login_user(User(), remember=True, duration=timedelta(days=1))
        return "ok"

    response = app.test_client().get("/")
    assert response.status_code == 200
    assert "remember_token=" in "\n".join(response.headers.getlist("Set-Cookie"))


def test_tornado_entrypoint_runs_inside_asyncio_and_avoids_legacy_ioloop_api():
    source = (
        ROOT / "web" / "tradingview_zy_chart" / "app.py"
    ).read_text(encoding="utf-8")

    assert "asyncio.run(serve_forever())" in source
    assert "await asyncio.Event().wait()" in source
    assert "await server.close_all_connections()" in source
    assert "IOLoop.instance" not in source
    assert "IOLoop.current" not in source


def test_optional_pyfolio_import_is_limited_to_the_report_method():
    source = (
        ROOT / "src" / "tradingview_zy" / "backtesting" / "backtest.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_imports = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "pyfolio" not in top_level_imports

    report_method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "result_by_pyfolio"
    )
    local_imports = {
        alias.name
        for node in ast.walk(report_method)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "pyfolio" in local_imports
