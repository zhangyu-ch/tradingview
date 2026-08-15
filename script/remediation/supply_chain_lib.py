#!/usr/bin/env python3
"""Deterministic supply-chain evidence helpers for the locked Python graph."""
from __future__ import annotations

import datetime as dt
import email
import hashlib
import importlib.metadata
import json
import re
import tomllib
import urllib.parse
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

UV_VERSION = "0.10.0"
CYCLONEDX_SPEC_VERSION = "1.6"
SUPPLY_CHAIN_DIR = Path("audit/supply-chain")
LOCAL_ARTIFACTS_FILE = SUPPLY_CHAIN_DIR / "local-artifacts.json"
SBOM_FILE = SUPPLY_CHAIN_DIR / "sbom.cdx.json"
LICENSE_REPORT_FILE = SUPPLY_CHAIN_DIR / "license-report.json"
VULNERABILITY_REPORT_FILE = SUPPLY_CHAIN_DIR / "vulnerability-report.json"
VULNERABILITY_POLICY_FILE = SUPPLY_CHAIN_DIR / "vulnerability-policy.json"


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", str(value).strip()).lower()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    algorithm, separator, digest = value.partition(":")
    if separator and algorithm.lower() == "sha256" and re.fullmatch(r"[0-9a-f]{64}", digest):
        return digest
    return None


def _lock_groups(root: Path) -> list[dict[str, Any]]:
    lock = load_toml(root / "uv.lock")
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for package in lock.get("package", []):
        name = str(package.get("name", ""))
        version = str(package.get("version", ""))
        key = (normalize_name(name), version)
        item = grouped.setdefault(
            key,
            {
                "name": name,
                "normalized_name": normalize_name(name),
                "version": version,
                "source_kinds": set(),
                "resolution_markers": set(),
                "local_paths": set(),
                "hashes": set(),
                "dependency_names": set(),
            },
        )
        source = package.get("source", {})
        if isinstance(source, Mapping):
            for source_kind in sorted(source):
                item["source_kinds"].add(str(source_kind))
            local_path = source.get("path")
            if isinstance(local_path, str):
                item["local_paths"].add(local_path)
        for marker in package.get("resolution-markers", []) or []:
            item["resolution_markers"].add(str(marker))
        sdist = package.get("sdist")
        if isinstance(sdist, Mapping):
            digest = _hash_value(sdist.get("hash"))
            if digest:
                item["hashes"].add(digest)
        for wheel in package.get("wheels", []) or []:
            if isinstance(wheel, Mapping):
                digest = _hash_value(wheel.get("hash"))
                if digest:
                    item["hashes"].add(digest)
        for dependency in package.get("dependencies", []) or []:
            if isinstance(dependency, Mapping) and dependency.get("name"):
                item["dependency_names"].add(normalize_name(str(dependency["name"])))
    result: list[dict[str, Any]] = []
    for item in grouped.values():
        result.append(
            {
                **item,
                "source_kinds": sorted(item["source_kinds"]),
                "resolution_markers": sorted(item["resolution_markers"]),
                "local_paths": sorted(item["local_paths"]),
                "hashes": sorted(item["hashes"]),
                "dependency_names": sorted(item["dependency_names"]),
            }
        )
    return sorted(result, key=lambda entry: (entry["normalized_name"], entry["version"]))


def locked_components(root: Path) -> list[dict[str, Any]]:
    return _lock_groups(root.resolve())


def osv_packages(root: Path) -> list[dict[str, str]]:
    packages = []
    for component in locked_components(root):
        if "virtual" in component["source_kinds"]:
            continue
        packages.append(
            {
                "name": component["normalized_name"],
                "version": component["version"],
            }
        )
    return packages


