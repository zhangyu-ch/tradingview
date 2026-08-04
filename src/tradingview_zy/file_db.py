from __future__ import annotations

import contextlib
import datetime
import hashlib
import json
import math
import os
import pathlib
import random
import tempfile
import threading
import uuid
from typing import Any, Iterator, Union

import pandas as pd
import pytz

from tradingview_zy import fun
from tradingview_zy.base import Market
from tradingview_zy.config import get_data_path


class FileCacheError(RuntimeError):
    """Base class for cache persistence failures."""


class SafeCacheEncodingError(FileCacheError):
    """Raised when an object is outside the safe cache schema."""


class SafeCacheCorruptionError(FileCacheError):
    """Raised when a safe cache envelope fails validation."""


class UnsafeLegacyCacheError(FileCacheError):
    """Raised instead of executing a legacy pickle payload."""


_SAFE_CACHE_SCHEMA = "tradingview_zy.safe_cache"
_SAFE_CACHE_VERSION = 1
_KLINE_META_SCHEMA = "tradingview_zy.tdx_klines"
_KLINE_META_VERSION = 1
_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))
_POSITION_FIELDS = {
    "code",
    "signal",
    "mmd",
    "type",
    "balance",
    "release_balance",
    "price",
    "amount",
    "loss_price",
    "open_date",
    "open_datetime",
    "close_datetime",
    "fee",
    "profit",
    "profit_rate",
    "max_profit_rate",
    "max_loss_rate",
    "open_msg",
    "close_msg",
    "info",
    "open_uid",
    "now_pos_rate",
    "open_keys",
    "close_keys",
    "open_records",
    "close_records",
    "close_uid_profit",
}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _lock_for(path: pathlib.Path) -> threading.RLock:
    index = int(hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:8], 16)
    return _LOCK_STRIPES[index % len(_LOCK_STRIPES)]


def _chmod(path: pathlib.Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


def _ensure_directory(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, 0o700)


def _fsync_directory(path: pathlib.Path) -> None:
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def _atomic_write_bytes(path: pathlib.Path, data: bytes) -> None:
    _ensure_directory(path.parent)
    temp_name: str | None = None
    with _lock_for(path):
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temp_name = handle.name
                _chmod(pathlib.Path(temp_name), 0o600)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
            temp_name = None
            _chmod(path, 0o600)
            _fsync_directory(path.parent)
        finally:
            if temp_name is not None:
                with contextlib.suppress(OSError):
                    pathlib.Path(temp_name).unlink()


def _safe_basename(filename: str) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("cache filename must be a non-empty string")
    name = filename.strip()
    if (
        name in {".", ".."}
        or "/" in name
        or "\\" in name
        or pathlib.PurePath(name).name != name
        or len(name.encode("utf-8")) > 180
    ):
        raise ValueError("cache filename must be a short basename without path segments")
    return name


def _quarantine(path: pathlib.Path) -> pathlib.Path | None:
    if not path.exists():
        return None
    destination = path.with_name(
        f"{path.name}.corrupt.{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.{uuid.uuid4().hex[:8]}"
    )
    with _lock_for(path):
        try:
            os.replace(path, destination)
            _chmod(destination, 0o600)
            _fsync_directory(path.parent)
            return destination
        except OSError:
            return None


def _encode_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SafeCacheEncodingError("non-finite floats are not supported")
        return value
    # numpy scalar support without importing numpy as a hard dependency here.
    if hasattr(value, "item") and type(value).__module__.startswith("numpy"):
        return _encode_safe(value.item())
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime.datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, datetime.date):
        return {"__type__": "date", "value": value.isoformat()}
    if isinstance(value, list):
        return {"__type__": "list", "items": [_encode_safe(item) for item in value]}
    if isinstance(value, tuple):
        return {"__type__": "tuple", "items": [_encode_safe(item) for item in value]}
    if isinstance(value, set):
        items = [_encode_safe(item) for item in value]
        items.sort(key=lambda item: _canonical_bytes(item))
        return {"__type__": "set", "items": items}
    if isinstance(value, dict):
        return {
            "__type__": "dict",
            "items": [
                [_encode_safe(key), _encode_safe(item)] for key, item in value.items()
            ],
        }
    if isinstance(value, pd.DataFrame):
        return {
            "__type__": "dataframe",
            "columns": [_encode_safe(item) for item in value.columns.tolist()],
            "index": [_encode_safe(item) for item in value.index.tolist()],
            "data": [
                [_encode_safe(item) for item in row]
                for row in value.itertuples(index=False, name=None)
            ],
        }
    if isinstance(value, pd.Series):
        return {
            "__type__": "series",
            "name": _encode_safe(value.name),
            "index": [_encode_safe(item) for item in value.index.tolist()],
            "data": [_encode_safe(item) for item in value.tolist()],
        }
    # Import only the one trusted project domain type; the payload cannot name a class.
    from tradingview_zy.backtesting.base import POSITION

    if isinstance(value, POSITION):
        unexpected = set(vars(value)) - _POSITION_FIELDS
        if unexpected:
            raise SafeCacheEncodingError(
                f"POSITION contains unsupported fields: {sorted(unexpected)}"
            )
        return {
            "__type__": "position",
            "fields": _encode_safe(dict(vars(value))),
        }
    raise SafeCacheEncodingError(
        f"unsupported cache value type: {type(value).__module__}.{type(value).__qualname__}"
    )


