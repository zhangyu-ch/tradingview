import json
from typing import Union

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
)

from tradingview_zy import config
from tradingview_zy.db import db


def config_get_proxy():
    db_proxy = db.cache_get("req_proxy")
    if db_proxy is not None and db_proxy["host"] != "" and db_proxy["port"] != "":
        return db_proxy
    return {
        "host": config.PROXY_HOST,
        "port": config.PROXY_PORT,
    }


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


# 旧版的API接口已经下架，不能新增了，后续使用 飞书的 消息接口


def send_fs_msg(market, title, contents: Union[str, list]):
    """
    发送飞书消息
    """
    fs_key = config_get_feishu_keys(market)
    if (
        fs_key is None
        or fs_key["app_id"] == ""
        or fs_key["app_secret"] == ""
        or fs_key["user_id"] == ""
    ):
        return True
    # 创建client
    client = (
        lark.Client.builder()
        .app_id(fs_key["app_id"])
        .app_secret(fs_key["app_secret"])
        .log_level(lark.LogLevel.WARNING)
        .build()
    )
    # https://open.feishu.cn/document/server-docs/im-v1/message-content-description/create_json
    if isinstance(contents, str):
        msg_content = {
            "zh_cn": {
                "title": title,
                "content": [[{"tag": "text", "text": f"{contents} \n"}]],
            }
        }
    else:
        msg_content = {
            "zh_cn": {
                "title": title,
                "content": [[]],
            }
        }
        for _c in contents:
            if _c.startswith("img_"):  # 支持图片消息
                msg_content["zh_cn"]["content"][0].append(
                    {"tag": "img", "image_key": f"{_c}"}
                )
            else:
                msg_content["zh_cn"]["content"][0].append(
                    {"tag": "text", "text": f"{_c} \n"}
                )

    msg_content = json.dumps(msg_content, ensure_ascii=False)
    # 构造请求对象
    request: CreateMessageRequest = (
        CreateMessageRequest.builder()
        .receive_id_type("user_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(fs_key["user_id"])
            .msg_type("post")
            .content(msg_content)
            .build()
        )
        .build()
    )

    # 发起请求
    response: CreateMessageResponse = client.im.v1.message.create(request)
    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.im.v1.message.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
        )
    return True


if __name__ == "__main__":
    send_fs_msg(
        "futures",
        "这里是选股的测试消息",
        ["运行完成", "选出300只股票", "用时1000小时"],
    )