def read_wheel_metadata(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_paths = sorted(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        if len(metadata_paths) != 1:
            raise ValueError(f"{path}: expected one METADATA file, found {metadata_paths}")
        metadata_path = metadata_paths[0]
        message = email.message_from_bytes(archive.read(metadata_path))
        license_paths = sorted(
            name
            for name in names
            if ".dist-info/licenses/" in name and not name.endswith("/")
        )
        license_files = [
            {"path": name, "sha256": sha256_bytes(archive.read(name))}
            for name in license_paths
        ]
    classifiers = [
        value
        for value in message.get_all("Classifier", [])
        if value.startswith("License ::")
    ]
    return {
        "home_page": message.get("Home-page"),
        "license": message.get("License"),
        "license_classifiers": classifiers,
        "license_expression": message.get("License-Expression"),
        "license_files": license_files,
        "metadata_path": metadata_path,
        "name": message.get("Name"),
        "project_urls": sorted(message.get_all("Project-URL", [])),
        "summary": message.get("Summary"),
        "version": message.get("Version"),
    }


def _load_local_artifact_manifest(root: Path) -> Mapping[str, Any]:
    payload = load_json(root / LOCAL_ARTIFACTS_FILE)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("artifacts"), list):
        raise ValueError("local-artifacts.json must contain an artifacts list")
    return payload


def local_artifact_manifest(root: Path) -> list[dict[str, Any]]:
    return _load_local_artifact_manifest(root)["artifacts"]


def _pyproject_local_sources(root: Path) -> dict[str, dict[str, Any]]:
    project = load_toml(root / "pyproject.toml")
    sources = project.get("tool", {}).get("uv", {}).get("sources", {})
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(sources, Mapping):
        return result
    for package, raw_entries in sources.items():
        entries = raw_entries if isinstance(raw_entries, list) else [raw_entries]
        for entry in entries:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
                continue
            result[entry["path"]] = {
                "package": normalize_name(str(package)),
                "marker": entry.get("marker"),
            }
    return result


def _lock_local_sources(root: Path) -> dict[str, dict[str, Any]]:
    lock = load_toml(root / "uv.lock")
    result: dict[str, dict[str, Any]] = {}
    for package in lock.get("package", []) or []:
        source = package.get("source", {})
        if not isinstance(source, Mapping) or not isinstance(source.get("path"), str):
            continue
        hashes = {
            digest
            for wheel in package.get("wheels", []) or []
            if isinstance(wheel, Mapping)
            for digest in [_hash_value(wheel.get("hash"))]
            if digest
        }
        result[source["path"]] = {
            "package": normalize_name(str(package.get("name", ""))),
            "version": str(package.get("version", "")),
            "hashes": sorted(hashes),
        }
    return result


def validate_local_artifacts(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    manifest_path = root / LOCAL_ARTIFACTS_FILE
    if not manifest_path.is_file():
        return [f"missing {LOCAL_ARTIFACTS_FILE.as_posix()}"]
    try:
        manifest = _load_local_artifact_manifest(root)
        entries = manifest["artifacts"]
    except Exception as error:
        return [f"invalid local artifact manifest: {error}"]
    if manifest.get("lock_sha256") != sha256_file(root / "uv.lock"):
        errors.append("local artifact manifest lock_sha256 differs from uv.lock")

    paths = [entry.get("path") for entry in entries if isinstance(entry, Mapping)]
    if len(paths) != len(set(paths)):
        errors.append("local artifact manifest contains duplicate paths")
    expected_paths = {str(value) for value in paths if isinstance(value, str)}
    package_dir = root / "package"
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in package_dir.iterdir()
        if path.is_file()
    } if package_dir.is_dir() else set()
    for path in sorted(actual_paths - expected_paths):
        errors.append(f"untracked local artifact: {path}")
    for path in sorted(expected_paths - actual_paths):
        errors.append(f"missing local artifact: {path}")

    pyproject_sources = _pyproject_local_sources(root)
    lock_sources = _lock_local_sources(root)
    if set(pyproject_sources) != expected_paths:
        errors.append(
            "pyproject local source drift: "
            f"missing={sorted(expected_paths - set(pyproject_sources))}, "
            f"extra={sorted(set(pyproject_sources) - expected_paths)}"
        )
    if set(lock_sources) != expected_paths:
        errors.append(
            "uv.lock local source drift: "
            f"missing={sorted(expected_paths - set(lock_sources))}, "
            f"extra={sorted(set(lock_sources) - expected_paths)}"
        )

    required_provenance = (
        "origin",
        "origin_type",
        "acquisition_evidence",
        "upstream_project",
        "license_review",
    )
    for raw_entry in entries:
        if not isinstance(raw_entry, Mapping):
            errors.append("local artifact entry must be an object")
            continue
        relative = raw_entry.get("path")
        if not isinstance(relative, str):
            errors.append("local artifact entry is missing path")
            continue
        for key in required_provenance:
            value = raw_entry.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{relative}: missing provenance field {key}")
        path = root / relative
        if not path.is_file():
            continue
        size = path.stat().st_size
        digest = sha256_file(path)
        if raw_entry.get("size") != size:
            errors.append(f"{relative}: size mismatch")
        if raw_entry.get("sha256") != digest:
            errors.append(f"{relative}: sha256 mismatch")
        project_entry = pyproject_sources.get(relative)
        if project_entry:
            if normalize_name(str(raw_entry.get("package", ""))) != project_entry["package"]:
                errors.append(f"{relative}: package name differs from pyproject source")
            if raw_entry.get("marker") != project_entry["marker"]:
                errors.append(f"{relative}: marker differs from pyproject source")
        lock_entry = lock_sources.get(relative)
        if lock_entry:
            if normalize_name(str(raw_entry.get("package", ""))) != lock_entry["package"]:
                errors.append(f"{relative}: package name differs from uv.lock")
            if str(raw_entry.get("version", "")) != lock_entry["version"]:
                errors.append(f"{relative}: version differs from uv.lock")
            if digest not in lock_entry["hashes"]:
                errors.append(f"{relative}: sha256 is not locked in uv.lock")
        try:
            metadata = read_wheel_metadata(path)
        except Exception as error:
            errors.append(f"{relative}: wheel metadata error: {error}")
        else:
            if raw_entry.get("wheel_metadata") != metadata:
                errors.append(f"{relative}: wheel metadata evidence is stale")
        if raw_entry.get("upstream_download_url") is None:
            evidence = str(raw_entry.get("acquisition_evidence", "")).lower()
            if "unknown" not in evidence and "not inferred" not in evidence:
                errors.append(
                    f"{relative}: missing download URL must be explicitly documented as unknown"
                )
    return sorted(set(errors))


def _component_ref(component: Mapping[str, Any]) -> str:
    name = urllib.parse.quote(component["normalized_name"], safe="-._~")
    version = urllib.parse.quote(component["version"], safe="-._~")
    return f"pkg:pypi/{name}@{version}"


def build_sbom(root: Path) -> dict[str, Any]:
    root = root.resolve()
    lock_digest = sha256_file(root / "uv.lock")
    components = locked_components(root)
    refs_by_name: dict[str, list[str]] = defaultdict(list)
    for component in components:
        refs_by_name[component["normalized_name"]].append(_component_ref(component))

    sbom_components = []
    dependencies = []
    for component in components:
        ref = _component_ref(component)
        entry: dict[str, Any] = {
            "bom-ref": ref,
            "type": "application" if "virtual" in component["source_kinds"] else "library",
            "name": component["name"],
            "version": component["version"],
            "purl": ref,
            "properties": [
                {
                    "name": "tradingview:source-kinds",
                    "value": json.dumps(component["source_kinds"], separators=(",", ":")),
                },
                {
                    "name": "tradingview:resolution-markers",
                    "value": json.dumps(component["resolution_markers"], separators=(",", ":")),
                },
                {
                    "name": "tradingview:local-paths",
                    "value": json.dumps(component["local_paths"], separators=(",", ":")),
                },
            ],
        }
        if component["hashes"]:
            entry["hashes"] = [
                {"alg": "SHA-256", "content": digest}
                for digest in component["hashes"]
            ]
        sbom_components.append(entry)
        depends_on = sorted(
            {
                ref_value
                for name in component["dependency_names"]
                for ref_value in refs_by_name.get(name, [])
            }
        )
        dependencies.append({"ref": ref, "dependsOn": depends_on})

    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'tradingview-zy:{lock_digest}')}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "tradingview-zy",
                "version": "1.0.0",
            },
            "properties": [
                {"name": "tradingview:uv-lock-sha256", "value": lock_digest},
                {"name": "tradingview:uv-version", "value": UV_VERSION},
            ],
        },
        "components": sbom_components,
        "dependencies": dependencies,
    }


