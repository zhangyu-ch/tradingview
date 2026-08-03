from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class ProcessOutputConfigurationError(ValueError):
    """Raised before a process pool is created when output cannot be persisted."""


def validate_process_output_base(value: Any) -> Path:
    if value is None:
        raise ProcessOutputConfigurationError("save_file is required for process backtesting")
    if not isinstance(value, (str, Path)):
        raise ProcessOutputConfigurationError("save_file must be a file path")
    raw = str(value).strip()
    if raw == "":
        raise ProcessOutputConfigurationError("save_file must not be empty")
    path = Path(raw).expanduser()
    if path.exists() and path.is_dir():
        raise ProcessOutputConfigurationError("save_file must not be a directory")
    if path.name in {"", ".", ".."}:
        raise ProcessOutputConfigurationError("save_file must include a file name")
    return path


def prepare_process_output_base(value: Any) -> Path:
    path = validate_process_output_base(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _safe_code_name(code: Any) -> str:
    if not isinstance(code, str):
        raise ProcessOutputConfigurationError("process code must be text")
    normalized = re.sub(r"[^a-z0-9_-]+", "_", code.strip().lower()).strip("_")
    if normalized == "":
        raise ProcessOutputConfigurationError("process code cannot form a safe file name")
    return normalized


def build_process_output_path(base_value: Any, code: Any) -> Path:
    base = validate_process_output_base(base_value)
    safe_code = _safe_code_name(code)
    # Path.stem only touches the final component, so parent directories containing
    # '.pkl' remain intact. Process artifacts use a fixed pickle suffix.
    stem = base.stem if base.suffix else base.name
    return base.parent / f"{stem}_{safe_code}_process_.pkl"
