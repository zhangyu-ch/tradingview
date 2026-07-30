"""Validate the local runtime and configured services."""

from __future__ import annotations

import os
import socket
import sys
from typing import Any

MIN_PYTHON = (3, 11)
NETWORK_TIMEOUT_SECONDS = 3.0


def _python_version_supported(version_info: Any = None) -> bool:
    version_info = sys.version_info if version_info is None else version_info
    return tuple(version_info[:2]) >= MIN_PYTHON


def _check_tcp_endpoint(host: str, port: int, timeout: float = NETWORK_TIMEOUT_SECONDS) -> None:
    with socket.create_connection((host, int(port)), timeout=timeout):
        pass


def _load_project_config():
    try:
        from tradingview_zy import base  # noqa: F401
    except Exception as error:
        print("无法导入 tradingview_zy 模块，环境变量未设置或设置错误")
        print(f"当前的环境变量如下：{sys.path}")
        print(f"需要将 PYTHONPATH 环境变量设置为 {os.getcwd()}\\src 目录")
        print(f"详细错误：{error}")
        return None

    try:
        from tradingview_zy import config
    except Exception as error:
        print("无法导入 config，请在 src/tradingview_zy 目录复制 config.py.demo 为 config.py")
        print(f"详细错误：{error}")
        return None
    return config


def _check_proxy(config) -> bool:
    if getattr(config, "PROXY_HOST", "") == "":
        return True
    try:
        _check_tcp_endpoint(config.PROXY_HOST, config.PROXY_PORT)
        return True
    except (OSError, ValueError) as error:
        print(f"可选项：当前设置的代理不可用：{error}")
        print("如不使用数字货币行情，可以忽略该项")
        return False


def _check_redis(config) -> bool:
    if getattr(config, "REDIS_HOST", "") == "":
        return True
    try:
        import redis

        client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=NETWORK_TIMEOUT_SECONDS,
            socket_timeout=NETWORK_TIMEOUT_SECONDS,
        )
        client.ping()
        client.close()
        return True
    except Exception as error:
        print(f"可选项：Redis 连接失败：{error}")
        print("Redis 不是必须的，不使用可以忽略")
        return False


def _check_mysql(config) -> bool:
    if getattr(config, "DB_TYPE", "sqlite") != "mysql":
        return True
    try:
        import pymysql

        connection = pymysql.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            password=config.DB_PWD,
            database=config.DB_DATABASE,
            connect_timeout=int(NETWORK_TIMEOUT_SECONDS),
            read_timeout=int(NETWORK_TIMEOUT_SECONDS),
            write_timeout=int(NETWORK_TIMEOUT_SECONDS),
        )
        connection.close()
        return True
    except Exception as error:
        print(
            "MySQL 连接失败，请检查服务、地址、端口、用户名、密码和数据库配置："
            f"{error}"
        )
        return False


def check_env() -> bool:
    """Run environment checks and return whether required checks passed."""

    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"当前Python版本：{version}")
    if not _python_version_supported():
        print("当前 Python 不受支持：项目要求 Python 3.11 或更高版本")
        print("环境检查失败")
        return False

    config = _load_project_config()
    if config is None:
        print("环境检查失败")
        return False

    proxy_ok = _check_proxy(config)
    redis_ok = _check_redis(config)
    optional_ok = proxy_ok and redis_ok
    required_ok = _check_mysql(config)

    if not required_ok:
        print("环境检查失败")
        return False
    if optional_ok:
        print("环境OK")
    else:
        print("环境可运行，但存在不可用的可选服务")
    return True


def main() -> int:
    return 0 if check_env() else 1


if __name__ == "__main__":
    raise SystemExit(main())