def _installed_license_index() -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        version = distribution.version
        if not name or not version:
            continue
        result[(normalize_name(name), str(version))] = {
            "license": distribution.metadata.get("License"),
            "license_expression": distribution.metadata.get("License-Expression"),
            "license_classifiers": [
                value
                for value in distribution.metadata.get_all("Classifier", [])
                if value.startswith("License ::")
            ],
        }
    return result


def build_license_report(root: Path, *, installed: bool = False) -> dict[str, Any]:
    root = root.resolve()
    local_by_package = {
        (normalize_name(str(entry.get("package", ""))), str(entry.get("version", ""))): entry
        for entry in local_artifact_manifest(root)
    }
    installed_index = _installed_license_index() if installed else {}
    components = []
    for component in locked_components(root):
        key = (component["normalized_name"], component["version"])
        local = local_by_package.get(key)
        evidence: dict[str, Any] = {
            "name": component["name"],
            "normalized_name": component["normalized_name"],
            "version": component["version"],
            "source_kinds": component["source_kinds"],
            "license": None,
            "license_expression": None,
            "license_classifiers": [],
            "license_files": [],
            "review": "metadata-unavailable-offline",
        }
        if local:
            wheel = local.get("wheel_metadata", {})
            evidence.update(
                {
                    "license": wheel.get("license"),
                    "license_expression": wheel.get("license_expression"),
                    "license_classifiers": wheel.get("license_classifiers", []),
                    "license_files": wheel.get("license_files", []),
                    "review": local.get("license_review"),
                }
            )
        if key in installed_index:
            evidence.update(installed_index[key])
            evidence["review"] = "installed-metadata"
        components.append(evidence)
    return {
        "schema_version": 1,
        "source": "uv.lock + local wheel evidence" + (" + installed metadata" if installed else ""),
        "uv_lock_sha256": sha256_file(root / "uv.lock"),
        "component_count": len(components),
        "components": components,
        "limitations": [
            "This is a metadata inventory, not legal advice.",
            "Registry package license metadata is enriched only in an installed environment."
            if not installed
            else "Installed metadata may still omit or misstate licensing terms.",
        ],
    }