def _decode_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise SafeCacheCorruptionError("non-finite float in cache")
        return value
    if not isinstance(value, dict) or set(value) - {"__type__", "value", "items", "columns", "index", "data", "name", "fields"}:
        raise SafeCacheCorruptionError("invalid safe cache value")
    kind = value.get("__type__")
    if kind == "datetime" and set(value) == {"__type__", "value"}:
        try:
            return datetime.datetime.fromisoformat(value["value"])
        except (TypeError, ValueError) as exc:
            raise SafeCacheCorruptionError("invalid datetime value") from exc
    if kind == "date" and set(value) == {"__type__", "value"}:
        try:
            return datetime.date.fromisoformat(value["value"])
        except (TypeError, ValueError) as exc:
            raise SafeCacheCorruptionError("invalid date value") from exc
    if kind in {"list", "tuple", "set"} and set(value) == {"__type__", "items"}:
        raw_items = value.get("items")
        if not isinstance(raw_items, list):
            raise SafeCacheCorruptionError(f"invalid {kind} items")
        items = [_decode_safe(item) for item in raw_items]
        if kind == "list":
            return items
        if kind == "tuple":
            return tuple(items)
        try:
            return set(items)
        except TypeError as exc:
            raise SafeCacheCorruptionError("unhashable set item") from exc
    if kind == "dict" and set(value) == {"__type__", "items"}:
        raw_items = value.get("items")
        if not isinstance(raw_items, list):
            raise SafeCacheCorruptionError("invalid dict items")
        result = {}
        for pair in raw_items:
            if not isinstance(pair, list) or len(pair) != 2:
                raise SafeCacheCorruptionError("invalid dict item")
            key = _decode_safe(pair[0])
            try:
                result[key] = _decode_safe(pair[1])
            except TypeError as exc:
                raise SafeCacheCorruptionError("unhashable dict key") from exc
        return result
    if kind == "dataframe" and set(value) == {"__type__", "columns", "index", "data"}:
        columns = [_decode_safe(item) for item in value.get("columns", [])]
        index = [_decode_safe(item) for item in value.get("index", [])]
        raw_data = value.get("data")
        if not isinstance(raw_data, list):
            raise SafeCacheCorruptionError("invalid dataframe data")
        data = [[_decode_safe(item) for item in row] for row in raw_data]
        if len(index) != len(data) or any(len(row) != len(columns) for row in data):
            raise SafeCacheCorruptionError("dataframe shape mismatch")
        return pd.DataFrame(data, columns=columns, index=index)
    if kind == "series" and set(value) == {"__type__", "name", "index", "data"}:
        index = [_decode_safe(item) for item in value.get("index", [])]
        data = [_decode_safe(item) for item in value.get("data", [])]
        if len(index) != len(data):
            raise SafeCacheCorruptionError("series shape mismatch")
        return pd.Series(data, index=index, name=_decode_safe(value.get("name")))
    if kind == "position" and set(value) == {"__type__", "fields"}:
        fields = _decode_safe(value.get("fields"))
        if not isinstance(fields, dict) or set(fields) - _POSITION_FIELDS:
            raise SafeCacheCorruptionError("invalid POSITION fields")
        from tradingview_zy.backtesting.base import POSITION

        code = fields.get("code")
        signal = fields.get("signal")
        if not isinstance(code, str) or not isinstance(signal, str):
            raise SafeCacheCorruptionError("POSITION code/signal must be strings")
        position = POSITION(code=code, signal=signal)
        for key, item in fields.items():
            setattr(position, key, item)
        return position
    raise SafeCacheCorruptionError(f"unsupported safe cache type tag: {kind!r}")


