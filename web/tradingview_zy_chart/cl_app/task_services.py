"""Generic, observable lazy loading for optional web task services."""
from __future__ import annotations

import importlib
import threading
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, Mapping


class TaskServiceState(StrEnum):
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TaskServiceHealth:
    module: str
    attribute: str
    state: TaskServiceState
    attempts: int
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "attribute": self.attribute,
            "state": self.state.value,
            "attempts": self.attempts,
            "error_type": self.error_type,
        }


class TaskServiceUnavailableError(RuntimeError):
    """Stable public error that preserves the original failure as ``__cause__``."""

    def __init__(self, health: TaskServiceHealth) -> None:
        self.health = health
        error_type = health.error_type or "unknown"
        super().__init__(
            "task service unavailable: "
            f"{health.module}.{health.attribute} "
            f"state={health.state.value} error_type={error_type}"
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": False,
            "error": "task_service_unavailable",
            "msg": "任务服务暂不可用",
            "service": self.health.to_dict(),
        }


Importer = Callable[[str], Any]


class LazyTaskService:
    """Load one task service exactly once and publish an auditable health state.

    Dynamic task modules are an integration boundary: import, attribute lookup,
    construction and optional callbacks may raise unrelated third-party errors.
    One broad catch is therefore intentional here; routes receive only the stable
    ``TaskServiceUnavailableError`` while the original exception remains chained.
    """

    def __init__(
        self,
        *,
        module_name: str,
        attribute_name: str,
        factory_args: tuple[Any, ...] = (),
        factory_kwargs: Mapping[str, Any] | None = None,
        on_load: Callable[[Any], None] | None = None,
        importer: Importer = importlib.import_module,
        logger: Any | None = None,
    ) -> None:
        self.module_name = _module_name(module_name)
        self.attribute_name = _identifier(attribute_name, field="attribute_name")
        self._factory_args = tuple(factory_args)
        self._factory_kwargs = dict(factory_kwargs or {})
        self._on_load = on_load
        self._importer = importer
        self._logger = logger
        self._condition = threading.Condition(threading.RLock())
        self._state = TaskServiceState.NOT_LOADED
        self._attempts = 0
        self._instance: Any | None = None
        self._failure: Exception | None = None
        self._error_type: str | None = None

    @property
    def health(self) -> TaskServiceHealth:
        with self._condition:
            return self._health_locked()

    def get(self) -> Any:
        with self._condition:
            while self._state is TaskServiceState.LOADING:
                self._condition.wait()
            if self._state is TaskServiceState.READY:
                return self._instance
            if self._state is TaskServiceState.FAILED:
                failure = self._failure
                error = TaskServiceUnavailableError(self._health_locked())
                raise error from failure
            self._state = TaskServiceState.LOADING
            self._attempts += 1

        try:
            module = self._importer(self.module_name)
            factory = getattr(module, self.attribute_name)
            instance = factory(*self._factory_args, **self._factory_kwargs)
            if instance is None:
                raise TypeError("task service factory returned None")
            if self._on_load is not None:
                self._on_load(instance)
        except Exception as failure:  # noqa: BLE001 - deliberate dynamic task integration boundary
            with self._condition:
                self._failure = failure
                self._error_type = type(failure).__name__
                self._state = TaskServiceState.FAILED
                health = self._health_locked()
                self._condition.notify_all()
            if self._logger is not None:
                self._logger.error(
                    "task_service_load_failed module=%s attribute=%s error_type=%s",
                    health.module,
                    health.attribute,
                    health.error_type,
                )
            raise TaskServiceUnavailableError(health) from failure

        with self._condition:
            self._instance = instance
            self._failure = None
            self._error_type = None
            self._state = TaskServiceState.READY
            self._condition.notify_all()
            return instance

    def resolve(self) -> tuple[Any | None, TaskServiceUnavailableError | None]:
        try:
            return self.get(), None
        except TaskServiceUnavailableError as error:
            return None, error

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.get(), name)

    def _health_locked(self) -> TaskServiceHealth:
        return TaskServiceHealth(
            module=self.module_name,
            attribute=self.attribute_name,
            state=self._state,
            attempts=self._attempts,
            error_type=self._error_type,
        )


def _identifier(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    token = value.strip()
    if not token or len(token) > 128 or not token.isidentifier():
        raise ValueError(f"invalid {field}: {value!r}")
    return token


def _module_name(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("module_name must be a string")
    token = value.strip()
    if not token or len(token) > 255:
        raise ValueError(f"invalid module_name: {value!r}")
    if any(not part.isidentifier() for part in token.split(".")):
        raise ValueError(f"invalid module_name: {value!r}")
    return token