def build_offline_vulnerability_report(root: Path) -> dict[str, Any]:
    packages = osv_packages(root)
    return {
        "schema_version": 1,
        "status": "not-run-offline",
        "scan_completed": False,
        "package_count": len(packages),
        "advisories": [],
        "unwaived_advisory_count": None,
        "note": (
            "No network query was performed while generating committed evidence. "
            "An empty advisory list is not a security conclusion; CI runs the live OSV scan."
        ),
    }


def validate_vulnerability_policy(payload: Any, *, today: dt.date | None = None) -> list[str]:
    today = today or dt.date.today()
    errors: list[str] = []
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        return ["vulnerability policy must be an object with schema_version 1"]
    exceptions = payload.get("exceptions")
    if not isinstance(exceptions, list):
        return ["vulnerability policy exceptions must be a list"]
    seen: set[tuple[str, str]] = set()
    for index, exception in enumerate(exceptions):
        prefix = f"exceptions[{index}]"
        if not isinstance(exception, Mapping):
            errors.append(f"{prefix} must be an object")
            continue
        values: dict[str, str] = {}
        for field in ("id", "package", "owner", "reason", "expires"):
            value = exception.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{prefix}.{field} is required")
            else:
                values[field] = value.strip()
        if "package" in values:
            values["package"] = normalize_name(values["package"])
        if "id" in values and "package" in values:
            key = (values["id"], values["package"])
            if key in seen:
                errors.append(f"duplicate vulnerability exception: {key[0]} / {key[1]}")
            seen.add(key)
        if "expires" in values:
            try:
                expiry = dt.date.fromisoformat(values["expires"])
            except ValueError:
                errors.append(f"{prefix}.expires must be YYYY-MM-DD")
            else:
                if expiry < today:
                    errors.append(f"{prefix} expired on {expiry.isoformat()}")
    return errors


