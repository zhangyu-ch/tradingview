"""Per-application dependency container shared by feature blueprints."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from flask import current_app

WEB_SERVICES_EXTENSION = "tradingview_zy.web_services"


@dataclass(frozen=True, slots=True)
class WebAppServices:
    web_host: str
    login_password: str
    login_password_hash: str
    remember_days: int
    auto_login: bool
    csrf_trusted_origins: tuple[str, ...]
    login_limiter: Any
    storage_principal: str
    max_upload_bytes: int
    max_watchlist_lines: int
    max_watchlist_line_bytes: int
    tick_rate_limiter: Any
    tick_provider_caller: Any
    scheduler_status_store: Any
    history_request_tracker: Any
    footprint_cache: Any
    frequency_maps: Mapping[str, str]
    resolution_maps: Mapping[str, str]
    market_frequencies: Mapping[str, Sequence[str]]
    market_default_codes: Mapping[str, str]
    market_catalog: tuple[Mapping[str, Any], ...]
    default_market: str
    logger: Any
    alert_tasks: Any
    xuangu_tasks: Any
    security_overrides: Mapping[str, Any]
    database: Any
    get_exchange: Callable[..., Any]
    config: Any
    fun: Any
    zixuan_factory: Callable[..., Any]
    stocks_bkgn_factory: Callable[..., Any]
    secret_store_factory: Callable[..., Any]
    get_data_path: Callable[[], Any]

    @classmethod
    def create(cls, **values: Any) -> "WebAppServices":
        for field in (
            "frequency_maps",
            "resolution_maps",
            "market_default_codes",
            "security_overrides",
        ):
            values[field] = MappingProxyType(dict(values[field]))
        values["market_frequencies"] = MappingProxyType(
            {key: tuple(frequencies) for key, frequencies in values["market_frequencies"].items()}
        )
        values["market_catalog"] = tuple(
            MappingProxyType(dict(item)) for item in values["market_catalog"]
        )
        return cls(**values)


def install_web_services(app, services: WebAppServices) -> None:
    if WEB_SERVICES_EXTENSION in app.extensions:
        raise RuntimeError("web services already installed")
    app.extensions[WEB_SERVICES_EXTENSION] = services


def get_web_services() -> WebAppServices:
    services = current_app.extensions.get(WEB_SERVICES_EXTENSION)
    if not isinstance(services, WebAppServices):
        raise RuntimeError("web services are not installed for this app")
    return services
