"""Feature blueprints for the TradingView web application."""
from __future__ import annotations

from .auth import auth_bp, init_auth
from .core import core_bp
from .pages import pages_bp
from .settings import settings_bp
from .storage import storage_bp
from .tasks import tasks_bp
from .udf import udf_bp
from .watchlist import watchlist_bp

BLUEPRINTS = (
    core_bp,
    auth_bp,
    pages_bp,
    udf_bp,
    storage_bp,
    watchlist_bp,
    tasks_bp,
    settings_bp,
)


def register_blueprints(app) -> None:
    init_auth(app)
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
