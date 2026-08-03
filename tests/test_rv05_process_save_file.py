from __future__ import annotations

from pathlib import Path

import pytest

from tradingview_zy.backtesting.process_output import (
    ProcessOutputConfigurationError,
    build_process_output_path,
    prepare_process_output_base,
    validate_process_output_base,
)


@pytest.mark.parametrize("value", [None, "", "   ", 123])
def test_validate_process_output_base_rejects_missing_or_non_path(value):
    with pytest.raises(ProcessOutputConfigurationError):
        validate_process_output_base(value)


def test_validate_process_output_base_rejects_existing_directory(tmp_path):
    with pytest.raises(ProcessOutputConfigurationError):
        validate_process_output_base(tmp_path)


def test_prepare_process_output_base_creates_parent(tmp_path):
    target = tmp_path / "nested" / "result.pkl"
    assert prepare_process_output_base(target) == target
    assert target.parent.is_dir()


def test_build_process_output_path_preserves_parent_named_with_pkl(tmp_path):
    base = tmp_path / "archive.pkl.folder" / "portfolio.pkl"
    output = build_process_output_path(base, "BTC/USDT:PERP")
    assert output.parent == base.parent
    assert output.name == "portfolio_btc_usdt_perp_process_.pkl"


def test_build_process_output_path_handles_multiple_suffixes():
    output = build_process_output_path("result.tar.pkl", "US.AAPL")
    assert output == Path("result.tar_us_aapl_process_.pkl")


@pytest.mark.parametrize("code", ["", "...", 3])
def test_build_process_output_path_rejects_unsafe_empty_code(code):
    with pytest.raises(ProcessOutputConfigurationError):
        build_process_output_path("result.pkl", code)


def test_backtest_source_validates_before_process_pool_and_uses_path_builder():
    source = open("src/tradingview_zy/backtesting/backtest.py", encoding="utf-8").read()
    run_by_code = source[source.index("    def run_by_code"):source.index("    def run_process")]
    run_process = source[source.index("    def run_process"):source.index("    def result")]
    assert "build_process_output_path" in run_by_code
    assert ".split(\".pkl\")" not in run_by_code
    assert run_process.index("prepare_process_output_base") < run_process.index("ProcessPoolExecutor")
