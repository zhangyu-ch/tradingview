from __future__ import annotations

import datetime as dt
import importlib.util
import logging
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from tradingview_zy import fun
from tradingview_zy.messaging_reliability import (
    RetryPolicy,
    execute_with_retry,
    redact_sensitive,
)

ROOT = Path(__file__).resolve().parents[1]
UTILS_PATH = ROOT / "src/tradingview_zy/utils.py"


def test_timestamp_helpers_are_explicit_and_host_independent() -> None:
    assert fun.str_to_timeint(
        "1970-01-01 08:00:00", tz="Asia/Shanghai"
    ) == 0
    assert fun.timeint_to_str(
        0, "%Y-%m-%d %H:%M:%S", tz="Asia/Shanghai"
    ) == "1970-01-01 08:00:00"
    assert fun.timeint_to_str(
        0, "%Y-%m-%d %H:%M:%S", tz="UTC"
    ) == "1970-01-01 00:00:00"
    assert fun.timeint_to_datetime(0, tz="UTC").tzinfo is not None


def test_naive_epoch_conversion_requires_explicit_timezone() -> None:
    naive = dt.datetime(1970, 1, 1, 8, 0, 0)
    with pytest.raises(ValueError, match="explicit assume_tz"):
        fun.datetime_to_int(naive)
    assert fun.datetime_to_int(naive, assume_tz="Asia/Shanghai") == 0
    assert fun.datetime_to_int(dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)) == 0


def test_dst_ambiguous_and_nonexistent_wall_times_fail_closed() -> None:
    with pytest.raises(ValueError, match="nonexistent"):
        fun.str_to_datetime(
            "2026-03-08 02:30:00", tz="America/New_York"
        )
    with pytest.raises(ValueError, match="ambiguous"):
        fun.str_to_datetime(
            "2026-11-01 01:30:00", tz="America/New_York"
        )

    first = fun.str_to_datetime(
        "2026-11-01 01:30:00", tz="America/New_York", fold=0
    )
    second = fun.str_to_datetime(
        "2026-11-01 01:30:00", tz="America/New_York", fold=1
    )
    assert int(second.timestamp() - first.timestamp()) == 3600


def test_string_arithmetic_does_not_use_mktime_or_localtime() -> None:
    assert fun.str_add_seconds_to_str(
        "2026-01-01 00:00:00", 90, tz="Asia/Shanghai"
    ) == "2026-01-01 00:01:30"
    source = (ROOT / "src/tradingview_zy/fun.py").read_text(encoding="utf-8")
    assert "time.localtime" not in source
    assert "time.mktime" not in source
    assert "get_localzone" not in source


def test_singleton_is_published_once_under_concurrent_first_use() -> None:
    counter = 0
    counter_lock = threading.Lock()

    @fun.singleton
    class Resource:
        def __init__(self) -> None:
            nonlocal counter
            time.sleep(0.01)
            with counter_lock:
                counter += 1

    with ThreadPoolExecutor(max_workers=24) as pool:
        values = list(pool.map(lambda _n: Resource(), range(72)))

    assert counter == 1
    assert len({id(value) for value in values}) == 1


def test_singleton_does_not_cache_failed_construction_and_can_reset() -> None:
    attempts = 0

    @fun.singleton
    class Flaky:
        def __init__(self) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("first construction failed")

    with pytest.raises(RuntimeError):
        Flaky()
    first = Flaky()
    second = Flaky()
    assert first is second
    assert attempts == 2

    Flaky.reset_instance()
    third = Flaky()
    assert third is not first
    assert attempts == 3


def test_retry_policy_is_finite_and_exponential() -> None:
    calls = 0
    sleeps: list[float] = []

    def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TimeoutError("transient")
        return "ok"

    outcome = execute_with_retry(
        operation,
        policy=RetryPolicy(
            request_timeout_seconds=1,
            max_attempts=3,
            initial_backoff_seconds=0.1,
            max_backoff_seconds=0.5,
        ),
        sleep=sleeps.append,
    )
    assert outcome.result == "ok"
    assert outcome.error is None
    assert outcome.attempts == 3
    assert outcome.exhausted is False
    assert calls == 3
    assert sleeps == [0.1, 0.2]


def test_retry_policy_exhausts_and_never_swallows_baseexception() -> None:
    outcome = execute_with_retry(
        lambda: (_ for _ in ()).throw(TimeoutError("down")),
        policy=RetryPolicy(max_attempts=2, initial_backoff_seconds=0),
        sleep=lambda _delay: None,
    )
    assert isinstance(outcome.error, TimeoutError)
    assert outcome.attempts == 2
    assert outcome.exhausted is True

    with pytest.raises(KeyboardInterrupt):
        execute_with_retry(
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            policy=RetryPolicy(max_attempts=3),
            sleep=lambda _delay: None,
        )


def test_sensitive_diagnostics_are_redacted_and_compact() -> None:
    secret = "super-secret-value"
    text = redact_sensitive(f"failure\ncredential={secret}" + "x" * 500, [secret])
    assert secret not in text
    assert "[REDACTED]" in text
    assert "\n" not in text
    assert len(text) <= 300


class _FluentBuilder:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    def __getattr__(self, name: str):
        def setter(value):
            self.state[name] = value
            return self

        return setter

    def build(self):
        return SimpleNamespace(**self.state)


