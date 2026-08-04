from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Union

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
)

from tradingview_zy import config
from tradingview_zy.db import db
from tradingview_zy.messaging_reliability import (
    RetryPolicy,
    execute_with_retry,
    redact_sensitive,
)

logger = logging.getLogger(__name__)


def config_get_proxy():
    db_proxy = db.cache_get("req_proxy")
    if db_proxy is not None and db_proxy["host"] != "" and db_proxy["port"] != "":
        return dict(db_proxy)
    return {"host": config.PROXY_HOST, "port": config.PROXY_PORT}


def config_get_feishu_keys(market: str) -> dict[str, str]:
    db_fs_key = db.cache_get("fs_keys")
    if (
        db_fs_key is not None
        and db_fs_key["fs_app_id"] != ""
        and db_fs_key["fs_app_secret"] != ""
        and db_fs_key["fs_user_id"] != ""
    ):
        return {
            "app_id": db_fs_key["fs_app_id"],
            "app_secret": db_fs_key["fs_app_secret"],
            "user_id": db_fs_key["fs_user_id"],
        }

    source = config.FEISHU_KEYS.get(market, config.FEISHU_KEYS["default"])
    keys = dict(source)
    keys["user_id"] = config.FEISHU_KEYS["user_id"]
    return keys


def _message_content(title: str, contents: Union[str, list[str]]) -> str:
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if len(title.encode("utf-8")) > 512:
        raise ValueError("title exceeds 512 UTF-8 bytes")
    if isinstance(contents, str):
        rows = [[{"tag": "text", "text": f"{contents} \n"}]]
    elif isinstance(contents, list):
        if len(contents) > 100:
            raise ValueError("contents exceeds 100 entries")
        row: list[dict[str, str]] = []
        for item in contents:
            if not isinstance(item, str):
                raise TypeError("message contents entries must be strings")
            if item.startswith("img_"):
                row.append({"tag": "img", "image_key": item})
            else:
                row.append({"tag": "text", "text": f"{item} \n"})
        rows = [row]
    else:
        raise TypeError("contents must be a string or list of strings")

    payload = {"zh_cn": {"title": title.strip(), "content": rows}}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 32 * 1024:
        raise ValueError("message content exceeds 32 KiB")
    return encoded


def _response_http_status(response: object) -> int | None:
    raw = getattr(response, "raw", None)
    status = getattr(raw, "status_code", None)
    return status if isinstance(status, int) else None


def _retryable_feishu_response(response: object) -> bool:
    status = _response_http_status(response)
    return status == 429 or (status is not None and 500 <= status <= 599)


def _delivery_policy(
    timeout_seconds: float | None, max_attempts: int | None
) -> RetryPolicy:
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else getattr(config, "FEISHU_REQUEST_TIMEOUT_SECONDS", 5.0)
    )
    attempts = (
        max_attempts
        if max_attempts is not None
        else getattr(config, "FEISHU_MAX_ATTEMPTS", 3)
    )
    return RetryPolicy(
        request_timeout_seconds=float(timeout),
        max_attempts=int(attempts),
        initial_backoff_seconds=float(
            getattr(config, "FEISHU_RETRY_BACKOFF_SECONDS", 0.2)
        ),
        max_backoff_seconds=float(
            getattr(config, "FEISHU_MAX_RETRY_BACKOFF_SECONDS", 1.0)
        ),
    )


def send_fs_msg(
    market: str,
    title: str,
    contents: Union[str, list[str]],
    *,
    delivery_id: str | None = None,
    timeout_seconds: float | None = None,
    max_attempts: int | None = None,
    _sleep=time.sleep,
) -> bool:
    """Send one Feishu message with finite timeout, retry, and idempotency.

    A fresh UUID is generated for each logical call and reused by all retries,
    preventing a transport retry from creating duplicate messages.  Disabled or
    failed delivery returns ``False``; only a confirmed SDK success returns
    ``True``.
    """

    fs_key = config_get_feishu_keys(market)
    secrets = tuple(str(value) for value in fs_key.values() if value)
    if not all(fs_key.get(key, "") for key in ("app_id", "app_secret", "user_id")):
        logger.info("Feishu messaging is disabled for market=%s", market)
        return False

    policy = _delivery_policy(timeout_seconds, max_attempts)
    message_content = _message_content(title, contents)
    request_uuid = delivery_id or uuid.uuid4().hex
    if not isinstance(request_uuid, str) or not request_uuid.strip():
        raise ValueError("delivery_id must be a non-empty string")
    request_uuid = request_uuid.strip()
    if len(request_uuid.encode("utf-8")) > 50:
        raise ValueError("delivery_id exceeds 50 UTF-8 bytes")

    client = (
        lark.Client.builder()
        .app_id(fs_key["app_id"])
        .app_secret(fs_key["app_secret"])
        .timeout(policy.request_timeout_seconds)
        .log_level(lark.LogLevel.WARNING)
        .build()
    )
    request: CreateMessageRequest = (
        CreateMessageRequest.builder()
        .receive_id_type("user_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(fs_key["user_id"])
            .msg_type("post")
            .content(message_content)
            .uuid(request_uuid)
            .build()
        )
        .build()
    )

    outcome = execute_with_retry(
        lambda: client.im.v1.message.create(request),
        policy=policy,
        should_retry_result=_retryable_feishu_response,
        sleep=_sleep,
    )
    if outcome.error is not None:
        logger.error(
            "Feishu delivery failed after %d attempt(s): %s",
            outcome.attempts,
            redact_sensitive(outcome.error, secrets),
        )
        return False

    response: CreateMessageResponse = outcome.result
    if response is not None and response.success():
        return True

    code = getattr(response, "code", "unknown")
    status = _response_http_status(response)
    log_id_getter = getattr(response, "get_log_id", None)
    log_id = log_id_getter() if callable(log_id_getter) else "unknown"
    message = redact_sensitive(getattr(response, "msg", "unknown"), secrets)
    logger.error(
        "Feishu delivery rejected after %d attempt(s): code=%s http_status=%s log_id=%s msg=%s",
        outcome.attempts,
        code,
        status,
        log_id,
        message,
    )
    return False


if __name__ == "__main__":
    send_fs_msg(
        "futures",
        "这里是选股的测试消息",
        ["运行完成", "选出300只股票", "用时1000小时"],
    )
