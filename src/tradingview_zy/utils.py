"""Shared proxy settings used by market-data adapters."""

from tradingview_zy import config
from tradingview_zy.db import db


def config_get_proxy():
    db_proxy = db.cache_get("req_proxy")
    if db_proxy is not None and db_proxy["host"] != "" and db_proxy["port"] != "":
        return dict(db_proxy)
    return {"host": config.PROXY_HOST, "port": config.PROXY_PORT}
