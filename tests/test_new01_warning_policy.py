from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _project_config():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_dependency_ranges_bound_known_warning_sources():
    dependencies = _project_config()["project"]["dependencies"]
    assert "flask-login>=0.6.3,<0.7" in dependencies
    assert "tornado>=6.5.1,<7" in dependencies


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


def test_tornado_entrypoint_runs_inside_asyncio_and_avoids_legacy_ioloop_api():
    source = (
        ROOT / "web" / "tradingview_zy_chart" / "app.py"
    ).read_text(encoding="utf-8")

    assert "asyncio.run(serve_forever())" in source
    assert "await asyncio.Event().wait()" in source
    assert "IOLoop.instance" not in source
    assert "IOLoop.current" not in source
