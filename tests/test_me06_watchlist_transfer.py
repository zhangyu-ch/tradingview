from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from test_support.web_routes import route_source

from tradingview_zy.watchlist_transfer import (
    WatchlistTooLargeError,
    WatchlistTransferError,
    export_watchlist_text,
    parse_watchlist_stream,
)

ROOT = Path(__file__).resolve().parents[1]


def test_export_is_request_private_and_deterministic() -> None:
    stocks = [{"code": "SH.600519", "name": "贵州茅台"}]
    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda _: export_watchlist_text(stocks), range(20)))
    assert outputs == ["SH.600519,贵州茅台\n"] * 20
    assert not (ROOT / "data/zx.txt").exists()


def test_import_handles_bom_aliases_duplicates_and_unknown_codes() -> None:
    data = "\ufeffSHSE.600519,贵州茅台\n600519,duplicate\nBAD,Unknown\n".encode()
    entries = parse_watchlist_stream(
        io.BytesIO(data), market="a", available_codes=["SH.600519", "SZ.000001"]
    )
    assert [(entry.code, entry.name) for entry in entries] == [
        ("SH.600519", "贵州茅台")
    ]


def test_import_rejects_size_line_count_line_length_and_encoding() -> None:
    with pytest.raises(WatchlistTooLargeError):
        parse_watchlist_stream(io.BytesIO(b"A,1\nB,2\n"), market="us", available_codes=["A", "B"], max_lines=1)
    with pytest.raises(WatchlistTooLargeError):
        parse_watchlist_stream(io.BytesIO(b"A,123456\n"), market="us", available_codes=["A"], max_line_bytes=4)
    with pytest.raises(WatchlistTooLargeError):
        parse_watchlist_stream(io.BytesIO(b"A,1\n"), market="us", available_codes=["A"], max_bytes=3)
    with pytest.raises(WatchlistTransferError, match="UTF-8"):
        parse_watchlist_stream(io.BytesIO(b"\xff\xfe\n"), market="us", available_codes=[])


def test_web_route_uses_no_shared_file_or_unbounded_read() -> None:
    source = (ROOT / "web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    route = route_source("opt_zixuan_export") + route_source("opt_zixuan_import")
    assert "zx.txt" not in route
    assert ".save(" not in route
    assert ".readlines(" not in route
    assert "BytesIO(output)" in route
    assert "parse_watchlist_stream(" in route
    assert "MAX_CONTENT_LENGTH=max_upload_bytes" in source
