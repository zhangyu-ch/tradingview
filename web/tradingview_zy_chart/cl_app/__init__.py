import datetime
import json
import os
import time
import traceback
import uuid
import importlib
from io import BytesIO

import pinyin
import pytz
from apscheduler.events import (
    EVENT_ALL,
    EVENT_EXECUTOR_ADDED,
    EVENT_EXECUTOR_REMOVED,
    EVENT_JOB_ADDED,
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
    EVENT_JOB_MODIFIED,
    EVENT_JOB_REMOVED,
    EVENT_JOB_SUBMITTED,
    EVENT_JOBSTORE_ADDED,
    EVENT_JOBSTORE_REMOVED,
)
from apscheduler.executors.tornado import TornadoExecutor
from apscheduler.schedulers.tornado import TornadoScheduler
from flask import Flask, redirect, render_template, request, send_file, session
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from tzlocal import get_localzone

from tradingview_zy import config, fun
from tradingview_zy.base import Market
from tradingview_zy.config import get_data_path
from tradingview_zy.db import db
from tradingview_zy.exchange import get_exchange
from tradingview_zy.exchange.stocks_bkgn import StocksBKGN
from tradingview_zy.footprint import SUB_FREQUENCY_MAP, TTLCache, aggregate_footprint
from tradingview_zy.market_metadata import market_default_codes, market_frequencies
from tradingview_zy.web_payloads import (
    datetime_to_timestamp_seconds,
    filter_klines_by_timestamp_range,
    klines_to_tv_history,
    normalize_klines_for_market,
)
from tradingview_zy.zixuan import ZiXuan
from tradingview_zy.strategies.loader import (
    StrategyRegistryError,
    find_registered_strategy_id_by_path,
    registered_strategy_choices,
    validate_registered_strategy,
)
from tradingview_zy.web_security import (
    LoginAttemptLimiter,
    get_csrf_token,
    is_loopback_host,
    resolve_login_credentials,
    resolve_web_secret_key,
    rotate_csrf_token,
    validate_csrf_request,
    validate_web_access,
    verify_login_password,
)
from tradingview_zy.watchlist_transfer import (
    WatchlistTransferError,
    export_watchlist_text,
    parse_watchlist_stream,
)
from tradingview_zy.web_api_validation import (
    WebParameterError,
    parse_bounded_text,
    parse_positive_int,
)
from tradingview_zy.settings_security import (
    feishu_secret_is_configured,
    merge_feishu_settings,
)
from tradingview_zy.tick_request import (
    BoundedProviderCaller,
    SlidingWindowLimiter,
    TickProviderBusyError,
    TickProviderCallError,
    TickProviderTimeoutError,
    TickRateLimitError,
    TickRequestError,
    parse_tick_request,
)


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
            value.strip() for value in csrf_trusted_origins.split(",") if value.strip()
        )
    else:
        csrf_trusted_origins = tuple(csrf_trusted_origins or ())

    max_upload_bytes = int(
        security_overrides.get(
            "WEB_MAX_UPLOAD_BYTES", getattr(config, "WEB_MAX_UPLOAD_BYTES", 1_048_576)
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
        max_requests=int(security_overrides.get("WEB_TICKS_RATE_LIMIT", getattr(config, "WEB_TICKS_RATE_LIMIT", 30))),
        window_seconds=float(security_overrides.get("WEB_TICKS_RATE_WINDOW_SECONDS", getattr(config, "WEB_TICKS_RATE_WINDOW_SECONDS", 60))),
        max_keys=int(security_overrides.get("WEB_TICKS_RATE_MAX_KEYS", getattr(config, "WEB_TICKS_RATE_MAX_KEYS", 1024))),
    )
    tick_provider_caller = BoundedProviderCaller(
        max_concurrent=int(security_overrides.get("WEB_TICKS_PROVIDER_MAX_CONCURRENT", getattr(config, "WEB_TICKS_PROVIDER_MAX_CONCURRENT", 8))),
        timeout_seconds=float(security_overrides.get("WEB_TICKS_PROVIDER_TIMEOUT_SECONDS", getattr(config, "WEB_TICKS_PROVIDER_TIMEOUT_SECONDS", 5))),
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

    # 任务对象
    scheduler = TornadoScheduler(timezone=pytz.timezone("Asia/Shanghai"))
    scheduler.add_executor(TornadoExecutor())
    scheduler.my_task_list = {}

    def run_tasks_listener(event):
        state_map = {
            EVENT_EXECUTOR_ADDED: "已添加",
            EVENT_EXECUTOR_REMOVED: "删除调度",
            EVENT_JOBSTORE_ADDED: "已添加",
            EVENT_JOBSTORE_REMOVED: "删除存储",
            EVENT_JOB_ADDED: "已添加",
            EVENT_JOB_REMOVED: "删除作业",
            EVENT_JOB_MODIFIED: "修改作业",
            EVENT_JOB_SUBMITTED: "运行中",
            EVENT_JOB_MAX_INSTANCES: "等待运行",
            EVENT_JOB_EXECUTED: "已完成",
            EVENT_JOB_ERROR: "执行异常",
            EVENT_JOB_MISSED: "未执行",
        }
        if event.code not in state_map.keys():
            return
        if hasattr(event, "job_id"):
            job_id = event.job_id
            if job_id not in scheduler.my_task_list.keys():
                scheduler.my_task_list[job_id] = {
                    "id": job_id,
                    "name": "--",
                    "update_dt": fun.datetime_to_str(datetime.datetime.now()),
                    "next_run_dt": "--",
                    "state": "未知",
                }
            scheduler.my_task_list[job_id]["update_dt"] = fun.datetime_to_str(
                datetime.datetime.now()
            )
            job = scheduler.get_job(event.job_id)
            if job is not None:
                scheduler.my_task_list[job_id]["name"] = job.name
                scheduler.my_task_list[job_id]["next_run_dt"] = fun.datetime_to_str(
                    job.next_run_time
                )
            scheduler.my_task_list[job_id]["state"] = state_map[event.code]
            # print('任务更新', task_list[job_id])
        return

    scheduler.add_listener(run_tasks_listener, EVENT_ALL)
    scheduler.start()

    # 项目中的周期与 tv 的周期对应表
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

    # Web 元数据来自无副作用静态注册表；provider 仅在具体请求时惰性构造。
    market_frequencys = market_frequencies()
    market_default_codes = market_default_codes()

    # 各个市场的交易时间
    market_session = {
        "a": "24x7",
        "hk": "24x7",
        "fx": "24x7",
        "us": "24x7",
        "futures": "24x7",
        "ny_futures": "24x7",
        "currency": "24x7",
        "currency_spot": "24x7",
    }

    # 各个交易所的时区 统一时区
    market_timezone = {
        "a": "Asia/Shanghai",
        "hk": "Asia/Shanghai",
        "fx": "Asia/Shanghai",
        "us": "America/New_York",
        "futures": "Asia/Shanghai",
        "ny_futures": "Asia/Shanghai",
        "currency": str(get_localzone()),
        "currency_spot": str(get_localzone()),
    }

    market_types = {
        "a": "stock",
        "hk": "stock",
        "fx": "stock",
        "us": "stock",
        "futures": "futures",
        "ny_futures": "futures",
        "currency": "crypto",
        "currency_spot": "crypto",
    }

    # 记录请求次数，超过则返回 no_data
    __history_req_counter = {}

    __log = fun.get_logger()

    def _unavailable_task_message():
        return "监控/选股任务将在策略接入后可用：旧缠论依赖已移除"

    _REMOVED_LEGACY_MODULE_PREFIXES = (
        "tradingview_zy.cl",
        "tradingview_zy.kcharts",
        "tradingview_zy.monitor",
        "tradingview_zy.xuangu",
    )
    _REMOVED_LEGACY_IMPORT_NAMES = ("cl", "cl_interface", "cl_utils", "kcharts", "monitor", "xuangu")

    def _is_removed_legacy_import_error(error: ImportError):
        missing_name = getattr(error, "name", None) or ""
        if any(
            missing_name == prefix or missing_name.startswith(f"{prefix}.")
            for prefix in _REMOVED_LEGACY_MODULE_PREFIXES
        ):
            return True

        message = str(error)
        if any(prefix in message for prefix in _REMOVED_LEGACY_MODULE_PREFIXES):
            return True
        return missing_name == "tradingview_zy" and any(
            f"'{import_name}'" in message for import_name in _REMOVED_LEGACY_IMPORT_NAMES
        )

    class _UnavailableTasks:
        def __init__(self, module_name: str, error: ImportError):
            self.module_name = module_name
            self.error = error

        def __getattr__(self, name):
            raise RuntimeError(_unavailable_task_message()) from self.error

    class _LazyTasks:
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

            task_cls, task_error = _load_task_class(self.module_name, self.class_name)
            if task_error is not None:
                self._task_error = task_error
                return None

            self._task_obj = task_cls(scheduler)
            if self.on_load is not None:
                self.on_load(self._task_obj)
            return self._task_obj

        def __getattr__(self, name):
            task_obj = self._load()
            if task_obj is None:
                raise RuntimeError(_unavailable_task_message()) from self._task_error
            return getattr(task_obj, name)

    def _load_task_class(module_name: str, class_name: str):
        try:
            module = importlib.import_module(f"{__package__}.{module_name}")
            return getattr(module, class_name), None
        except (ImportError, ModuleNotFoundError) as e:
            if _is_removed_legacy_import_error(e):
                __log.warning(
                    "%s 依赖的旧缠论模块已移除，任务将在策略接入后可用：%s",
                    module_name,
                    e,
                )
                return None, e
            __log.exception("%s 导入异常", module_name)
            raise

    def _task_error_response(error: Exception = None):
        msg = _unavailable_task_message()
        if error is not None:
            msg = f"{msg}：{error}"
        return {"ok": False, "msg": msg}

    _alert_tasks = _LazyTasks("alert_tasks", "AlertTasks", lambda task: task.run())
    _xuangu_tasks = _LazyTasks("xuangu_tasks", "XuanguTasks")
    _other_tasks = _LazyTasks("other_tasks", "OtherTasks")

    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    if test_config:
        app.config.update(test_config)
    # Security-critical values are derived from the dedicated WEB_* settings above and
    # cannot be weakened accidentally by a generic Flask config override.
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
    )  # 过滤静态资源请求日志

    login_manager = LoginManager()
    login_manager.session_protection = "basic"
    login_manager.init_app(app)
    login_manager.login_view = "login_opt"

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": lambda: get_csrf_token(session)}

    @app.before_request
    def protect_unsafe_requests():
        valid, reason = validate_csrf_request(
            request, session, trusted_origins=csrf_trusted_origins
        )
        if valid:
            return None
        app.logger.warning(
            "CSRF request rejected endpoint=%s reason=%s", request.endpoint, reason
        )
        return {
            "ok": False,
            "error": "csrf_failed",
            "msg": "请求安全校验失败，请刷新页面后重试",
        }, 403

    class LoginUser(UserMixin):
        user_id = "tradingview_zy"

        def __init__(self) -> None:
            super().__init__()
            self.id = self.user_id

    @login_manager.user_loader
    def load_user(user_id):
        return LoginUser() if user_id == LoginUser.user_id else None

    auto_login = (
        login_password == ""
        and login_password_hash == ""
        and is_loopback_host(web_host)
    )

    @app.route("/login", methods=["GET", "POST"])
    def login_opt():
        if auto_login:
            login_user(LoginUser(), remember=False)
            return redirect("/")

        emsg = ""
        if request.method == "POST":
            remote_key = request.remote_addr or "unknown"
            if not login_limiter.is_allowed(remote_key):
                return render_template(
                    "login.html", emsg="登录失败次数过多，请稍后再试"
                ), 429

            password = request.form.get("password")
            if verify_login_password(password, login_password, login_password_hash):
                login_limiter.reset(remote_key)
                login_user(
                    LoginUser(),
                    remember=remember_days > 0,
                    duration=datetime.timedelta(days=max(remember_days, 1)),
                )
                rotate_csrf_token(session)
                return redirect("/")

            login_limiter.record_failure(remote_key)
            emsg = "密码错误"

        return render_template("login.html", emsg=emsg)

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout_opt():
        logout_user()
        rotate_csrf_token(session)
        return redirect("/login")

    @app.route("/")
    @login_required
    def index_show():
        """
        首页
        """

        return render_template(
            "index.html",
            market_default_codes=market_default_codes,
            market_frequencys=market_frequencys,
        )

    @app.route("/tv/config")
    @login_required
    def tv_config():
        """
        配置项
        """
        frequencys = list(
            set(market_frequencys["a"])
            | set(market_frequencys["hk"])
            | set(market_frequencys["fx"])
            | set(market_frequencys["us"])
            | set(market_frequencys["futures"])
            | set(market_frequencys["currency"])
            | set(market_frequencys["currency_spot"])
        )
        supportedResolutions = [v for k, v in frequency_maps.items() if k in frequencys]
        return {
            "supports_search": True,
            "supports_group_request": False,
            "supported_resolutions": supportedResolutions,
            "supports_marks": True,
            "supports_timescale_marks": True,
            "supports_time": False,
            "exchanges": [
                {"value": "a", "name": "沪深", "desc": "沪深A股"},
                {"value": "hk", "name": "港股", "desc": "港股"},
                {"value": "fx", "name": "外汇", "desc": "外汇"},
                {"value": "us", "name": "美股", "desc": "美股"},
                {"value": "futures", "name": "国内期货", "desc": "国内期货"},
                {"value": "ny_futures", "name": "纽约期货", "desc": "纽约期货"},
                {
                    "value": "currency",
                    "name": "数字货币(Futures)",
                    "desc": "数字货币（合约）",
                },
                {
                    "value": "currency_spot",
                    "name": "数字货币(Spot)",
                    "desc": "数字货币（现货）",
                },
            ],
        }

    @app.route("/tv/symbol_info")
    @login_required
    def tv_symbol_info():
        """
        商品集合信息
        supports_search is True 则不会调用这个接口
        """
        group = request.args.get("group")
        ex = get_exchange(Market(group))
        all_symbols = ex.all_stocks()

        info = {
            "symbol": [s["code"] for s in all_symbols],
            "description": [s["name"] for s in all_symbols],
            "exchange-listed": group,
            "exchange-traded": group,
        }
        return info

    @app.route("/tv/symbols")
    @login_required
    def tv_symbols():
        """
        商品解析
        """
        symbol: str = request.args.get("symbol")
        symbol: list = symbol.split(":")
        market: str = symbol[0].lower()
        code: str = symbol[1]

        ex = get_exchange(Market(market))
        stocks = ex.stock_info(code)

        sector = ""
        industry = ""
        if market == "a":
            try:
                gnbk = ex.stock_owner_plate(code)
                sector = " / ".join([_g["name"] for _g in gnbk["GN"]])
                industry = " / ".join([_h["name"] for _h in gnbk["HY"]])
            except Exception:
                pass

        info = {
            "name": stocks["code"],
            "ticker": f"{market}:{stocks['code']}",
            "full_name": f"{market}:{stocks['code']}",
            "description": stocks["name"],
            "exchange": market,
            "type": market_types[market],
            "session": market_session[market],
            "timezone": market_timezone[market],
            "pricescale": (
                stocks["precision"] if "precision" in stocks.keys() else 1000
            ),
            "visible_plots_set": "ohlcv",
            "supported_resolutions": [
                v for k, v in frequency_maps.items() if k in market_frequencys[market]
            ],
            "intraday_multipliers": [
                "1",
                "2",
                "3",
                "5",
                "10",
                "15",
                "20",
                "30",
                "60",
                "120",
                "240",
            ],
            "seconds_multipliers": [
                "1",
                "2",
                "3",
                "5",
                "10",
                "15",
                "20",
                "30",
                "40",
                "50",
                "60",
            ],
            "daily_multipliers": [
                "1",
                "2",
            ],
            "minmov": 1,
            "minmov2": 0,
            "has_intraday": True,
            "has_seconds": True if market in ["futures", "ny_futures"] else False,
            "has_daily": True,
            "has_weekly_and_monthly": True,
            "sector": sector,
            "industry": industry,
        }
        return info

    @app.route("/tv/search")
    @login_required
    def tv_search():
        """
        商品检索
        """
        query = request.args.get("query")
        type = request.args.get("type")
        exchange = request.args.get("exchange")
        limit = request.args.get("limit")

        ex = get_exchange(Market(exchange))
        all_stocks = ex.all_stocks()

        if exchange in ["currency", "currency_spot"]:
            res_stocks = [
                stock for stock in all_stocks if query.lower() in stock["code"].lower()
            ]
        else:
            res_stocks = [
                stock
                for stock in all_stocks
                if query.lower() in stock["code"].lower()
                or query.lower() in stock["name"].lower()
                or query.lower()
                in "".join([pinyin.get_initial(_p)[0] for _p in stock["name"]]).lower()
            ]
        res_stocks = res_stocks[0 : int(limit)]

        infos = []
        for stock in res_stocks:
            infos.append(
                {
                    "symbol": stock["code"],
                    "name": stock["code"],
                    "full_name": f"{exchange}:{stock['code']}",
                    "description": stock["name"],
                    "exchange": exchange,
                    "ticker": f"{exchange}:{stock['code']}",
                    "type": type,
                    "session": market_session[exchange],
                    "timezone": market_timezone[exchange],
                    "supported_resolutions": [
                        v
                        for k, v in frequency_maps.items()
                        if k in market_frequencys[exchange]
                    ],
                }
            )
        return infos

    @app.route("/tv/history")
    @login_required
    def tv_history():
        """
        K线柱
        """

        symbol = request.args.get("symbol")
        resolution = request.args.get("resolution")
        firstDataRequest = request.args.get("firstDataRequest", "false")
        try:
            _from = int(request.args.get("from"))
            _to = int(request.args.get("to"))
        except (TypeError, ValueError):
            return {"s": "error", "errmsg": "invalid from/to"}

        if _from < 0 and _to < 0:
            return {"s": "no_data"}

        if resolution not in resolution_maps:
            return {"s": "error", "errmsg": "unsupported resolution"}

        _symbol_res_old_k_time_key = f"{symbol}_{resolution}"

        now_time = time.time()

        s = "ok"

        if firstDataRequest == "false":
            # 判断在 5 秒内，同一个请求大于 5 次，返回 no_data
            if _symbol_res_old_k_time_key not in __history_req_counter.keys():
                __history_req_counter[_symbol_res_old_k_time_key] = {
                    "counter": 0,
                    "tm": now_time,
                }
            else:
                if __history_req_counter[_symbol_res_old_k_time_key]["counter"] >= 5:
                    __history_req_counter[_symbol_res_old_k_time_key] = {
                        "counter": 0,
                        "tm": now_time,
                    }
                    s = "no_data"
                elif (
                    now_time - __history_req_counter[_symbol_res_old_k_time_key]["tm"]
                    <= 5
                ):
                    __history_req_counter[_symbol_res_old_k_time_key]["counter"] += 1
                    __history_req_counter[_symbol_res_old_k_time_key]["tm"] = now_time
                else:
                    __history_req_counter[_symbol_res_old_k_time_key] = {
                        "counter": 0,
                        "tm": now_time,
                    }

        market = symbol.split(":")[0].lower()
        code = symbol.split(":")[1]

        ex = get_exchange(Market(market))

        # 判断当前是否可交易时间
        if (
            firstDataRequest == "false"
            and _from >= int(now_time - (10 * 60))
            and ex.now_trading() is False
        ):
            return {"s": "no_data", "nextTime": int(now_time + (10 * 60))}

        frequency = resolution_maps[resolution]
        klines = ex.klines(code, frequency)
        if klines is None or len(klines) == 0:
            return {"s": "no_data"}

        klines = normalize_klines_for_market(klines, market)
        if _to < datetime_to_timestamp_seconds(klines.iloc[0]["date"]):
            return {"s": "no_data"}

        if firstDataRequest != "true":
            klines = filter_klines_by_timestamp_range(
                klines, _from, _to, market=market
            )
            if klines is None or len(klines) == 0:
                return {"s": "no_data"}

        return klines_to_tv_history(
            klines,
            update=False if firstDataRequest == "true" else True,
            status=s,
            market=market,
        )

    # (symbol, frequency) -> 全量足迹聚合结果，TTL 内直接复用，按请求窗口切片返回
    __footprint_cache = TTLCache(ttl_seconds=10.0)

    @app.route("/tv/footprint")
    @login_required
    def tv_footprint():
        """
        K线分价成交量（Volume Footprint），供样式 17 的足迹渲染使用
        """
        symbol = request.args.get("symbol")
        resolution = request.args.get("resolution")
        try:
            _from = int(request.args.get("from"))
            _to = int(request.args.get("to"))
        except (TypeError, ValueError):
            return {"s": "error", "errmsg": "invalid from/to"}

        if not symbol or ":" not in symbol:
            return {"s": "error", "errmsg": "invalid symbol"}
        if resolution not in resolution_maps:
            return {"s": "error", "errmsg": "unsupported resolution"}

        frequency = resolution_maps[resolution]
        sub_frequency = SUB_FREQUENCY_MAP.get(frequency)
        market = symbol.split(":")[0].lower()
        code = symbol.split(":")[1]
        ex = get_exchange(Market(market))
        if sub_frequency is None or sub_frequency not in ex.support_frequencys():
            return {"s": "no_data"}

        cache_key = (symbol, frequency)
        footprint_bars = __footprint_cache.get(cache_key)
        if footprint_bars is None:
            display_klines = ex.klines(code, frequency)
            sub_klines = ex.klines(code, sub_frequency)
            footprint_bars = aggregate_footprint(display_klines, sub_klines)
            __footprint_cache.set(cache_key, footprint_bars)

        return {
            "s": "ok",
            "bars": {ts: bar for ts, bar in footprint_bars.items() if _from <= ts <= _to},
        }

    @app.route("/tv/timescale_marks")
    @login_required
    def tv_timescale_marks():
        symbol = request.args.get("symbol")
        _from = int(request.args.get("from"))
        _to = int(request.args.get("to"))
        resolution = request.args.get("resolution")
        market = symbol.split(":")[0]
        code = symbol.split(":")[1]

        freq = resolution_maps[resolution]

        order_type_maps = {
            "buy": "买入",
            "sell": "卖出",
            "open_long": "买入开多",
            "open_short": "买入开空",
            "close_long": "卖出平多",
            "close_short": "买入平空",
        }
        marks = []

        # 增加订单的信息
        orders = db.order_query_by_code(market, code)
        for i in range(len(orders)):
            o = orders[i]
            _dt_int = fun.datetime_to_int(o["datetime"])
            if _from <= _dt_int <= _to:
                m = {
                    "id": i,
                    "time": _dt_int,
                    "color": (
                        "red"
                        if o["type"] in ["buy", "open_long", "close_short"]
                        else "green"
                    ),
                    "label": (
                        "B" if o["type"] in ["buy", "open_long", "close_short"] else "S"
                    ),
                    "tooltip": [
                        f"{order_type_maps[o['type']]}[{o['price']}/{o['amount']}]",
                        f"{'' if 'info' not in o else o['info']}",
                    ],
                    "shape": (
                        "earningUp"
                        if o["type"] in ["buy", "open_long", "close_short"]
                        else "earningDown"
                    ),
                }
                marks.append(m)

        # 增加其他自定义信息
        other_marks = db.marks_query(market, code)
        for i in range(len(other_marks)):
            _m = other_marks[i]
            if _m.frequency == "" or _m.frequency == freq:
                if _from <= _m.mark_time <= _to:
                    marks.append(
                        {
                            "id": f"m-{i}",
                            "time": int(_m.mark_time),
                            "color": _m.mark_color,
                            "label": _m.mark_label,
                            "tooltip": _m.mark_tooltip,
                            "shape": _m.mark_shape,
                        }
                    )

        return marks

    @app.route("/tv/marks")
    @login_required
    def tv_marks():
        symbol = request.args.get("symbol")
        _from = int(request.args.get("from"))
        _to = int(request.args.get("to"))
        resolution = request.args.get("resolution")
        market = symbol.split(":")[0]
        code = symbol.split(":")[1]

        freq = resolution_maps[resolution]

        marks = []
        price_marks = db.marks_query_by_price(market, code, start_date=_from)
        for i in range(len(price_marks)):
            _m = price_marks[i]
            if _m.frequency == "" or _m.frequency == freq:
                if _from <= _m.mark_time <= _to:
                    marks.append(
                        {
                            "id": f"m-{i}",
                            "time": int(_m.mark_time),
                            "color": _m.mark_color,
                            "text": _m.mark_text,
                            "label": _m.mark_label,
                            "labelFontColor": _m.mark_label_font_color,
                            "minSize": _m.mark_min_size,
                        }
                    )

        return marks

    @app.route("/tv/del_marks", methods=["POST"])
    @login_required
    def tv_del_marks():
        symbol = request.form["symbol"]
        market = symbol.split(":")[0]
        code = symbol.split(":")[1]

        db.marks_del_all_by_code(market, code)

        return {"status": "ok"}

    @app.route("/tv/time")
    @login_required
    def tv_time():
        """
        服务器时间
        """
        return fun.datetime_to_int(datetime.datetime.now())

    @app.route("/tv/<version>/charts", methods=["GET", "POST", "DELETE"])
    @login_required
    def tv_charts(version):
        """TradingView chart layout storage."""
        client_id = str(request.args.get("client"))
        user_id = str(request.args.get("user"))
        raw_chart_id = request.args.get("chart")

        if request.method == "GET":
            if raw_chart_id is None:
                chart_list = db.tv_chart_list("chart", client_id, user_id)
                return {
                    "status": "ok",
                    "data": [
                        {
                            "timestamp": chart.timestamp,
                            "symbol": chart.symbol,
                            "resolution": chart.resolution,
                            "id": chart.id,
                            "name": chart.name,
                        }
                        for chart in chart_list
                    ],
                }
            try:
                chart_id = parse_positive_int(raw_chart_id, field="chart")
            except WebParameterError as exc:
                return {"status": "error", "error": "invalid_chart_id", "message": str(exc)}, 422
            chart = db.tv_chart_get("chart", chart_id, client_id, user_id)
            if chart is None:
                return {"status": "error", "error": "chart_not_found"}, 404
            return {
                "status": "ok",
                "data": {
                    "content": chart.content,
                    "timestamp": chart.timestamp,
                    "name": chart.name,
                    "id": chart.id,
                },
            }

        if request.method == "DELETE":
            try:
                chart_id = parse_positive_int(raw_chart_id, field="chart")
            except WebParameterError as exc:
                return {"status": "error", "error": "invalid_chart_id", "message": str(exc)}, 422
            db.tv_chart_del("chart", chart_id, client_id, user_id)
            return {"status": "ok"}

        # Validate an update identifier before reading the potentially large form body.
        chart_id = None
        if raw_chart_id is not None:
            try:
                chart_id = parse_positive_int(raw_chart_id, field="chart")
            except WebParameterError as exc:
                return {"status": "error", "error": "invalid_chart_id", "message": str(exc)}, 422
        name = request.form["name"]
        content = request.form["content"]
        symbol = request.form["symbol"]
        resolution = request.form["resolution"]
        if chart_id is None:
            saved_id = db.tv_chart_save(
                "chart", client_id, user_id, name, content, symbol, resolution
            )
            return {"status": "ok", "id": saved_id}
        db.tv_chart_update(
            "chart", chart_id, client_id, user_id, name, content, symbol, resolution
        )
        return {"status": "ok"}

    @app.route("/tv/<version>/study_templates", methods=["GET", "POST", "DELETE"])
    @login_required
    def tv_study_templates(version):
        """TradingView indicator template storage."""
        client_id = str(request.args.get("client"))
        user_id = str(request.args.get("user"))

        if request.method == "GET":
            raw_name = request.args.get("template")
            if raw_name is None:
                template_list = db.tv_chart_list("template", client_id, user_id)
                return {
                    "status": "ok",
                    "data": [{"name": template.name} for template in template_list],
                }
            try:
                name = parse_bounded_text(raw_name, field="template", max_chars=200)
            except WebParameterError as exc:
                return {"status": "error", "error": "invalid_template_name", "message": str(exc)}, 422
            template = db.tv_chart_get_by_name("template", name, client_id, user_id)
            if template is None:
                return {"status": "error", "error": "template_not_found"}, 404
            return {
                "status": "ok",
                "data": {"name": template.name, "content": template.content},
            }

        if request.method == "DELETE":
            try:
                name = parse_bounded_text(
                    request.args.get("template"), field="template", max_chars=200
                )
            except WebParameterError as exc:
                return {"status": "error", "error": "invalid_template_name", "message": str(exc)}, 422
            db.tv_chart_del_by_name("template", name, client_id, user_id)
            return {"status": "ok"}

        name = request.form["name"]
        content = request.form["content"]
        db.tv_chart_save("template", client_id, user_id, name, content, "", "")
        return {"status": "ok"}

    @app.route("/tv/<version>/drawings", methods=["GET", "POST"])
    @login_required
    def tv_drawings(version):
        """TradingView drawing persistence with explicit failure semantics."""
        client_id = str(request.args.get("client") or "")
        user_id = str(request.args.get("user") or "")
        chart_id = str(request.args.get("chart") or "")
        layout_id = str(request.args.get("layout") or "")
        symbol = str(request.args.get("symbol") or "")

        if request.method == "GET":
            if client_id == "" or user_id == "" or chart_id == "" or layout_id == "":
                return {"status": "ok", "data": {"state": ""}}
            state = db.tv_drawing_get(client_id, user_id, layout_id, chart_id, symbol)
            return {"status": "ok", "data": {"state": state or ""}}

        state = request.form.get("state")
        if state is None:
            data = request.get_json(silent=True) or {}
            state = data.get("state")

        if state is not None and symbol == "":
            try:
                state_obj = json.loads(state) if isinstance(state, str) else state
                if isinstance(state_obj, dict):
                    symbol = str(state_obj.get("symbol") or "")
            except (TypeError, ValueError, json.JSONDecodeError):
                symbol = ""

        if client_id == "" or user_id == "" or chart_id == "" or layout_id == "" or state is None:
            return {
                "status": "error",
                "error": "invalid_drawing_request",
                "message": "client, user, chart, layout and state are required",
            }, 422

        request_id = uuid.uuid4().hex
        try:
            saved = db.tv_drawing_save_or_update(
                client_id, user_id, layout_id, chart_id, symbol, state
            )
        except Exception:
            __log.exception("drawing save failed request_id=%s", request_id)
            return {
                "status": "error",
                "error": "drawing_save_failed",
                "request_id": request_id,
            }, 500
        if saved is not True:
            __log.error("drawing save was not confirmed request_id=%s", request_id)
            return {
                "status": "error",
                "error": "drawing_save_failed",
                "request_id": request_id,
            }, 500
        return {"status": "ok"}

    # 股票涨跌幅
    @app.route("/ticks", methods=["POST"])
    @login_required
    def ticks():
        try:
            tick_request = parse_tick_request(
                request.form.get("market"),
                request.form.get("codes"),
                allowed_markets=market_frequencys.keys(),
                max_codes=int(security_overrides.get("WEB_TICKS_MAX_CODES", getattr(config, "WEB_TICKS_MAX_CODES", 200))),
                max_code_bytes=int(security_overrides.get("WEB_TICKS_MAX_CODE_BYTES", getattr(config, "WEB_TICKS_MAX_CODE_BYTES", 128))),
            )
            tick_rate_limiter.check(request.remote_addr or "unknown")
        except TickRateLimitError as exc:
            return {"error": exc.code, "message": str(exc)}, exc.http_status
        except TickRequestError as exc:
            return {"error": exc.code, "message": str(exc)}, exc.http_status

        try:
            ex = get_exchange(Market(tick_request.market))
            stock_ticks = tick_provider_caller.call(ex.ticks, list(tick_request.codes))
            now_trading = bool(ex.now_trading())
            res_ticks = [
                {"code": code, "price": tick.last, "rate": round(float(tick.rate), 2)}
                for code, tick in stock_ticks.items()
            ]
            return {"now_trading": now_trading, "ticks": res_ticks}
        except (TickProviderBusyError, TickProviderTimeoutError) as exc:
            return {"error": exc.code, "message": str(exc), "now_trading": False, "ticks": []}, exc.http_status
        except TickProviderCallError as exc:
            __log.exception("tick provider call failed")
            return {"error": exc.code, "message": "tick provider call failed", "now_trading": False, "ticks": []}, exc.http_status
        except Exception:
            __log.exception("tick response conversion failed")
            return {"error": "tick_provider_failed", "message": "tick provider call failed", "now_trading": False, "ticks": []}, 502

    # 获取自选组列表
    @app.route("/get_zixuan_groups/<market>")
    @login_required
    def get_zixuan_groups(market):
        zx = ZiXuan(market)
        groups = zx.get_zx_groups()
        return groups

    # 获取自选组的股票
    @app.route("/get_zixuan_stocks/<market>/<group_name>")
    @login_required
    def get_zixuan_stocks(market, group_name):
        zx = ZiXuan(market)
        stock_list = zx.zx_stocks(group_name)
        return {"code": 0, "msg": "", "count": len(stock_list), "data": stock_list}

    @app.route("/get_stock_zixuan/<market>/<code>")
    @login_required
    def get_stock_zixuan(market, code: str):
        code = code.replace("__", "/")  # 数字货币特殊处理
        zx = ZiXuan(market)
        zx_groups = zx.query_code_zx_names(code)
        return zx_groups

    @app.route("/zixuan_group/<market>", methods=["GET"])
    @login_required
    def zixuan_group_view(market):
        zx = ZiXuan(market)
        zx_groups = zx.get_zx_groups()
        return render_template("zixuan.html", market=market, zx_groups=zx_groups)

    @app.route("/opt_zixuan_group/<market>", methods=["POST"])
    @login_required
    def opt_zixuan_group(market):
        """
        操作自选组
        """
        opt = request.form["opt"]
        zx_group = request.form["zx_group"]
        zx = ZiXuan(market)
        if opt == "DEL":
            return {"ok": zx.del_zx_group(zx_group)}
        else:
            return {"ok": zx.add_zx_group(zx_group)}

    @app.route("/zixuan_opt_export", methods=["GET"])
    @login_required
    def opt_zixuan_export():
        """导出自选组；响应使用请求私有内存流，不写共享临时文件。"""
        market = request.args.get("market")
        zx_group = request.args.get("zx_group")
        zx = ZiXuan(market)
        output = export_watchlist_text(zx.zx_stocks(zx_group)).encode("utf-8")
        return send_file(
            BytesIO(output),
            mimetype="text/plain; charset=utf-8",
            as_attachment=True,
            download_name="zixuan_export.txt",
            max_age=0,
        )

    @app.route("/zixuan_opt_import", methods=["POST"])
    @login_required
    def opt_zixuan_import():
        """导入经过大小、编码、行数与字段边界校验的 UTF-8 文本。"""
        market = request.form.get("market", "")
        zx_group = request.form.get("zx_group", "").strip()
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return {"ok": False, "msg": "请选择导入文件"}, 400
        if not upload.filename.lower().endswith(".txt"):
            return {"ok": False, "msg": "只允许上传 .txt 文件"}, 422
        if not zx_group or len(zx_group) > 100:
            return {"ok": False, "msg": "自选组名称无效"}, 422
        try:
            ex = get_exchange(Market(market))
            market_all_stocks = ex.all_stocks()
            entries = parse_watchlist_stream(
                upload.stream,
                market=market,
                available_codes=(stock["code"] for stock in market_all_stocks),
                max_bytes=max_upload_bytes,
                max_lines=max_watchlist_lines,
                max_line_bytes=max_watchlist_line_bytes,
            )
        except (ValueError, KeyError, WatchlistTransferError) as exc:
            status_code = getattr(exc, "status_code", 422)
            return {"ok": False, "msg": str(exc) or "导入文件无效"}, status_code

        zx = ZiXuan(market)
        for entry in entries:
            zx.add_stock(zx_group, entry.code, entry.name)
        return {"ok": True, "msg": f"成功导入 {len(entries)} 条记录"}

    # 设置股票的自选组
    @app.route("/set_stock_zixuan", methods=["POST"])
    @login_required
    def set_stock_zixuan():
        market = request.form["market"]
        opt = request.form["opt"]
        group_name = request.form["group_name"]
        code = request.form["code"]
        zx = ZiXuan(market)
        if opt == "DEL":
            res = zx.del_stock(group_name, code)
        elif opt == "ADD":
            res = zx.add_stock(group_name, code, None)
        elif opt == "COLOR":
            color = request.form["color"]
            res = zx.color_stock(group_name, code, color)
        elif opt == "SORT":
            direction = request.form["direction"]
            if direction == "top":
                res = zx.sort_top_stock(group_name, code)
            else:
                res = zx.sort_bottom_stock(group_name, code)
        else:
            res = False

        return {"ok": res}

    def _guard_task(task_obj):
        if isinstance(task_obj, _UnavailableTasks):
            return _task_error_response(task_obj.error)
        if isinstance(task_obj, _LazyTasks):
            task_obj._load()
            if task_obj.error is not None:
                return _task_error_response(task_obj.error)
        return None

    # 警报提醒列表
    @app.route("/alert_list/<market>")
    @login_required
    def alert_list(market):
        task_error = _guard_task(_alert_tasks)
        if task_error is not None:
            return {"code": 1, "msg": task_error["msg"], "count": 0, "data": []}
        al = _alert_tasks.task_list(market)
        al = [
            {
                "id": _l.id,
                "market": _l.market,
                "task_name": _l.task_name,
                "zx_group": _l.zx_group,
                "interval_minutes": _l.interval_minutes,
                "frequency": _l.frequency,
                "strategy_config": _l.strategy_config,
                "strategy_memo": _l.strategy_memo,
                "is_send_msg": _l.is_send_msg,
                "is_run": _l.is_run,
            }
            for _l in al
        ]
        return {"code": 0, "msg": "", "count": len(al), "data": al}

    # 警报编辑页面
    @app.route("/alert_edit/<market>/<id>")
    @login_required
    def alert_edit(market, id):
        task_error = _guard_task(_alert_tasks)
        if task_error is not None:
            return task_error

        strategy_registry = getattr(config, "ALERT_STRATEGIES", {})
        try:
            alert_strategies = registered_strategy_choices(strategy_registry)
        except (StrategyRegistryError, ValueError, TypeError) as error:
            return {"ok": False, "msg": f"ALERT_STRATEGIES 配置错误：{error}"}

        default_strategy_id = (
            alert_strategies[0].strategy_id if alert_strategies else ""
        )
        alert_config = {
            "id": "",
            "market": market,
            "task_name": "",
            "zx_group": "我的关注",
            "interval_minutes": 5,
            "frequency": "5m",
            "strategy_id": default_strategy_id,
            "strategy_kwargs": "{}",
            "strategy_memo": "",
            "legacy_strategy_path": "",
            "unavailable_strategy_id": "",
            "is_send_msg": 1,
            "is_run": 1,
        }
        if id != "0":
            _alert_config = _alert_tasks.alert_get(id)
            if _alert_config is not None:
                try:
                    strategy_config = json.loads(_alert_config.strategy_config or "{}")
                except json.JSONDecodeError:
                    strategy_config = {}
                if not isinstance(strategy_config, dict):
                    strategy_config = {}

                strategy_id = strategy_config.get("strategy_id", "")
                legacy_strategy_path = strategy_config.get("strategy_path", "")
                unavailable_strategy_id = ""
                if strategy_id and strategy_id not in strategy_registry:
                    unavailable_strategy_id = str(strategy_id)
                    strategy_id = ""
                if not strategy_id and legacy_strategy_path:
                    strategy_id = (
                        find_registered_strategy_id_by_path(
                            strategy_registry, legacy_strategy_path
                        )
                        or ""
                    )
                alert_config = {
                    "id": _alert_config.id,
                    "market": _alert_config.market,
                    "task_name": _alert_config.task_name,
                    "zx_group": _alert_config.zx_group,
                    "interval_minutes": _alert_config.interval_minutes,
                    "frequency": _alert_config.frequency,
                    "strategy_id": strategy_id,
                    "strategy_kwargs": json.dumps(
                        strategy_config.get("strategy_kwargs", {}), ensure_ascii=False
                    ),
                    "strategy_memo": _alert_config.strategy_memo,
                    "legacy_strategy_path": (
                        legacy_strategy_path if not strategy_id else ""
                    ),
                    "unavailable_strategy_id": unavailable_strategy_id,
                    "is_send_msg": _alert_config.is_send_msg,
                    "is_run": _alert_config.is_run,
                }

        zx = ZiXuan(market)
        zixuan_groups = zx.zixuan_list
        frequencys = get_exchange(Market(market)).support_frequencys()

        return render_template(
            "alert.html",
            zixuan_groups=zixuan_groups,
            frequencys=frequencys,
            alert_strategies=alert_strategies,
            **alert_config,
        )

    @app.route("/alert_save", methods=["POST"])
    @login_required
    def alert_save():
        task_error = _guard_task(_alert_tasks)
        if task_error is not None:
            return task_error

        strategy_id = request.form.get("strategy_id", "").strip()
        if strategy_id == "":
            return {"ok": False, "msg": "请选择已注册策略"}

        try:
            strategy_kwargs = json.loads(request.form.get("strategy_kwargs") or "{}")
        except json.JSONDecodeError as error:
            return {"ok": False, "msg": f"strategy_kwargs 必须是合法 JSON：{error}"}
        if not isinstance(strategy_kwargs, dict):
            return {"ok": False, "msg": "strategy_kwargs 必须是 JSON 对象"}

        strategy_registry = getattr(config, "ALERT_STRATEGIES", {})
        try:
            validate_registered_strategy(
                strategy_registry, strategy_id, strategy_kwargs
            )
        except Exception as error:
            # Validation may import a trusted registry module. Surface any configuration
            # or import failure as a form error instead of returning a 500 response.
            return {"ok": False, "msg": f"策略配置无效：{error}"}

        try:
            interval_minutes = int(request.form.get("interval_minutes", "5"))
            is_send_msg = int(request.form.get("is_send_msg", "1"))
            is_run = int(request.form.get("is_run", "1"))
        except ValueError as error:
            return {"ok": False, "msg": f"数值字段格式错误：{error}"}

        strategy_config = json.dumps(
            {
                "strategy_id": strategy_id,
                "strategy_kwargs": strategy_kwargs,
            },
            ensure_ascii=False,
        )
        alert_config = {
            "id": request.form.get("id", ""),
            "market": request.form.get("market", ""),
            "task_name": request.form.get("task_name", ""),
            "interval_minutes": interval_minutes,
            "zx_group": request.form.get("zx_group", ""),
            "frequency": request.form.get("frequency", ""),
            "strategy_config": strategy_config,
            "strategy_memo": request.form.get("strategy_memo", ""),
            "is_send_msg": is_send_msg,
            "is_run": is_run,
        }
        _alert_tasks.alert_save(alert_config)
        return {"ok": True}

    @app.route("/alert_del/<id>", methods=["POST"])
    @login_required
    def alert_del(id):
        task_error = _guard_task(_alert_tasks)
        if task_error is not None:
            return task_error
        res = _alert_tasks.alert_del(id)
        return {"ok": res}

    @app.route("/alert_records/<market>")
    @login_required
    def alert_records(market):
        task_name = request.args.get("task_name")
        records = db.alert_record_query(market, task_name)
        rls = [
            {
                "event_type": _r.event_type,
                "action": _r.action,
                "score": _r.score,
                "event_time": _r.event_time,
                "msg": _r.alert_msg,
                "code": _r.stock_code,
                "name": _r.stock_name,
                "frequency": _r.frequency,
                "task_name": _r.task_name,
                "datetime_str": fun.datetime_to_str(_r.alert_dt),
            }
            for _r in records
        ]
        return {
            "code": 0,
            "msg": "",
            "count": len(rls),
            "data": rls,
        }

    @app.route("/jobs")
    @login_required
    def jobs():
        return render_template("jobs.html", jobs=list(scheduler.my_task_list.values()))

    @app.route("/xuangu/task_list/<market>")
    @login_required
    def xuangu_task_list(market):
        task_error = _guard_task(_xuangu_tasks)
        if task_error is not None:
            return task_error
        # 获取自选组
        zx = ZiXuan(market)
        zixuan_groups = zx.zixuan_list

        # 交易所支持周期
        frequencys = get_exchange(Market(market)).support_frequencys()

        # 选股配置
        xuangu_task_configs = _xuangu_tasks.xuangu_task_config_list()
        xuangu_task_list = {
            _k: {**_v, "name": _v.get("name", _k)}
            for _k, _v in xuangu_task_configs.items()
        }

        # task_memo
        task_infos = {
            _k: {
                "task_memo": _v.get("task_memo", _v.get("description", "")),
                "frequency_memo": _v.get("frequency_memo", "自定义策略周期"),
            }
            for _k, _v in xuangu_task_list.items()
        }

        return render_template(
            "xuangu_list.html",
            market=market,
            tasks=xuangu_task_list,
            task_infos=task_infos,
            zixuan_groups=zixuan_groups,
            frequencys=frequencys,
        )

    @app.route("/xuangu/task_add", methods=["POST"])
    @login_required
    def xuangu_task_add():
        task_error = _guard_task(_xuangu_tasks)
        if task_error is not None:
            return task_error
        market = request.form["market"]
        task_name = request.form["task_name"]
        frequencys = request.form["frequencys"]
        src_zx_group = request.form["src_zx_group"]
        target_zx_group = request.form.get("target_zx_group", "").strip()
        opt_type = request.form["opt_type"]

        frequencys = frequencys.split(",")
        opt_type = opt_type.split(",")

        if task_name not in _xuangu_tasks.xuangu_task_config_list().keys():
            return {"ok": False, "msg": "选股任务不存在"}

        allow_freq_num = _xuangu_tasks.xuangu_task_config_list()[task_name].get(
            "frequency_num", len(frequencys)
        )
        if len(frequencys) != allow_freq_num:
            return {
                "ok": False,
                "msg": f"选股周期错误，该任务可选周期数量 : {allow_freq_num}",
            }

        run_res = _xuangu_tasks.run_xuangu(
            market, task_name, frequencys, opt_type, src_zx_group, target_zx_group
        )

        return {
            "ok": run_res,
            "msg": "选股任务已存在，请在当前任务中查看任务" if run_res is False else "",
        }

    @app.route("/setting", methods=["GET"])
    @login_required
    def setting():
        # Never send a stored secret back to the browser.  The page only receives a
        # boolean so it can explain that leaving the password field blank keeps it.
        proxy = db.cache_get("req_proxy")
        fs_setting = db.cache_get("fs_keys")
        set_config = {
            "fs_app_id": fs_setting.get("fs_app_id", "") if fs_setting else "",
            "fs_app_secret_configured": feishu_secret_is_configured(fs_setting),
            "fs_user_id": fs_setting.get("fs_user_id", "") if fs_setting else "",
            "proxy_host": proxy.get("host", "") if proxy else "",
            "proxy_port": proxy.get("port", "") if proxy else "",
        }
        return (
            render_template("setting.html", **set_config),
            200,
            {"Cache-Control": "no-store", "Pragma": "no-cache"},
        )

    @app.route("/setting/save", methods=["POST"])
    @login_required
    def setting_save():
        proxy = {
            "host": request.form.get("proxy_host", "").strip(),
            "port": request.form.get("proxy_port", "").strip(),
        }
        fs_keys = merge_feishu_settings(
            db.cache_get("fs_keys"),
            app_id=request.form.get("fs_app_id"),
            app_secret=request.form.get("fs_app_secret"),
            user_id=request.form.get("fs_user_id"),
        )
        db.cache_set("req_proxy", proxy)
        db.cache_set("fs_keys", fs_keys)

        return {"ok": True}, 200, {"Cache-Control": "no-store"}

    @app.route("/a/bkgn_list", methods=["GET"])
    @login_required
    def a_bkgn_list():
        """
        获取沪深a股市场的板块列表
        """
        stock_bkgn = StocksBKGN()
        bkgn_infos = stock_bkgn.file_bkgns()
        all_hy_names = bkgn_infos["hys"]
        all_gn_names = bkgn_infos["gns"]

        res_bkgn_list = []
        for _hy in all_hy_names:
            res_bkgn_list.append(
                {
                    "type": "hy",
                    "bkgn_name": f"行业:{_hy}",
                    "bkgn_code": _hy,
                }
            )
        for _gn in all_gn_names:
            res_bkgn_list.append(
                {
                    "type": "gn",
                    "bkgn_name": f"概念:{_gn}",
                    "bkgn_code": _gn,
                }
            )
        return {
            "code": 0,
            "msg": "",
            "data": res_bkgn_list,
            "count": len(res_bkgn_list),
        }

    @app.route("/a/bkgn_codes", methods=["POST"])
    @login_required
    def a_bkgn_codes():
        bkgn_type = request.form["bkgn_type"]
        bkgn_code = request.form["bkgn_code"]
        stock_bkgn = StocksBKGN()

        if bkgn_type == "hy":
            codes = stock_bkgn.ths_to_tdx_codes(stock_bkgn.get_codes_by_hy(bkgn_code))
        elif bkgn_type == "gn":
            codes = stock_bkgn.ths_to_tdx_codes(stock_bkgn.get_codes_by_gn(bkgn_code))
        else:
            codes = []

        ex = get_exchange(Market.A)
        stocks = {}
        for _code in codes:
            _stock = ex.stock_info(_code)
            if _stock is not None:
                stocks[_code] = _stock

        return {"code": 0, "msg": "", "data": stocks, "count": len(stocks)}

    return app
