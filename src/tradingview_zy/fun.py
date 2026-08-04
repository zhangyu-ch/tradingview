from __future__ import annotations

import datetime
import logging
import threading
from functools import wraps
from types import MethodType
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_TIMEZONE_NAME = "Asia/Shanghai"
DEFAULT_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE_NAME)
UTC = datetime.timezone.utc


def resolve_timezone(
    tz: str | datetime.tzinfo | None = None,
) -> datetime.tzinfo:
    """Resolve an explicit timezone; the project default is Asia/Shanghai."""

    if tz is None:
        return DEFAULT_TIMEZONE
    if isinstance(tz, str):
        try:
            return ZoneInfo(tz)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {tz!r}") from exc
    if isinstance(tz, datetime.tzinfo):
        return tz
    raise TypeError("tz must be a timezone name or datetime.tzinfo")


def _localize_naive(
    value: datetime.datetime,
    tz: str | datetime.tzinfo | None,
    *,
    fold: int | None = None,
) -> datetime.datetime:
    zone = resolve_timezone(tz)
    if value.tzinfo is not None:
        return value.astimezone(zone)

    # pytz remains accepted at the public boundary for older external callers.
    localize = getattr(zone, "localize", None)
    if callable(localize):
        try:
            return localize(value, is_dst=None)
        except Exception as exc:  # pytz raises provider-specific DST errors
            raise ValueError(f"invalid or ambiguous local time: {value!s}") from exc

    candidates: list[datetime.datetime] = []
    for candidate_fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=candidate_fold)
        round_trip = candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
        if round_trip == value:
            candidates.append(candidate)

    if not candidates:
        raise ValueError(f"nonexistent local time: {value!s}")

    offsets = {candidate.utcoffset() for candidate in candidates}
    if len(offsets) > 1:
        if fold not in (0, 1):
            raise ValueError(f"ambiguous local time requires fold=0 or fold=1: {value!s}")
        return value.replace(tzinfo=zone, fold=fold)

    return candidates[0]


def ensure_aware_datetime(
    value: datetime.datetime,
    *,
    assume_tz: str | datetime.tzinfo | None = None,
    fold: int | None = None,
) -> datetime.datetime:
    """Return an aware datetime or reject host-local implicit conversion."""

    if not isinstance(value, datetime.datetime):
        raise TypeError("value must be datetime.datetime")
    if value.tzinfo is None:
        if assume_tz is None:
            raise ValueError("naive datetime requires an explicit assume_tz")
        return _localize_naive(value, assume_tz, fold=fold)
    return value


