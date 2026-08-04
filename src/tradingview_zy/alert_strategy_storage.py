"""Validation and serialization boundaries for alert strategy persistence."""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

STRATEGY_CONFIG_MAX_BYTES = 32 * 1024
STRATEGY_MEMO_MAX_BYTES = 8 * 1024


class StrategyStorageValidationError(ValueError):
    """Raised when a strategy configuration cannot be safely persisted."""


def _utf8_length(value: str, *, field: str) -> int:
    if not isinstance(value, str):
        raise StrategyStorageValidationError(f"{field} 必须是字符串")
    if "\x00" in value:
        raise StrategyStorageValidationError(f"{field} 不能包含 NUL 字符")
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise StrategyStorageValidationError(f"{field} 包含非法 Unicode") from error


def _validate_json_value(value: Any, *, path: str = "strategy_config") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise StrategyStorageValidationError(f"{path} 不能包含 NaN 或 Infinity")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise StrategyStorageValidationError(f"{path} 的键必须是字符串")
            _validate_json_value(item, path=f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            _validate_json_value(item, path=f"{path}[{index}]")
        return
    raise StrategyStorageValidationError(
        f"{path} 只能包含 JSON 标准类型，不能包含 {type(value).__name__}"
    )


def _reject_json_constant(value: str):
    raise StrategyStorageValidationError(f"strategy_config 不能包含 {value}")


def parse_strategy_kwargs(raw: str | None) -> dict[str, Any]:
    """Parse request JSON only after applying the raw UTF-8 byte boundary."""
    text = "{}" if raw in (None, "") else raw
    if _utf8_length(text, field="strategy_kwargs") > STRATEGY_CONFIG_MAX_BYTES:
        raise StrategyStorageValidationError(
            f"strategy_kwargs 超过 {STRATEGY_CONFIG_MAX_BYTES} UTF-8 字节"
        )
    try:
        value = json.loads(text, parse_constant=_reject_json_constant)
    except StrategyStorageValidationError:
        raise
    except json.JSONDecodeError as error:
        raise StrategyStorageValidationError(
            f"strategy_kwargs 必须是合法 JSON：{error.msg}"
        ) from error
    if not isinstance(value, dict):
        raise StrategyStorageValidationError("strategy_kwargs 必须是 JSON 对象")
    _validate_json_value(value, path="strategy_kwargs")
    return value


def normalize_strategy_config(value: str | Mapping[str, Any]) -> str:
    """Return canonical JSON text that is safe for the configured TEXT boundary."""
    if isinstance(value, str):
        if _utf8_length(value, field="strategy_config") > STRATEGY_CONFIG_MAX_BYTES:
            raise StrategyStorageValidationError(
                f"strategy_config 超过 {STRATEGY_CONFIG_MAX_BYTES} UTF-8 字节"
            )
        try:
            parsed = json.loads(value, parse_constant=_reject_json_constant)
        except StrategyStorageValidationError:
            raise
        except json.JSONDecodeError as error:
            raise StrategyStorageValidationError(
                f"strategy_config 必须是合法 JSON：{error.msg}"
            ) from error
    elif isinstance(value, Mapping):
        parsed = dict(value)
    else:
        raise StrategyStorageValidationError("strategy_config 必须是 JSON 对象或字符串")

    if not isinstance(parsed, dict):
        raise StrategyStorageValidationError("strategy_config 必须是 JSON 对象")
    _validate_json_value(parsed)
    try:
        canonical = json.dumps(
            parsed,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise StrategyStorageValidationError(f"strategy_config 无法序列化：{error}") from error
    if _utf8_length(canonical, field="strategy_config") > STRATEGY_CONFIG_MAX_BYTES:
        raise StrategyStorageValidationError(
            f"strategy_config 超过 {STRATEGY_CONFIG_MAX_BYTES} UTF-8 字节"
        )
    return canonical


def build_strategy_config(strategy_id: str, strategy_kwargs: Mapping[str, Any]) -> str:
    if not isinstance(strategy_id, str) or not strategy_id.strip():
        raise StrategyStorageValidationError("strategy_id 不能为空")
    return normalize_strategy_config(
        {"strategy_id": strategy_id.strip(), "strategy_kwargs": dict(strategy_kwargs)}
    )


def normalize_strategy_memo(value: str | None) -> str:
    memo = "" if value is None else value
    if _utf8_length(memo, field="strategy_memo") > STRATEGY_MEMO_MAX_BYTES:
        raise StrategyStorageValidationError(
            f"strategy_memo 超过 {STRATEGY_MEMO_MAX_BYTES} UTF-8 字节"
        )
    return memo
