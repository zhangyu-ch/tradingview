import importlib

from flask import Flask

from tradingview_zy import config, fun
from tradingview_zy.config import get_data_path
from tradingview_zy.db import db
from tradingview_zy.exchange import get_exchange
from tradingview_zy.footprint import TTLCache
from tradingview_zy.history_request_tracker import HistoryRequestTracker
from tradingview_zy.market_metadata import (
    default_market_value,
    market_catalog,
    market_default_codes,
    market_frequencies,
)
from tradingview_zy.scheduler_runtime import SchedulerStatusStore
from tradingview_zy.secret_store import ManagedSecretStore
from tradingview_zy.tick_request import BoundedProviderCaller, SlidingWindowLimiter
from tradingview_zy.tv_storage import (
    normalize_legacy_owner_ids,
    normalize_storage_principal,
)
from tradingview_zy.web_security import (
    LoginAttemptLimiter,
    is_loopback_host,
    resolve_login_credentials,
    resolve_web_secret_key,
    validate_web_access,
)
from tradingview_zy.zixuan import ZiXuan

from .blueprints import register_blueprints
from .stocks_bkgn import StocksBKGN
from .web_services import WebAppServices, install_web_services


def create_app(test_config=None):
    security_overrides = test_config or {}
    web_host = str(
        security_overrides.get(
            "WEB_HOST", getattr(config, "WEB_HOST", "127.0.0.1")
        )
    )
    login_password, login_password_hash = resolve_login_credentials(
        config, security_overrides
    )
    validate_web_access(web_host, login_password, login_password_hash)

    configured_secret = str(
        security_overrides.get(
            "WEB_SECRET_KEY", getattr(config, "WEB_SECRET_KEY", "")
        )
        or ""
    )
    web_secret_key = resolve_web_secret_key(get_data_path(), configured_secret)
    remember_days = int(
        security_overrides.get(
            "WEB_REMEMBER_DAYS", getattr(config, "WEB_REMEMBER_DAYS", 30)
        )
    )
    cookie_secure = bool(
        security_overrides.get(
            "WEB_COOKIE_SECURE", getattr(config, "WEB_COOKIE_SECURE", False)
        )
    )
    csrf_trusted_origins = security_overrides.get(
        "WEB_CSRF_TRUSTED_ORIGINS",
        getattr(config, "WEB_CSRF_TRUSTED_ORIGINS", ()),
    )
    if isinstance(csrf_trusted_origins, str):
        csrf_trusted_origins = tuple(
            value.strip()
            for value in csrf_trusted_origins.split(",")
            if value.strip()
        )
    else:
        csrf_trusted_origins = tuple(csrf_trusted_origins or ())

    max_upload_bytes = int(
        security_overrides.get(
            "WEB_MAX_UPLOAD_BYTES",
            getattr(config, "WEB_MAX_UPLOAD_BYTES", 1_048_576),
        )
    )
    max_watchlist_lines = int(
        security_overrides.get(
            "WEB_MAX_WATCHLIST_IMPORT_LINES",
            getattr(config, "WEB_MAX_WATCHLIST_IMPORT_LINES", 5_000),
        )
    )
    max_watchlist_line_bytes = int(
        security_overrides.get(
            "WEB_MAX_WATCHLIST_LINE_BYTES",
            getattr(config, "WEB_MAX_WATCHLIST_LINE_BYTES", 512),
        )
    )

    tick_rate_limiter = SlidingWindowLimiter(
        max_requests=int(
            security_overrides.get(
                "WEB_TICKS_RATE_LIMIT",
                getattr(config, "WEB_TICKS_RATE_LIMIT", 30),
            )
        ),
        window_seconds=float(
            security_overrides.get(
                "WEB_TICKS_RATE_WINDOW_SECONDS",
                getattr(config, "WEB_TICKS_RATE_WINDOW_SECONDS", 60),
            )
        ),
        max_keys=int(
            security_overrides.get(
                "WEB_TICKS_RATE_MAX_KEYS",
                getattr(config, "WEB_TICKS_RATE_MAX_KEYS", 1024),
            )
        ),
    )
    tick_provider_caller = BoundedProviderCaller(
        max_concurrent=int(
            security_overrides.get(
                "WEB_TICKS_PROVIDER_MAX_CONCURRENT",
                getattr(config, "WEB_TICKS_PROVIDER_MAX_CONCURRENT", 8),
            )
        ),
        timeout_seconds=float(
            security_overrides.get(
                "WEB_TICKS_PROVIDER_TIMEOUT_SECONDS",
                getattr(config, "WEB_TICKS_PROVIDER_TIMEOUT_SECONDS", 5),
            )
        ),
    )
    login_limiter = LoginAttemptLimiter(
        max_attempts=int(
            security_overrides.get(
                "WEB_MAX_LOGIN_ATTEMPTS",
                getattr(config, "WEB_MAX_LOGIN_ATTEMPTS", 5),
            )
        ),
        window_seconds=int(
            security_overrides.get(
                "WEB_LOGIN_ATTEMPT_WINDOW_SECONDS",
                getattr(config, "WEB_LOGIN_ATTEMPT_WINDOW_SECONDS", 300),
            )
        ),
    )
    history_request_tracker = HistoryRequestTracker(
        max_entries=int(
            security_overrides.get(
                "WEB_HISTORY_TRACKER_MAX_ENTRIES",
                getattr(config, "WEB_HISTORY_TRACKER_MAX_ENTRIES", 4_096),
            )
        ),
        entry_ttl_seconds=float(
            security_overrides.get(
                "WEB_HISTORY_TRACKER_TTL_SECONDS",
                getattr(config, "WEB_HISTORY_TRACKER_TTL_SECONDS", 900),
            )
        ),
        burst_window_seconds=float(
            security_overrides.get(
                "WEB_HISTORY_BURST_WINDOW_SECONDS",
                getattr(config, "WEB_HISTORY_BURST_WINDOW_SECONDS", 5),
            )
        ),
        max_requests_per_window=int(
            security_overrides.get(
                "WEB_HISTORY_MAX_REQUESTS_PER_WINDOW",
                getattr(config, "WEB_HISTORY_MAX_REQUESTS_PER_WINDOW", 6),
            )
        ),
    )
    scheduler_status_store = SchedulerStatusStore()

    frequency_maps = {
        "10s": "10S",
        "30s": "30S",
        "1m": "1",
        "2m": "2",
        "3m": "3",
        "5m": "5",
        "10m": "10",
        "15m": "15",
        "30m": "30",
        "60m": "60",
        "120m": "120",
        "3h": "180",
        "4h": "240",
        "d": "1D",
        "2d": "2D",
        "w": "1W",
        "m": "1M",
        "y": "12M",
    }
    resolution_maps = dict(zip(frequency_maps.values(), frequency_maps.keys()))
    market_frequency_map = market_frequencies()
    market_default_code_map = market_default_codes()
    market_catalog_items = market_catalog()
    default_market_key = default_market_value()
    logger = fun.get_logger()

    def unavailable_task_message():
        return "监控/选股任务将在策略接入后可用：旧缠论依赖已移除"

    removed_legacy_module_prefixes = (
        "tradingview_zy.cl",
        "tradingview_zy.kcharts",
        "tradingview_zy.monitor",
        "tradingview_zy.xuangu",
    )
    removed_legacy_import_names = (
        "cl",
        "cl_interface",
        "cl_utils",
        "kcharts",
        "monitor",
        "xuangu",
    )

    def is_removed_legacy_import_error(error: ImportError):
        missing_name = getattr(error, "name", None) or ""
        if any(
            missing_name == prefix or missing_name.startswith(f"{prefix}.")
            for prefix in removed_legacy_module_prefixes
        ):
            return True
        message = str(error)
        if any(prefix in message for prefix in removed_legacy_module_prefixes):
            return True
        return missing_name == "tradingview_zy" and any(
            f"'{import_name}'" in message
            for import_name in removed_legacy_import_names
        )

    class UnavailableTasks:
        def __init__(self, module_name: str, error: ImportError):
            self.module_name = module_name
            self.error = error

        def __getattr__(self, name):
            raise RuntimeError(unavailable_task_message()) from self.error

    class LazyTasks:
        def __init__(self, module_name: str, class_name: str, on_load=None):
            self.module_name = module_name
            self.class_name = class_name
            self.on_load = on_load
            self._task_obj = None
            self._task_error = None

        @property
        def error(self):
            return self._task_error

        def _load(self):
            if self._task_obj is not None or self._task_error is not None:
                return self._task_obj
            task_cls, task_error = load_task_class(
                self.module_name, self.class_name
            )
            if task_error is not None:
                self._task_error = task_error
                return None
            self._task_obj = task_cls(None)
            if self.on_load is not None:
                self.on_load(self._task_obj)
            return self._task_obj

        def __getattr__(self, name):
            task_obj = self._load()
            if task_obj is None:
                raise RuntimeError(unavailable_task_message()) from self._task_error
            return getattr(task_obj, name)

    def load_task_class(module_name: str, class_name: str):
        try:
            module = importlib.import_module(f"{__package__}.{module_name}")
            return getattr(module, class_name), None
        except (ImportError, ModuleNotFoundError) as error:
            if is_removed_legacy_import_error(error):
                logger.warning(
                    "%s 依赖的旧缠论模块已移除，任务将在策略接入后可用：%s",
                    module_name,
                    error,
                )
                return None, error
            logger.exception("%s 导入异常", module_name)
            raise

    def task_error_response(error: Exception | None = None):
        message = unavailable_task_message()
        if error is not None:
            message = f"{message}：{error}"
        return {"ok": False, "msg": message}

    alert_tasks = LazyTasks("alert_tasks", "AlertTasks")
    xuangu_tasks = LazyTasks("xuangu_tasks", "XuanguTasks")

    def guard_task(task_obj):
        if isinstance(task_obj, UnavailableTasks):
            return task_error_response(task_obj.error)
        if isinstance(task_obj, LazyTasks):
            task_obj._load()
            if task_obj.error is not None:
                return task_error_response(task_obj.error)
        return None

    app = Flask(__name__, instance_relative_config=True)
    app.extensions["scheduler_mode"] = "external-process"
    app.extensions["history_request_tracker"] = history_request_tracker
    if test_config:
        app.config.update(test_config)
    app.config.update(
        SECRET_KEY=web_secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=cookie_secure,
        MAX_CONTENT_LENGTH=max_upload_bytes,
    )
    app.logger.addFilter(
        lambda record: "/static/" not in record.getMessage().lower()
    )

    storage_principal = normalize_storage_principal(
        security_overrides.get(
            "WEB_AUTH_PRINCIPAL",
            getattr(config, "WEB_AUTH_PRINCIPAL", "tradingview_zy"),
        )
    )
    storage_legacy_owner_ids = normalize_legacy_owner_ids(
        security_overrides.get(
            "TV_STORAGE_LEGACY_USER_IDS",
            getattr(config, "TV_STORAGE_LEGACY_USER_IDS", ()),
        ),
        authenticated_principal=storage_principal,
    )
    db.migrate_tv_storage_legacy_owners(
        storage_principal, storage_legacy_owner_ids
    )
    auto_login = (
        login_password == ""
        and login_password_hash == ""
        and is_loopback_host(web_host)
    )

    services = WebAppServices.create(
        web_host=web_host,
        login_password=login_password,
        login_password_hash=login_password_hash,
        remember_days=remember_days,
        auto_login=auto_login,
        csrf_trusted_origins=csrf_trusted_origins,
        login_limiter=login_limiter,
        storage_principal=storage_principal,
        max_upload_bytes=max_upload_bytes,
        max_watchlist_lines=max_watchlist_lines,
        max_watchlist_line_bytes=max_watchlist_line_bytes,
        tick_rate_limiter=tick_rate_limiter,
        tick_provider_caller=tick_provider_caller,
        scheduler_status_store=scheduler_status_store,
        history_request_tracker=history_request_tracker,
        footprint_cache=TTLCache(ttl_seconds=10.0),
        frequency_maps=frequency_maps,
        resolution_maps=resolution_maps,
        market_frequencies=market_frequency_map,
        market_default_codes=market_default_code_map,
        market_catalog=market_catalog_items,
        default_market=default_market_key,
        logger=logger,
        alert_tasks=alert_tasks,
        xuangu_tasks=xuangu_tasks,
        guard_task=guard_task,
        security_overrides=security_overrides,
        database=db,
        get_exchange=get_exchange,
        config=config,
        fun=fun,
        zixuan_factory=ZiXuan,
        stocks_bkgn_factory=StocksBKGN,
        secret_store_factory=ManagedSecretStore,
        get_data_path=get_data_path,
    )
    install_web_services(app, services)
    register_blueprints(app)
    return app