class _Response:
    def __init__(self, *, success: bool, status: int = 200, code=0, msg="ok"):
        self._success = success
        self.raw = SimpleNamespace(status_code=status)
        self.code = code
        self.msg = msg

    def success(self):
        return self._success

    def get_log_id(self):
        return "log-1"


def _load_utils(monkeypatch, responses):
    state: dict[str, object] = {"client": {}, "bodies": [], "requests": []}

    class MessageService:
        def create(self, request):
            state["requests"].append(request)
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

    class ClientBuilder(_FluentBuilder):
        def build(self):
            state["client"] = dict(self.state)
            return SimpleNamespace(
                im=SimpleNamespace(
                    v1=SimpleNamespace(message=MessageService())
                )
            )

    class Client:
        @staticmethod
        def builder():
            return ClientBuilder({})

    class Body:
        @staticmethod
        def builder():
            builder = _FluentBuilder({})
            original_build = builder.build

            def build():
                value = original_build()
                state["bodies"].append(value)
                return value

            builder.build = build
            return builder

    class Request:
        @staticmethod
        def builder():
            return _FluentBuilder({})

    lark_module = ModuleType("lark_oapi")
    lark_module.Client = Client
    lark_module.LogLevel = SimpleNamespace(WARNING="warning")
    v1_module = ModuleType("lark_oapi.api.im.v1")
    v1_module.CreateMessageRequest = Request
    v1_module.CreateMessageRequestBody = Body
    v1_module.CreateMessageResponse = _Response
    for name, module in {
        "lark_oapi": lark_module,
        "lark_oapi.api": ModuleType("lark_oapi.api"),
        "lark_oapi.api.im": ModuleType("lark_oapi.api.im"),
        "lark_oapi.api.im.v1": v1_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    config_module = ModuleType("tradingview_zy.config")
    config_module.PROXY_HOST = ""
    config_module.PROXY_PORT = ""
    config_module.FEISHU_REQUEST_TIMEOUT_SECONDS = 0.5
    config_module.FEISHU_MAX_ATTEMPTS = 3
    config_module.FEISHU_RETRY_BACKOFF_SECONDS = 0
    config_module.FEISHU_MAX_RETRY_BACKOFF_SECONDS = 0
    config_module.SECRET_ALLOW_LEGACY_PLAINTEXT = False
    config_module.get_data_path = lambda: Path(tempfile.mkdtemp(prefix="me22-secrets-"))
    config_module.FEISHU_KEYS = {
        "default": {
            "app_id": "env://ME22_FEISHU_APP_ID",
            "app_secret": "env://ME22_FEISHU_APP_SECRET",
        },
        "user_id": "env://ME22_FEISHU_USER_ID",
    }
    monkeypatch.setenv("ME22_FEISHU_APP_ID", "app")
    monkeypatch.setenv("ME22_FEISHU_APP_SECRET", "secret")
    monkeypatch.setenv("ME22_FEISHU_USER_ID", "user")
    db_module = ModuleType("tradingview_zy.db")
    db_module.db = SimpleNamespace(cache_get=lambda _key: None, cache_set=lambda _key, _value: True)
    monkeypatch.setitem(sys.modules, "tradingview_zy.config", config_module)
    monkeypatch.setitem(sys.modules, "tradingview_zy.db", db_module)
    import tradingview_zy

    monkeypatch.setattr(tradingview_zy, "config", config_module, raising=False)

    spec = importlib.util.spec_from_file_location("me22_utils", UTILS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, state


def test_feishu_delivery_sets_timeout_and_reuses_uuid_across_retries(monkeypatch) -> None:
    responses = [
        _Response(success=False, status=503, code=503),
        _Response(success=False, status=429, code=429),
        _Response(success=True),
    ]
    module, state = _load_utils(monkeypatch, responses)

    assert module.send_fs_msg(
        "a", "title", ["one"], delivery_id="delivery-1", _sleep=lambda _d: None
    ) is True
    assert state["client"]["timeout"] == 0.5
    assert len(state["requests"]) == 3
    assert len({id(request) for request in state["requests"]}) == 1
    assert state["bodies"][0].uuid == "delivery-1"


def test_feishu_delivery_does_not_retry_business_rejection(monkeypatch) -> None:
    responses = [_Response(success=False, status=400, code=1001, msg="invalid")]
    module, state = _load_utils(monkeypatch, responses)

    assert module.send_fs_msg(
        "a", "title", "body", _sleep=lambda _d: None
    ) is False
    assert len(state["requests"]) == 1


def test_feishu_failure_is_false_and_secret_is_not_logged(
    monkeypatch, caplog
) -> None:
    responses = [RuntimeError("connection failed with secret") for _ in range(3)]
    module, state = _load_utils(monkeypatch, responses)

    with caplog.at_level(logging.ERROR):
        assert module.send_fs_msg(
            "a", "title", "body", _sleep=lambda _d: None
        ) is False
    assert len(state["requests"]) == 3
    assert "secret" not in caplog.text.replace("[REDACTED]", "")


def test_feishu_disabled_config_returns_false_without_building_client(monkeypatch) -> None:
    module, state = _load_utils(monkeypatch, [_Response(success=True)])
    module.config.FEISHU_KEYS = {
        "default": {"app_id": "", "app_secret": ""},
        "user_id": "",
    }

    assert module.send_fs_msg("a", "title", "body") is False
    assert state["client"] == {}
    assert state["requests"] == []
