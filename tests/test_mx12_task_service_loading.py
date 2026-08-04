from __future__ import annotations

import importlib.util
import threading
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_support.web_routes import compile_route

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "tradingview_zy_chart" / "cl_app"
TASK_SERVICES_PATH = WEB_ROOT / "task_services.py"
FACTORY_PATH = WEB_ROOT / "__init__.py"
TASK_BLUEPRINT_PATH = WEB_ROOT / "blueprints" / "tasks.py"
WEB_SERVICES_PATH = WEB_ROOT / "web_services.py"


def _load_task_services():
    module_name = "test_mx12_task_services"
    spec = importlib.util.spec_from_file_location(module_name, TASK_SERVICES_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_lazy_service_loads_once_and_publishes_ready_health() -> None:
    module = _load_task_services()
    calls: list[str] = []

    class DemoTasks:
        def __init__(self, marker):
            self.marker = marker

        def ping(self):
            return self.marker

    def importer(name):
        calls.append(name)
        return SimpleNamespace(DemoTasks=DemoTasks)

    service = module.LazyTaskService(
        module_name="example.tasks",
        attribute_name="DemoTasks",
        factory_args=("ready",),
        importer=importer,
    )
    assert service.health.to_dict() == {
        "module": "example.tasks",
        "attribute": "DemoTasks",
        "state": "not_loaded",
        "attempts": 0,
        "error_type": None,
    }

    first, error = service.resolve()
    second = service.get()
    assert error is None
    assert first is second
    assert service.ping() == "ready"
    assert calls == ["example.tasks"]
    assert service.health.state is module.TaskServiceState.READY
    assert service.health.attempts == 1


def test_concurrent_callers_share_one_import_and_instance() -> None:
    module = _load_task_services()
    import_count = 0
    import_lock = threading.Lock()

    class DemoTasks:
        pass

    def importer(name):
        nonlocal import_count
        assert name == "example.concurrent"
        with import_lock:
            import_count += 1
        time.sleep(0.02)
        return SimpleNamespace(DemoTasks=DemoTasks)

    service = module.LazyTaskService(
        module_name="example.concurrent",
        attribute_name="DemoTasks",
        importer=importer,
    )
    barrier = threading.Barrier(12)
    instances: list[object] = []
    failures: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait(timeout=2)
            instances.append(service.get())
        except BaseException as error:  # test worker must retain every failure
            failures.append(error)

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert failures == []
    assert len(instances) == 12
    assert len({id(instance) for instance in instances}) == 1
    assert import_count == 1
    assert service.health.state is module.TaskServiceState.READY
    assert service.health.attempts == 1


def test_failure_is_cached_chained_and_public_payload_is_secret_free() -> None:
    module = _load_task_services()
    calls = 0
    original = ModuleNotFoundError("missing dependency token=super-secret")
    original.name = "vendor_secret_sdk"

    class Logger:
        messages: list[tuple] = []

        def error(self, message, *args):
            self.messages.append((message, args))

    logger = Logger()

    def importer(name):
        nonlocal calls
        calls += 1
        assert name == "cl_app.alert_tasks"
        raise original

    service = module.LazyTaskService(
        module_name="cl_app.alert_tasks",
        attribute_name="AlertTasks",
        importer=importer,
        logger=logger,
    )

    instance, first_error = service.resolve()
    assert instance is None
    assert isinstance(first_error, module.TaskServiceUnavailableError)
    assert first_error.__cause__ is original
    payload = first_error.to_payload()
    assert payload == {
        "ok": False,
        "error": "task_service_unavailable",
        "msg": "任务服务暂不可用",
        "service": {
            "module": "cl_app.alert_tasks",
            "attribute": "AlertTasks",
            "state": "failed",
            "attempts": 1,
            "error_type": "ModuleNotFoundError",
        },
    }
    serialized = repr(payload) + str(first_error) + repr(logger.messages)
    assert "super-secret" not in serialized
    assert "token=" not in serialized

    instance, second_error = service.resolve()
    assert instance is None
    assert second_error is not None
    assert second_error.__cause__ is original
    assert calls == 1
    assert service.health.state is module.TaskServiceState.FAILED
    assert service.health.attempts == 1


@pytest.mark.parametrize(
    ("module_name", "attribute_name", "error_type"),
    [
        ("", "Tasks", ValueError),
        ("bad-name.tasks", "Tasks", ValueError),
        ("valid.tasks", "bad-name", ValueError),
        (None, "Tasks", TypeError),
    ],
)
def test_loader_identifiers_are_validated(module_name, attribute_name, error_type) -> None:
    module = _load_task_services()
    with pytest.raises(error_type):
        module.LazyTaskService(
            module_name=module_name,
            attribute_name=attribute_name,
        )


def test_task_routes_return_structured_503_from_generic_health_error() -> None:
    module = _load_task_services()
    health = module.TaskServiceHealth(
        module="cl_app.alert_tasks",
        attribute="AlertTasks",
        state=module.TaskServiceState.FAILED,
        attempts=1,
        error_type="ImportError",
    )
    error = module.TaskServiceUnavailableError(health)

    class Proxy:
        @staticmethod
        def resolve():
            return None, error

    route = compile_route("alert_list", {"_alert_tasks": Proxy()})
    payload, status = route("a")
    assert status == 503
    assert payload["code"] == 1
    assert payload["count"] == 0
    assert payload["data"] == []
    assert payload["error"] == "task_service_unavailable"
    assert payload["service"] == health.to_dict()


def test_factory_and_service_container_have_no_legacy_specific_fallback() -> None:
    factory = FACTORY_PATH.read_text(encoding="utf-8")
    services = WEB_SERVICES_PATH.read_text(encoding="utf-8")
    routes = TASK_BLUEPRINT_PATH.read_text(encoding="utf-8")
    combined = factory + services + routes

    for legacy_name in (
        "UnavailableTasks",
        "LazyTasks",
        "removed_legacy_module_prefixes",
        "removed_legacy_import_names",
        "is_removed_legacy_import_error",
        "unavailable_task_message",
        "load_task_class",
        "task_error_response",
        "guard_task",
        "旧缠论模块已移除",
    ):
        assert legacy_name not in combined

    assert factory.count("LazyTaskService(") == 2
    assert 'module_name=f"{__package__}.alert_tasks"' in factory
    assert 'module_name=f"{__package__}.xuangu_tasks"' in factory
    assert routes.count(".resolve()") == 6
    assert routes.count("to_payload(), 503") == 5
    assert "payload, 503" in routes
    assert "guard_task:" not in services