def load_vulnerability_policy(root: Path, *, today: dt.date | None = None) -> dict[str, Any]:
    path = root / VULNERABILITY_POLICY_FILE
    payload = load_json(path)
    errors = validate_vulnerability_policy(payload, today=today)
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def build_osv_report(
    packages: list[dict[str, str]],
    response: Any,
    policy: Mapping[str, Any],
    *,
    scanned_at: str,
    today: dt.date | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors = validate_vulnerability_policy(policy, today=today)
    if errors:
        raise ValueError("; ".join(errors))
    if not isinstance(response, Mapping) or not isinstance(response.get("results"), list):
        raise ValueError("OSV response must contain a results list")
    results = response["results"]
    if len(results) != len(packages):
        raise ValueError(
            f"OSV response count mismatch: expected {len(packages)}, got {len(results)}"
        )
    exceptions = {
        (str(item["id"]), normalize_name(str(item["package"]))): item
        for item in policy.get("exceptions", [])
    }
    advisories: list[dict[str, Any]] = []
    unwaived: list[dict[str, Any]] = []
    for package, result in zip(packages, results, strict=True):
        if not isinstance(result, Mapping):
            raise ValueError("each OSV result must be an object")
        vulns = result.get("vulns", []) or []
        if not isinstance(vulns, list):
            raise ValueError("OSV vulns must be a list")
        for vuln in vulns:
            if not isinstance(vuln, Mapping) or not isinstance(vuln.get("id"), str):
                raise ValueError("OSV advisory is missing id")
            advisory_id = vuln["id"]
            waiver = exceptions.get((advisory_id, normalize_name(package["name"])))
            entry = {
                "id": advisory_id,
                "package": package["name"],
                "version": package["version"],
                "summary": vuln.get("summary"),
                "aliases": sorted(str(value) for value in vuln.get("aliases", []) or []),
                "waived": waiver is not None,
                "waiver": waiver,
            }
            advisories.append(entry)
            if waiver is None:
                unwaived.append(entry)
    advisories.sort(key=lambda item: (item["package"], item["version"], item["id"]))
    unwaived.sort(key=lambda item: (item["package"], item["version"], item["id"]))
    report = {
        "schema_version": 1,
        "status": "completed",
        "scan_completed": True,
        "scanned_at": scanned_at,
        "package_count": len(packages),
        "advisories": advisories,
        "unwaived_advisory_count": len(unwaived),
    }
    return report, unwaived


def generated_artifacts(root: Path, *, installed_licenses: bool = False) -> dict[Path, Any]:
    root = root.resolve()
    return {
        SBOM_FILE: build_sbom(root),
        LICENSE_REPORT_FILE: build_license_report(root, installed=installed_licenses),
        VULNERABILITY_REPORT_FILE: build_offline_vulnerability_report(root),
    }


def artifact_bytes(root: Path, *, installed_licenses: bool = False) -> dict[Path, bytes]:
    return {
        relative: canonical_json_bytes(value)
        for relative, value in generated_artifacts(
            root, installed_licenses=installed_licenses
        ).items()
    }


def validate_generated_artifacts(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for relative, expected in artifact_bytes(root).items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing generated artifact: {relative.as_posix()}")
            continue
        if path.read_bytes() != expected:
            errors.append(f"stale generated artifact: {relative.as_posix()}")
    return errors


def validate_supply_chain(root: Path, *, today: dt.date | None = None) -> list[str]:
    root = root.resolve()
    errors = validate_local_artifacts(root)
    errors.extend(validate_generated_artifacts(root))
    policy_path = root / VULNERABILITY_POLICY_FILE
    if not policy_path.is_file():
        errors.append(f"missing {VULNERABILITY_POLICY_FILE.as_posix()}")
    else:
        try:
            policy = load_json(policy_path)
        except Exception as error:
            errors.append(f"invalid vulnerability policy JSON: {error}")
        else:
            errors.extend(validate_vulnerability_policy(policy, today=today))
    for forbidden in (
        root / "script/bin/uv.exe",
        root / "script/bin/uvw.exe",
        root / "script/bin/uvx.exe",
    ):
        if forbidden.exists():
            errors.append(f"opaque bundled executable is forbidden: {forbidden.relative_to(root)}")
    return sorted(set(errors))