def get_logger(filename=None, level=logging.INFO) -> logging.Logger:
    """获取一个日志记录的对象。"""

    from tradingview_zy.config import get_data_path

    log_path = get_data_path() / "logs"
    if not log_path.is_dir():
        log_path.mkdir(parents=True)
    logger = logging.getLogger(f"{filename}")
    logger.setLevel(level)
    fmt = logging.Formatter("%(asctime)s - %(levelname)s : %(message)s")
    stream_handler = logging.StreamHandler()

    stream_exists = False
    file_exists = False
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            stream_exists = True
        if isinstance(handler, logging.FileHandler):
            file_exists = True
    if not stream_exists:
        logger.addHandler(stream_handler)

    if filename and not file_exists:
        file_handler = logging.FileHandler(
            filename=str(log_path / filename), encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def singleton(cls):
    """Thread-safe lazy singleton decorator.

    Construction is published only after the constructor returns successfully,
    so a failed first attempt is never cached.  ``reset_instance`` is provided
    for deterministic tests and explicit lifecycle ownership.
    """

    state: dict[str, Any] = {"instance": None}
    lock = threading.RLock()

    @wraps(cls)
    def wrapper(*args, **kwargs):
        instance = state["instance"]
        if instance is None:
            with lock:
                instance = state["instance"]
                if instance is None:
                    instance = cls(*args, **kwargs)
                    state["instance"] = instance
        return instance

    def reset_instance(_wrapper=None) -> None:
        with lock:
            state["instance"] = None

    wrapper.reset_instance = MethodType(reset_instance, wrapper)  # type: ignore[attr-defined]
    wrapper.singleton_lock = lock  # type: ignore[attr-defined]
    return wrapper


def timeint_to_datetime(
    value,
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
) -> datetime.datetime:
    """Convert Unix seconds to an aware datetime in an explicit timezone."""

    del _format  # retained for backward-compatible positional calls
    try:
        timestamp = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp must be numeric Unix seconds") from exc
    return datetime.datetime.fromtimestamp(timestamp, tz=resolve_timezone(tz))


def timeint_to_str(
    value,
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
) -> str:
    """Convert Unix seconds without consulting the host local timezone."""

    return timeint_to_datetime(value, tz=tz).strftime(_format)


def str_to_datetime(
    value,
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
    *,
    fold: int | None = None,
) -> datetime.datetime:
    """Parse exchange-local wall-clock text into an aware datetime."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("datetime text must be a non-empty string")
    parsed = datetime.datetime.strptime(value.strip(), _format)
    return _localize_naive(parsed, tz, fold=fold)


def str_to_timeint(
    value,
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
    *,
    fold: int | None = None,
) -> int:
    """Parse wall-clock text and return deterministic Unix seconds."""

    return int(str_to_datetime(value, _format, tz, fold=fold).timestamp())


def datetime_to_str(
    value: datetime.datetime,
    _format="%Y-%m-%d %H:%M:%S",
    *,
    tz: str | datetime.tzinfo | None = None,
    assume_tz: str | datetime.tzinfo | None = None,
) -> str:
    """Format a datetime, optionally converting it to ``tz`` first."""

    if not isinstance(value, datetime.datetime):
        raise TypeError("value must be datetime.datetime")
    if tz is None and assume_tz is None:
        return value.strftime(_format)
    aware = ensure_aware_datetime(value, assume_tz=assume_tz)
    if tz is not None:
        aware = aware.astimezone(resolve_timezone(tz))
    return aware.strftime(_format)


def datetime_to_int(
    value: datetime.datetime,
    *,
    assume_tz: str | datetime.tzinfo | None = None,
    fold: int | None = None,
) -> int:
    """Convert an aware datetime to Unix seconds.

    Naive datetimes are rejected unless the caller explicitly supplies the
    timezone whose wall-clock value they represent.
    """

    aware = ensure_aware_datetime(value, assume_tz=assume_tz, fold=fold)
    return int(aware.timestamp())


def str_add_seconds_to_str(
    value,
    seconds,
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
    *,
    fold: int | None = None,
) -> str:
    """Add seconds in an explicit timezone without host-local mktime/localtime."""

    parsed = str_to_datetime(value, _format, tz, fold=fold)
    return (parsed + datetime.timedelta(seconds=float(seconds))).strftime(_format)


def now_dt(
    _format="%Y-%m-%d %H:%M:%S",
    tz: str | datetime.tzinfo | None = None,
) -> str:
    """Return current time in the explicit project timezone."""

    return datetime.datetime.now(tz=resolve_timezone(tz)).strftime(_format)


def reverse_decimal_to_power_of_ten(decimal_number):
    """将小数转换为对应的小数点后位数的 10 的幂次方。"""

    if decimal_number <= 0 or decimal_number >= 1:
        return 1000
    decimal_str = str(decimal_number)
    num_zeros = 0
    if "." in decimal_str:
        num_zeros = len(decimal_str) - decimal_str.index(".") - 1
    if "e-" in decimal_str:
        num_zeros = int(decimal_str[decimal_str.index("e-") + 2 :])
    return 10**num_zeros


if __name__ == "__main__":
    for i in range(1, 10):
        dn = 1 / (10**i)
        print(dn, reverse_decimal_to_power_of_ten(dn))
