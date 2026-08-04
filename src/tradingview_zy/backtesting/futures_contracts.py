"""Versioned futures margin and fee parameter loading.

The bundled data was migrated verbatim from the historical module-level mapping.
A backtest must name an immutable version and prove that the requested date range
and instruments are covered before any market data is loaded.
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import json
import math
import re
from importlib import resources
from typing import Any, Iterable, Mapping

_DATA_FILE = "futures_parameters.json"
_REQUIRED_FIELDS = (
    "symbol_size",
    "margin_rate_long",
    "margin_rate_short",
    "fee_rate_open",
    "fee_rate_close",
    "fee_rate_close_today",
)
_PRODUCT_RE = re.compile(r"^[A-Za-z]+")


class FuturesParameterError(ValueError):
    """Raised when a futures parameter version or snapshot is invalid."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _as_date(value: Any, *, field: str) -> _dt.date:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise FuturesParameterError(f"{field} must not be empty")
        try:
            return _dt.datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return _dt.date.fromisoformat(text[:10])
            except ValueError as exc:
                raise FuturesParameterError(f"{field} is not an ISO date/datetime: {value!r}") from exc
    raise FuturesParameterError(f"{field} must be a date, datetime, or ISO string")


def normalize_futures_code(code: str) -> str:
    """Return the canonical ``EXCHANGE.PRODUCT`` key.

    Accepted examples include product keys (``DCE.M``), concrete contracts
    (``DCE.m2501``), and TQ continuous symbols (``KQ.m@DCE.M``).
    """
    if not isinstance(code, str) or not code.strip():
        raise FuturesParameterError("futures code must be a non-empty string")
    text = code.strip()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if ":" in text and "." not in text:
        text = text.replace(":", ".", 1)
    if "." not in text:
        raise FuturesParameterError(f"futures code must include exchange and product: {code!r}")
    exchange, raw_product = text.split(".", 1)
    exchange = exchange.strip().upper()
    raw_product = raw_product.strip()
    match = _PRODUCT_RE.match(raw_product)
    if not exchange or match is None:
        raise FuturesParameterError(f"invalid futures code: {code!r}")
    return f"{exchange}.{match.group(0).upper()}"


