"""Bounded, concurrency-safe watchlist import/export helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import BinaryIO
from dataclasses import dataclass


class WatchlistTransferError(ValueError):
    status_code = 422


class WatchlistTooLargeError(WatchlistTransferError):
    status_code = 413


@dataclass(frozen=True)
class WatchlistEntry:
    code: str
    name: str | None


def export_watchlist_text(stocks: Iterable[Mapping[str, object]]) -> str:
    lines: list[str] = []
    for stock in stocks:
        code = str(stock.get("code", "")).strip()
        name = str(stock.get("name", "") or "").strip()
        if not code:
            continue
        lines.append(f"{code},{name}")
    return "\n".join(lines) + ("\n" if lines else "")


def parse_watchlist_stream(
    stream: BinaryIO,
    *,
    market: str,
    available_codes: Iterable[str],
    max_bytes: int = 1_048_576,
    max_lines: int = 5_000,
    max_line_bytes: int = 512,
) -> list[WatchlistEntry]:
    if max_bytes < 1 or max_lines < 1 or max_line_bytes < 1:
        raise ValueError("watchlist import limits must be positive")

    codes = tuple(str(code) for code in available_codes)
    code_set = set(codes)
    entries: list[WatchlistEntry] = []
    seen: set[str] = set()
    total_bytes = 0

    for line_number, raw_line in enumerate(stream, start=1):
        if line_number > max_lines:
            raise WatchlistTooLargeError(f"导入行数超过上限 {max_lines}")
        if not isinstance(raw_line, (bytes, bytearray)):
            raise WatchlistTransferError("上传流必须为二进制文本")
        total_bytes += len(raw_line)
        if total_bytes > max_bytes:
            raise WatchlistTooLargeError(f"上传文件超过 {max_bytes} 字节")
        if len(raw_line) > max_line_bytes:
            raise WatchlistTooLargeError(
                f"第 {line_number} 行超过 {max_line_bytes} 字节"
            )
        try:
            line = bytes(raw_line).decode("utf-8-sig" if line_number == 1 else "utf-8")
        except UnicodeDecodeError as exc:
            raise WatchlistTransferError(
                f"第 {line_number} 行不是有效 UTF-8 文本"
            ) from exc
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 1)
        code = parts[0].strip()
        name = parts[1].strip() if len(parts) == 2 else None
        if not code:
            raise WatchlistTransferError(f"第 {line_number} 行缺少代码")
        if market == "a":
            code = code.replace("SHSE.", "SH.").replace("SZSE.", "SZ.")
        if code not in code_set:
            matches = [candidate for candidate in codes if code in candidate]
            if len(matches) != 1:
                continue
            code = matches[0]
        if code in seen:
            continue
        seen.add(code)
        entries.append(WatchlistEntry(code=code, name=name or None))

    return entries