class FileCacheDB:
    """Atomic, schema-validated file cache."""

    def __init__(self):
        self.home_path = pathlib.Path.home()
        self.project_path = pathlib.Path(get_data_path())
        _ensure_directory(self.project_path)
        self.klines_path = self.project_path / "klines"
        _ensure_directory(self.klines_path)
        self.cache_pkl_path = self.project_path / "cache_pkl"
        _ensure_directory(self.cache_pkl_path)
        for market in Market:
            _ensure_directory(self.klines_path / market.value)
        self.tz = pytz.timezone("Asia/Shanghai")

    @staticmethod
    def atomic_write_json(path: pathlib.Path, value: Any) -> None:
        _atomic_write_bytes(
            pathlib.Path(path),
            (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        )

    @staticmethod
    def atomic_write_dataframe_csv(path: pathlib.Path, frame: pd.DataFrame) -> None:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        _atomic_write_bytes(pathlib.Path(path), frame.to_csv(index=False).encode("utf-8"))

    @staticmethod
    def read_dataframe_csv(path: pathlib.Path, **kwargs) -> Union[None, pd.DataFrame]:
        path = pathlib.Path(path)
        if not path.is_file():
            return None
        try:
            return pd.read_csv(path, **kwargs)
        except (PermissionError, BlockingIOError):
            return None
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            _quarantine(path)
            raise SafeCacheCorruptionError(f"invalid CSV cache {path.name}: {exc}") from exc

    def _kline_path(self, market: str, code: str, frequency: str) -> pathlib.Path:
        market_name = _safe_basename(str(market))
        code_name = _safe_basename(str(code).replace(".", "_"))
        frequency_name = _safe_basename(str(frequency))
        market_path = self.klines_path / market_name
        _ensure_directory(market_path)
        return market_path / f"{code_name}_{frequency_name}.csv"

    @staticmethod
    def _meta_path(csv_path: pathlib.Path) -> pathlib.Path:
        return csv_path.with_name(f"{csv_path.name}.meta.json")

    def get_tdx_klines(
        self,
        market: str,
        code: str,
        frequency: str,
        *,
        include_incomplete: bool = False,
    ) -> Union[None, pd.DataFrame]:
        file_pathname = self._kline_path(market, code, frequency)
        if not file_pathname.is_file():
            return None
        try:
            csv_bytes = file_pathname.read_bytes()
            klines = pd.read_csv(file_pathname)
        except (PermissionError, BlockingIOError):
            return None
        except (OSError, ValueError, pd.errors.ParserError) as exc:
            _quarantine(file_pathname)
            _quarantine(self._meta_path(file_pathname))
            raise SafeCacheCorruptionError(
                f"invalid K-line cache {file_pathname.name}: {exc}"
            ) from exc

        if "date" not in klines.columns:
            _quarantine(file_pathname)
            _quarantine(self._meta_path(file_pathname))
            raise SafeCacheCorruptionError("K-line cache has no date column")
        klines["date"] = pd.to_datetime(klines["date"], errors="coerce")
        if klines["date"].isnull().any():
            _quarantine(file_pathname)
            _quarantine(self._meta_path(file_pathname))
            raise SafeCacheCorruptionError("K-line cache has invalid date values")

        last_row_complete = False  # conservative compatibility for legacy CSV files
        meta_path = self._meta_path(file_pathname)
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                expected_keys = {
                    "schema",
                    "version",
                    "last_row_complete",
                    "row_count",
                    "csv_sha256",
                }
                if (
                    not isinstance(meta, dict)
                    or set(meta) != expected_keys
                    or meta["schema"] != _KLINE_META_SCHEMA
                    or meta["version"] != _KLINE_META_VERSION
                    or not isinstance(meta["last_row_complete"], bool)
                    or meta["row_count"] != len(klines)
                    or meta["csv_sha256"] != hashlib.sha256(csv_bytes).hexdigest()
                ):
                    raise ValueError("metadata mismatch")
                last_row_complete = meta["last_row_complete"]
            except (PermissionError, BlockingIOError):
                last_row_complete = False
            except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
                _quarantine(meta_path)
                # Keep a valid CSV and fall back to the conservative legacy rule.
                last_row_complete = False

        if not include_incomplete and not last_row_complete and len(klines) > 0:
            klines = klines.iloc[:-1].copy()

        if random.randint(0, 1000) <= 5:
            self.clear_tdx_old_klines(market)
        return klines

    def save_tdx_klines(
        self,
        market: str,
        code: str,
        frequency: str,
        kline: pd.DataFrame,
        *,
        last_row_complete: bool = False,
    ) -> bool:
        if not isinstance(kline, pd.DataFrame):
            raise TypeError("kline must be a pandas DataFrame")
        if "date" not in kline.columns:
            raise ValueError("kline must include a date column")
        file_pathname = self._kline_path(market, code, frequency)
        csv_bytes = kline.to_csv(index=False).encode("utf-8")
        meta = {
            "schema": _KLINE_META_SCHEMA,
            "version": _KLINE_META_VERSION,
            "last_row_complete": bool(last_row_complete),
            "row_count": len(kline),
            "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        }
        # CSV and metadata are individually atomic. The conservative read fallback
        # prevents an interleaving reader from treating an unknown final bar as complete.
        _atomic_write_bytes(file_pathname, csv_bytes)
        self.atomic_write_json(self._meta_path(file_pathname), meta)
        return True

    def clear_tdx_old_klines(self, market: str) -> bool:
        del_lt_times = fun.datetime_to_int(
            datetime.datetime.now(datetime.timezone.utc)
        ) - (15 * 24 * 60 * 60)
        market_path = self.klines_path / _safe_basename(str(market))
        for filename in market_path.glob("*.csv"):
            try:
                if filename.stat().st_mtime < del_lt_times:
                    filename.unlink()
                    with contextlib.suppress(OSError):
                        self._meta_path(filename).unlink()
            except OSError:
                pass
        return True

    def _safe_state_path(self, filename: str) -> tuple[pathlib.Path, tuple[pathlib.Path, ...]]:
        name = _safe_basename(filename)
        stem = name[:-4] if name.lower().endswith(".pkl") else name
        if stem.lower().endswith(".json"):
            stem = stem[:-5]
        if not stem:
            raise ValueError("cache filename must contain a stem")
        json_path = self.cache_pkl_path / f"{stem}.json"
        legacy = tuple(
            dict.fromkeys(
                [self.cache_pkl_path / name, self.cache_pkl_path / f"{stem}.pkl"]
            )
        )
        return json_path, legacy

    def cache_pkl_to_file(self, filename: str, data: object) -> bool:
        """Compatibility name for the safe, non-executable state cache."""
        path, _ = self._safe_state_path(filename)
        encoded = _encode_safe(data)
        envelope = {
            "schema": _SAFE_CACHE_SCHEMA,
            "version": _SAFE_CACHE_VERSION,
            "payload": encoded,
            "sha256": _digest(encoded),
        }
        self.atomic_write_json(path, envelope)
        return True

    def cache_pkl_from_file(self, filename: str) -> object:
        """Read safe JSON state; never execute a legacy pickle."""
        path, legacy_candidates = self._safe_state_path(filename)
        if not path.is_file():
            for legacy in legacy_candidates:
                if legacy != path and legacy.is_file():
                    raise UnsafeLegacyCacheError(
                        f"legacy pickle cache {legacy.name!r} is not loaded; regenerate it"
                    )
            return None
        try:
            raw = path.read_text(encoding="utf-8")
            envelope = json.loads(raw)
            if (
                not isinstance(envelope, dict)
                or set(envelope) != {"schema", "version", "payload", "sha256"}
                or envelope["schema"] != _SAFE_CACHE_SCHEMA
                or envelope["version"] != _SAFE_CACHE_VERSION
                or not isinstance(envelope["sha256"], str)
                or envelope["sha256"] != _digest(envelope["payload"])
            ):
                raise SafeCacheCorruptionError("safe cache envelope mismatch")
            return _decode_safe(envelope["payload"])
        except (PermissionError, BlockingIOError):
            return None
        except UnsafeLegacyCacheError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, SafeCacheCorruptionError) as exc:
            _quarantine(path)
            if isinstance(exc, SafeCacheCorruptionError):
                raise
            raise SafeCacheCorruptionError(f"invalid safe cache {path.name}: {exc}") from exc


fdb = FileCacheDB()
