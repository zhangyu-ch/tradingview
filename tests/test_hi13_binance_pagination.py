from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "src/tradingview_zy/exchange/binance_pagination.py"
spec = importlib.util.spec_from_file_location("binance_pagination", HELPER)
assert spec and spec.loader
pagination = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pagination)


def _row(timestamp: int) -> list[float]:
    return [timestamp, 1.0, 2.0, 0.5, 1.5, 10.0]


def test_cache_resume_is_safe_for_zero_one_and_many_rows() -> None:
    empty = pd.DataFrame(columns=["date"])
    one = pd.DataFrame([{"date": pd.Timestamp("2026-01-01 00:00:00")}])
    many = pd.DataFrame(
        [
            {"date": pd.Timestamp("2026-01-01 00:00:00")},
            {"date": pd.Timestamp("2026-01-01 00:01:00")},
        ]
    )
    assert pagination.latest_cached_datetime(empty) is None
    assert pagination.latest_cached_datetime(one) == "2026-01-01 00:00:00"
    assert pagination.latest_cached_datetime(many) == "2026-01-01 00:01:00"


def test_forward_cursor_skips_inclusive_boundary_and_deduplicates() -> None:
    calls: list[dict[str, int]] = []
    pages = [
        [_row(1000), _row(2000)],
        [_row(2000), _row(3000)],
        [_row(3000)],
    ]

    def fetch(params):
        calls.append(dict(params))
        return pages[len(calls) - 1]

    result = pagination.paginate_ohlcv(
        fetch, start_ms=1000, page_limit=2, max_pages=5
    )
    assert [row[0] for row in result] == [1000, 2000, 3000]
    assert calls == [
        {"startTime": 1000},
        {"startTime": 2001},
        {"startTime": 3001},
    ]


def test_repeated_full_page_is_detected_as_stalled() -> None:
    page = [_row(1000), _row(2000)]
    with pytest.raises(pagination.PaginationStalledError, match="did not advance"):
        pagination.paginate_ohlcv(
            lambda _params: page,
            start_ms=1000,
            page_limit=2,
            max_pages=5,
        )


def test_backward_cursor_excludes_previous_first_row() -> None:
    calls: list[dict[str, int]] = []
    pages = [[_row(2000), _row(3000)], [_row(1000)]]

    def fetch(params):
        calls.append(dict(params))
        return pages[len(calls) - 1]

    result = pagination.paginate_ohlcv(
        fetch, start_ms=None, page_limit=2, target_count=10, max_pages=5
    )
    assert [row[0] for row in result] == [1000, 2000, 3000]
    assert calls == [{}, {"endTime": 1999}]


def test_both_adapters_use_shared_pagination_without_minus_two_index() -> None:
    for name in ["exchange_binance.py", "exchange_binance_spot.py"]:
        text = (ROOT / "src/tradingview_zy/exchange" / name).read_text(encoding="utf-8")
        assert "iloc[-2]" not in text
        assert "latest_cached_datetime(db_klines)" in text
        assert "paginate_ohlcv(" in text
