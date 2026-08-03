"""Validate the runtime environment against the project's declared contract."""

from __future__ import annotations

import importlib
import os
import socket
import sys
import tomllib
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Callable, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


class CheckStatus(IntEnum):
    OK = 0
    DEGRADED = 1
    FAILED = 2


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    message: str


def project_python_spec(path: Path = PYPROJECT) -> str:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    spec = data.get("project", {}).get("requires-python")
    if not isinstance(spec, str) or not spec.strip():
        raise RuntimeError("pyproject.toml does not declare project.requires-python")
    return spec.strip()


def _version_tuple(value: str | Iterable[int]) -> tuple[int, ...]:
    if isinstance(value, str):
        parts = value.strip().split(".")
        if not parts or not all(part.isdigit() for part in parts):
            raise ValueError(f"invalid version: {value!r}")
        return tuple(int(part) for part in parts)
    return tuple(int(part) for part in value)


def _compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return (left > right) - (left < right)


def _python_version_supported(
    version_info: tuple[int, ...] | None = None,
    spec: str | None = None,
) -> bool:
    """Evaluate the comma-separated PEP 440 bounds used by this project."""

    version = _version_tuple(version_info or tuple(sys.version_info[:3]))
    spec = project_python_spec() if spec is None else spec
    operators: tuple[tuple[str, Callable[[int], bool]], ...] = (
        (">=", lambda result: result >= 0),
        ("<=", lambda result: result <= 0),
        ("==", lambda result: result == 0),
        ("!=", lambda result: result != 0),
        (">", lambda result: result > 0),
        ("<", lambda result: result < 0),
    )
    for raw_clause in spec.split(","):
        clause = raw_clause.strip()
        if not clause:
            continue
        for operator, predicate in operators:
            if clause.startswith(operator):
                target = _version_tuple(clause[len(operator) :])
                if not predicate(_compare_versions(version, target)):
                    return False
                break
        else:
            raise ValueError(f"unsupported Python version clause: {clause!r}")
    return True


def _check_python() -> CheckResult:
    spec = project_python_spec()
    version = ".".join(str(part) for part in sys.version_info[:3])
    if _python_version_supported(tuple(sys.version_info[:3]), spec):
        return CheckResult("python", CheckStatus.OK, f"Python {version} satisfies {spec}")
    return CheckResult(
        "python",
        CheckStatus.FAILED,
        f"Python {version} does not satisfy project requires-python {spec}",
    )


def _check_project_imports() -> CheckResult:
    src_path = str(PROJECT_ROOT / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    try:
        importlib.import_module("tradingview_zy.base")
        importlib.import_module("tradingview_zy.config")
    except Exception as exc:
        return CheckResult(
            "project",
            CheckStatus.FAILED,
            f"cannot import project configuration: {type(exc).__name__}: {exc}",
        )
    return CheckResult("project", CheckStatus.OK, "project package and config import correctly")


def _check_proxy(config) -> CheckResult:
    host = str(getattr(config, "PROXY_HOST", "") or "").strip()
    if not host:
        return CheckResult("proxy", CheckStatus.OK, "proxy is not configured")
    port = int(getattr(config, "PROXY_PORT", 0) or 0)
    try:
        with socket.create_connection((host, port), timeout=3):
            pass
    except OSError as exc:
        return CheckResult(
            "proxy",
            CheckStatus.DEGRADED,
            f"proxy {host}:{port} is unavailable: {exc}",
        )
    return CheckResult("proxy", CheckStatus.OK, f"proxy {host}:{port} is reachable")


def _check_redis(config) -> CheckResult:
    host = str(getattr(config, "REDIS_HOST", "") or "").strip()
    if not host:
        return CheckResult("redis", CheckStatus.OK, "Redis is not configured")
    try:
        redis = importlib.import_module("redis")
        client = redis.Redis(
            host=host,
            port=int(getattr(config, "REDIS_PORT", 6379)),
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        client.ping()
        close = getattr(client, "close", None)
        if callable(close):
            close()
    except Exception as exc:
        return CheckResult(
            "redis",
            CheckStatus.DEGRADED,
            f"Redis is unavailable: {type(exc).__name__}: {exc}",
        )
    return CheckResult("redis", CheckStatus.OK, "Redis is reachable")


def _check_database(config) -> CheckResult:
    if str(getattr(config, "DB_TYPE", "sqlite")).lower() != "mysql":
        return CheckResult("database", CheckStatus.OK, "SQLite/local database mode")
    connection = None
    try:
        pymysql = importlib.import_module("pymysql")
        connection = pymysql.connect(
            host=config.DB_HOST,
            port=int(config.DB_PORT),
            user=config.DB_USER,
            password=config.DB_PWD,
            database=config.DB_DATABASE,
            connect_timeout=3,
            read_timeout=3,
            write_timeout=3,
        )
    except Exception as exc:
        return CheckResult(
            "database",
            CheckStatus.FAILED,
            f"configured MySQL is unavailable: {type(exc).__name__}: {exc}",
        )
    finally:
        if connection is not None:
            connection.close()
    return CheckResult("database", CheckStatus.OK, "configured MySQL is reachable")


def run_checks() -> list[CheckResult]:
    results = [_check_python()]
    if results[-1].status is CheckStatus.FAILED:
        return results

    project = _check_project_imports()
    results.append(project)
    if project.status is CheckStatus.FAILED:
        return results

    from tradingview_zy import config

    results.extend((_check_proxy(config), _check_redis(config), _check_database(config)))
    return results


def check_env() -> int:
    results = run_checks()
    for result in results:
        print(f"[{result.status.name}] {result.name}: {result.message}")
    status = max((result.status for result in results), default=CheckStatus.FAILED)
    print(f"环境检查结果：{status.name}")
    return 0 if status in {CheckStatus.OK, CheckStatus.DEGRADED} else 1


if __name__ == "__main__":
    raise SystemExit(check_env())
