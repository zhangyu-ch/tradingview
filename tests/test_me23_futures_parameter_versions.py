from __future__ import annotations

import importlib
import json
import pickle
import sys
import types
from pathlib import Path

import pytest

from tradingview_zy.backtesting import futures_contracts
from tradingview_zy.backtesting.backtest_trader import BackTestTrader


class FakeBackTestKlines:
    created = 0

    def __init__(self, *args, **kwargs):
        type(self).created += 1
        self.args = args
        self.kwargs = kwargs


@pytest.fixture()
def backtest_module(monkeypatch):
    for name in ("empyrical", "pyfolio", "prettytable"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))

    pyecharts = types.ModuleType("pyecharts")
    options = types.ModuleType("pyecharts.options")
    charts = types.ModuleType("pyecharts.charts")
    for cls_name in ("Bar", "Grid", "Line"):
        setattr(charts, cls_name, type(cls_name, (), {}))
    pyecharts.options = options
    monkeypatch.setitem(sys.modules, "pyecharts", pyecharts)
    monkeypatch.setitem(sys.modules, "pyecharts.options", options)
    monkeypatch.setitem(sys.modules, "pyecharts.charts", charts)

    klines_mod = types.ModuleType("tradingview_zy.backtesting.backtest_klines")
    klines_mod.BackTestKlines = FakeBackTestKlines
    monkeypatch.setitem(
        sys.modules, "tradingview_zy.backtesting.backtest_klines", klines_mod
    )

    exchange_mod = types.ModuleType("tradingview_zy.exchange.exchange")
    for name in (
        "convert_currency_kline_frequency",
        "convert_futures_kline_frequency",
        "convert_stock_kline_frequency",
    ):
        setattr(exchange_mod, name, lambda value: value)
    monkeypatch.setitem(sys.modules, "tradingview_zy.exchange.exchange", exchange_mod)

    sys.modules.pop("tradingview_zy.backtesting.backtest", None)
    return importlib.import_module("tradingview_zy.backtesting.backtest")


def _manifest(*, codes=("DCE.m2501",), start="2025-01-01 09:00:00"):
    return futures_contracts.build_futures_parameter_manifest(
        version="2024-12-13",
        start_datetime=start,
        end_datetime="2025-01-31 15:00:00",
        codes=codes,
    )


def _config(tmp_path: Path, **overrides):
    config = {
        "mode": "trade",
        "market": "futures",
        "base_code": "DCE.m2501",
        "codes": ["DCE.m2501"],
        "frequencys": ["5m"],
        "start_datetime": "2025-01-01 09:00:00",
        "end_datetime": "2025-01-31 15:00:00",
        "init_balance": 100_000,
        "fee_rate": 0.0,
        "max_pos": 5,
        "strategy": None,
        "save_file": str(tmp_path / "result.pkl"),
        "futures_parameter_version": "2024-12-13",
    }
    config.update(overrides)
    return config


def test_bundled_dataset_preserves_all_legacy_contract_values():
    data_path = (
        Path(futures_contracts.__file__).with_name("futures_parameters.json")
    )
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    version = raw["versions"][0]
    assert raw["schema_version"] == 1
    assert version["version"] == "2024-12-13"
    assert version["effective_from"] == "2024-12-13"
    assert version["source_date"] == "2024-12-13"
    assert len(version["contracts"]) == 20
    assert version["contracts"]["DCE.M"]["fee_rate_open"] == 1.51
    assert version["contracts"]["SHFE.RU"]["fee_rate_close_today"] == 18.01
    assert version["provenance"]["independent_verification"] is False


def test_normalize_futures_code_supports_product_contract_and_tq_symbols():
    assert futures_contracts.normalize_futures_code("DCE.M") == "DCE.M"
    assert futures_contracts.normalize_futures_code("dce.m2501") == "DCE.M"
    assert futures_contracts.normalize_futures_code("KQ.m@SHFE.rb") == "SHFE.RB"
    with pytest.raises(futures_contracts.FuturesParameterError):
        futures_contracts.normalize_futures_code("rb2501")


def test_manifest_round_trip_and_trader_use_injected_snapshot():
    manifest = _manifest()
    checked = futures_contracts.validate_futures_parameter_manifest(manifest)
    assert checked["snapshot_sha256"] == manifest["snapshot_sha256"]
    assert checked["requested_products"] == ["DCE.M"]

    trader = BackTestTrader(
        "test",
        mode="trade",
        market="futures",
        init_balance=100_000,
        futures_parameter_manifest=manifest,
    )
    assert trader.futures_parameter_version == "2024-12-13"
    assert trader.futures_contracts["DCE.M"]["symbol_size"] == 10
    assert trader.cal_fee("DCE.m2501", 3000.0, 6000.0, 2.0) == pytest.approx(3.02)

    # Mutating the caller's manifest cannot change the trader snapshot.
    manifest["contracts"]["DCE.M"]["fee_rate_open"] = 999
    assert trader.futures_contracts["DCE.M"]["fee_rate_open"] == 1.51


def test_unknown_version_is_rejected():
    with pytest.raises(futures_contracts.FuturesParameterError, match="unknown"):
        futures_contracts.build_futures_parameter_manifest(
            version="does-not-exist",
            start_datetime="2025-01-01",
            end_datetime="2025-01-02",
            codes=["DCE.M"],
        )


def test_date_outside_effective_range_is_rejected():
    with pytest.raises(futures_contracts.FuturesParameterError, match="does not cover"):
        futures_contracts.build_futures_parameter_manifest(
            version="2024-12-13",
            start_datetime="2024-12-12",
            end_datetime="2024-12-13",
            codes=["DCE.M"],
        )


def test_missing_contract_is_rejected():
    with pytest.raises(futures_contracts.FuturesParameterError, match="does not define"):
        futures_contracts.build_futures_parameter_manifest(
            version="2024-12-13",
            start_datetime="2025-01-01",
            end_datetime="2025-01-02",
            codes=["CFFEX.IF2501"],
        )


def test_backtest_validates_before_data_load_and_detects_tampering(
    tmp_path, backtest_module
):
    BackTest = backtest_module.BackTest
    FakeBackTestKlines.created = 0
    missing = _config(tmp_path)
    missing.pop("futures_parameter_version")
    with pytest.raises(
        futures_contracts.FuturesParameterError,
        match="futures_parameter_version is required",
    ):
        BackTest(missing)
    assert FakeBackTestKlines.created == 0

    bt = BackTest(_config(tmp_path))
    assert FakeBackTestKlines.created == 1
    assert bt.trader.futures_parameter_manifest["version"] == "2024-12-13"
    bt.save()

    restored = BackTest()
    restored.load(bt.save_file)
    assert restored.futures_parameter_manifest["snapshot_sha256"] == (
        bt.futures_parameter_manifest["snapshot_sha256"]
    )

    with open(bt.save_file, "rb") as fh:
        stored = pickle.load(fh)
    stored["futures_parameter_manifest"]["contracts"]["DCE.M"][
        "symbol_size"
    ] = 999
    tampered = tmp_path / "tampered.pkl"
    with tampered.open("wb") as fh:
        pickle.dump(stored, fh)
    with pytest.raises(futures_contracts.FuturesParameterError, match="hash mismatch"):
        BackTest().load(str(tampered))