def _validate_contract(code: str, raw: Mapping[str, Any]) -> dict[str, float | int]:
    if not isinstance(raw, Mapping):
        raise FuturesParameterError(f"contract {code} must be an object")
    missing = [name for name in _REQUIRED_FIELDS if name not in raw]
    extra = sorted(set(raw) - set(_REQUIRED_FIELDS))
    if missing or extra:
        raise FuturesParameterError(
            f"contract {code} fields invalid; missing={missing}, extra={extra}"
        )
    result: dict[str, float | int] = {}
    for name in _REQUIRED_FIELDS:
        value = raw[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FuturesParameterError(f"contract {code}.{name} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or numeric < 0:
            raise FuturesParameterError(f"contract {code}.{name} must be finite and non-negative")
        if name == "symbol_size":
            if numeric <= 0 or not numeric.is_integer():
                raise FuturesParameterError(f"contract {code}.symbol_size must be a positive integer")
            result[name] = int(numeric)
        elif name.startswith("margin_rate"):
            if numeric <= 0 or numeric > 1:
                raise FuturesParameterError(f"contract {code}.{name} must be in (0, 1]")
            result[name] = numeric
        else:
            result[name] = numeric
    return result


def _load_dataset() -> dict[str, Any]:
    try:
        text = resources.files(__package__).joinpath(_DATA_FILE).read_text(encoding="utf-8")
        raw = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise FuturesParameterError(f"cannot load bundled futures parameter dataset: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        raise FuturesParameterError("unsupported futures parameter dataset schema")
    if raw.get("dataset_id") != "tradingview_zy.futures_parameters":
        raise FuturesParameterError("unexpected futures parameter dataset id")
    versions = raw.get("versions")
    if not isinstance(versions, list) or not versions:
        raise FuturesParameterError("futures parameter dataset has no versions")
    seen: set[str] = set()
    normalized_versions: list[dict[str, Any]] = []
    for item in versions:
        if not isinstance(item, dict):
            raise FuturesParameterError("futures parameter version must be an object")
        version = item.get("version")
        if not isinstance(version, str) or not version.strip() or version in seen:
            raise FuturesParameterError(f"invalid or duplicate futures parameter version: {version!r}")
        seen.add(version)
        effective_from = _as_date(item.get("effective_from"), field="effective_from")
        effective_to_raw = item.get("effective_to")
        effective_to = (
            _as_date(effective_to_raw, field="effective_to")
            if effective_to_raw is not None
            else None
        )
        if effective_to is not None and effective_to < effective_from:
            raise FuturesParameterError(f"version {version} has an inverted effective range")
        contracts_raw = item.get("contracts")
        if not isinstance(contracts_raw, dict) or not contracts_raw:
            raise FuturesParameterError(f"version {version} has no contracts")
        contracts: dict[str, dict[str, float | int]] = {}
        for raw_code, contract in contracts_raw.items():
            canonical = normalize_futures_code(raw_code)
            if canonical != raw_code:
                raise FuturesParameterError(
                    f"dataset contract key {raw_code!r} is not canonical ({canonical})"
                )
            if canonical in contracts:
                raise FuturesParameterError(f"duplicate contract {canonical}")
            contracts[canonical] = _validate_contract(canonical, contract)
        sources = item.get("sources")
        provenance = item.get("provenance")
        if not isinstance(sources, list) or not sources:
            raise FuturesParameterError(f"version {version} must declare sources")
        if not isinstance(provenance, dict):
            raise FuturesParameterError(f"version {version} must declare provenance")
        normalized = {
            "version": version,
            "effective_from": effective_from.isoformat(),
            "effective_to": effective_to.isoformat() if effective_to else None,
            "source_date": str(item.get("source_date") or ""),
            "sources": copy.deepcopy(sources),
            "provenance": copy.deepcopy(provenance),
            "contracts": contracts,
        }
        normalized["dataset_sha256"] = _sha256(normalized)
        normalized_versions.append(normalized)
    return {
        "schema_version": 1,
        "dataset_id": raw["dataset_id"],
        "versions": normalized_versions,
    }


def available_futures_parameter_versions() -> tuple[str, ...]:
    return tuple(item["version"] for item in _load_dataset()["versions"])


def build_futures_parameter_manifest(
    *,
    version: str,
    start_datetime: Any,
    end_datetime: Any,
    codes: Iterable[str],
) -> dict[str, Any]:
    if not isinstance(version, str) or not version.strip():
        raise FuturesParameterError(
            "futures_parameter_version is required for futures backtests"
        )
    start_date = _as_date(start_datetime, field="start_datetime")
    end_date = _as_date(end_datetime, field="end_datetime")
    if end_date < start_date:
        raise FuturesParameterError("end_datetime must be on or after start_datetime")
    requested = tuple(dict.fromkeys(normalize_futures_code(code) for code in codes))
    if not requested:
        raise FuturesParameterError("futures backtest must include at least one code")
    dataset = _load_dataset()
    selected = next(
        (item for item in dataset["versions"] if item["version"] == version.strip()),
        None,
    )
    if selected is None:
        raise FuturesParameterError(
            f"unknown futures parameter version {version!r}; "
            f"available={available_futures_parameter_versions()}"
        )
    effective_from = _dt.date.fromisoformat(selected["effective_from"])
    effective_to = (
        _dt.date.fromisoformat(selected["effective_to"])
        if selected["effective_to"]
        else None
    )
    if start_date < effective_from or (effective_to is not None and end_date > effective_to):
        raise FuturesParameterError(
            f"version {selected['version']} does not cover {start_date}..{end_date}; "
            f"effective={effective_from}..{effective_to or 'open'}"
        )
    missing = [code for code in requested if code not in selected["contracts"]]
    if missing:
        raise FuturesParameterError(
            f"version {selected['version']} does not define contracts: {missing}"
        )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": dataset["dataset_id"],
        "version": selected["version"],
        "effective_from": selected["effective_from"],
        "effective_to": selected["effective_to"],
        "source_date": selected["source_date"],
        "sources": copy.deepcopy(selected["sources"]),
        "provenance": copy.deepcopy(selected["provenance"]),
        "dataset_sha256": selected["dataset_sha256"],
        "requested_products": list(requested),
        "contracts": copy.deepcopy(selected["contracts"]),
    }
    manifest["snapshot_sha256"] = _sha256(manifest)
    return manifest


def validate_futures_parameter_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        raise FuturesParameterError("futures parameter manifest must be an object")
    candidate = copy.deepcopy(dict(manifest))
    supplied_hash = candidate.pop("snapshot_sha256", None)
    if not isinstance(supplied_hash, str) or not supplied_hash:
        raise FuturesParameterError("futures parameter manifest has no snapshot_sha256")
    actual_hash = _sha256(candidate)
    if actual_hash != supplied_hash:
        raise FuturesParameterError("futures parameter manifest hash mismatch")
    if candidate.get("schema_version") != 1:
        raise FuturesParameterError("unsupported futures parameter manifest schema")
    if candidate.get("dataset_id") != "tradingview_zy.futures_parameters":
        raise FuturesParameterError("unexpected futures parameter manifest dataset id")
    contracts_raw = candidate.get("contracts")
    if not isinstance(contracts_raw, dict) or not contracts_raw:
        raise FuturesParameterError("futures parameter manifest has no contracts")
    contracts = {
        normalize_futures_code(code): _validate_contract(normalize_futures_code(code), raw)
        for code, raw in contracts_raw.items()
    }
    requested_raw = candidate.get("requested_products")
    if not isinstance(requested_raw, list) or not requested_raw:
        raise FuturesParameterError("futures parameter manifest has no requested_products")
    requested = [normalize_futures_code(code) for code in requested_raw]
    missing = [code for code in requested if code not in contracts]
    if missing:
        raise FuturesParameterError(f"futures parameter manifest is missing contracts: {missing}")
    # Verify that immutable version metadata still matches the bundled version record.
    dataset = _load_dataset()
    selected = next(
        (item for item in dataset["versions"] if item["version"] == candidate.get("version")),
        None,
    )
    if selected is None:
        raise FuturesParameterError(f"unknown futures parameter manifest version: {candidate.get('version')!r}")
    if candidate.get("dataset_sha256") != selected["dataset_sha256"]:
        raise FuturesParameterError("futures parameter dataset hash mismatch")
    candidate["contracts"] = contracts
    candidate["requested_products"] = requested
    candidate["snapshot_sha256"] = supplied_hash
    return candidate


def contract_parameters(manifest: Mapping[str, Any], code: str) -> dict[str, float | int]:
    checked = validate_futures_parameter_manifest(manifest)
    canonical = normalize_futures_code(code)
    try:
        return copy.deepcopy(checked["contracts"][canonical])
    except KeyError as exc:
        raise FuturesParameterError(f"manifest does not define contract {canonical}") from exc
