from __future__ import annotations

from pathlib import Path

from tradingview_zy.market_metadata import market_default_codes, market_frequencies

ROOT = Path(__file__).resolve().parents[1]


def test_static_market_metadata_needs_no_provider_construction() -> None:
    frequencies = market_frequencies()
    defaults = market_default_codes()
    assert set(frequencies) == set(defaults) == {
        "a", "hk", "fx", "us", "futures", "ny_futures", "currency", "currency_spot"
    }
    assert defaults["a"] == "SH.000001"
    assert "d" in frequencies["us"]


def test_create_app_startup_metadata_does_not_call_get_exchange() -> None:
    source = (ROOT / "web/tradingview_zy_chart/cl_app/__init__.py").read_text(encoding="utf-8")
    create_app = source[source.index("def create_app"):source.index('@app.route("/login"')]
    assert "market_frequencys = market_frequencies()" in create_app
    assert "market_default_codes = market_default_codes()" in create_app
    metadata_block = create_app[
        create_app.index("# Web 元数据"):create_app.index("__log = fun.get_logger()")
    ]
    assert "get_exchange(" not in metadata_block


def test_metadata_module_has_no_sdk_or_exchange_imports() -> None:
    source = (ROOT / "src/tradingview_zy/market_metadata.py").read_text(encoding="utf-8")
    assert "get_exchange" not in source
    assert "tradingview_zy.exchange" not in source
    assert "tqsdk" not in source
    assert "ccxt" not in source
