from __future__ import annotations

import datetime as dt
import importlib
import os
import pickle
import stat
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# The production repository intentionally does not ship the private config.py.
# Install the smallest contract needed to load the cache module in isolation.
_CONFIG_ROOT = ROOT / ".test-file-cache-import"
config_module = sys.modules.get("tradingview_zy.config")
if config_module is None:
    config_module = types.ModuleType("tradingview_zy.config")
    config_module.get_data_path = lambda: _CONFIG_ROOT
    sys.modules["tradingview_zy.config"] = config_module

if "tzlocal" not in sys.modules:
    tzlocal_module = types.ModuleType("tzlocal")
    tzlocal_module.get_localzone = lambda: dt.timezone.utc
    sys.modules["tzlocal"] = tzlocal_module

cache_module = importlib.import_module("tradingview_zy.file_db")
from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.base import POSITION


@pytest.fixture()
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cache_module, "get_data_path", lambda: tmp_path)
    instance = cache_module.FileCacheDB()
    monkeypatch.setattr(cache_module, "fdb", instance)
    return instance


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-08-03 09:30:00", "2026-08-03 09:31:00"]
            ),
            "open": [10.0, 10.1],
            "high": [10.2, 10.3],
            "low": [9.9, 10.0],
            "close": [10.1, 10.2],
            "volume": [100.0, 200.0],
        }
    )


def test_atomic_write_failure_preserves_old_file_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    target.write_text("old", encoding="utf-8")
    real_replace = cache_module.os.replace

    def fail_replace(source, destination):
        if Path(destination) == target:
            raise OSError("simulated crash before replace")
        return real_replace(source, destination)

    monkeypatch.setattr(cache_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated crash"):
        cache_module._atomic_write_bytes(target, b"new")

    assert target.read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob(".state.json.*.tmp"))


def test_kline_metadata_makes_incomplete_bar_explicit(cache) -> None:
    frame = _frame()
    assert cache.save_tdx_klines(
        "a", "SH.600000", "1m", frame, last_row_complete=False
    )

    completed = cache.get_tdx_klines("a", "SH.600000", "1m")
    all_rows = cache.get_tdx_klines(
        "a", "SH.600000", "1m", include_incomplete=True
    )
    assert completed["close"].tolist() == [10.1]
    assert all_rows["close"].tolist() == [10.1, 10.2]

    cache.save_tdx_klines(
        "a", "SH.600000", "1m", frame, last_row_complete=True
    )
    assert len(cache.get_tdx_klines("a", "SH.600000", "1m")) == 2


def test_corrupt_csv_is_quarantined_instead_of_deleted(cache) -> None:
    path = cache._kline_path("a", "SH.600000", "1m")
    path.write_text("not_a_date,close\nbad,1\n", encoding="utf-8")

    with pytest.raises(cache_module.SafeCacheCorruptionError, match="date"):
        cache.get_tdx_klines("a", "SH.600000", "1m")

    assert not path.exists()
    quarantined = list(path.parent.glob(f"{path.name}.corrupt.*"))
    assert len(quarantined) == 1
    assert "not_a_date" in quarantined[0].read_text(encoding="utf-8")


def test_temporary_permission_error_preserves_kline_file(
    cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = _frame()
    cache.save_tdx_klines("a", "SH.600000", "1m", frame)
    path = cache._kline_path("a", "SH.600000", "1m")
    original = path.read_bytes()
    real_read_bytes = Path.read_bytes

    def denied(candidate: Path):
        if candidate == path:
            raise PermissionError("temporary lock")
        return real_read_bytes(candidate)

    monkeypatch.setattr(Path, "read_bytes", denied)
    assert cache.get_tdx_klines("a", "SH.600000", "1m") is None
    assert path.exists()
    assert path.stat().st_size == len(original)
    assert not list(path.parent.glob(f"{path.name}.corrupt.*"))


def test_safe_state_round_trip_and_real_trader_compatibility(cache) -> None:
    position = POSITION(
        "SH.600000",
        "1buy",
        balance=1000.0,
        price=10.0,
        amount=100.0,
        open_datetime=dt.datetime(2026, 8, 3, 9, 30),
    )
    position.close_uid_profit = {
        "clear": {
            "close_datetime": dt.datetime(
                2026, 8, 3, 15, 0, tzinfo=dt.timezone.utc
            ),
            "profit": 12.5,
        }
    }
    payload = {
        "position": position,
        "aware": dt.datetime(2026, 8, 3, tzinfo=dt.timezone.utc),
        "naive": dt.datetime(2026, 8, 3, 9, 30),
        "series": pd.Series([1.0, 2.0], index=["a", "b"], name="values"),
        "frame": pd.DataFrame({"x": [1, 2], "y": ["a", "b"]}),
        "tuple": (1, "x"),
        "set": {"a", "b"},
    }
    assert cache.cache_pkl_to_file("roundtrip", payload)
    restored = cache.cache_pkl_from_file("roundtrip")
    assert isinstance(restored["position"], POSITION)
    assert restored["position"].close_uid_profit["clear"]["profit"] == 12.5
    assert restored["aware"].tzinfo is not None
    assert restored["naive"].tzinfo is None
    pd.testing.assert_series_equal(restored["series"], payload["series"])
    pd.testing.assert_frame_equal(restored["frame"], payload["frame"])
    assert restored["tuple"] == (1, "x")
    assert restored["set"] == {"a", "b"}

    trader = BackTestTrader("source", mode="trade", market="a", init_balance=12345)
    trader.positions["SH.600000"] = [position]
    trader.save_to_pkl("trader-state")
    target = BackTestTrader("target", mode="trade", market="a", init_balance=1)
    assert target.load_from_pkl("trader-state") is True
    assert target.name == "source"
    assert target.balance == 12345
    assert target.positions["SH.600000"][0].amount == 100.0

    state_file = cache.cache_pkl_path / "trader-state.json"
    if os.name == "posix":
        assert stat.S_IMODE(state_file.stat().st_mode) == 0o600


def test_legacy_pickle_is_detected_but_never_executed(cache, tmp_path: Path) -> None:
    marker = tmp_path / "executed.txt"

    class Payload:
        def __reduce__(self):
            return (os.system, (f"printf executed > {marker}",))

    legacy = cache.cache_pkl_path / "legacy.pkl"
    legacy.write_bytes(pickle.dumps(Payload()))

    with pytest.raises(cache_module.UnsafeLegacyCacheError, match="not loaded"):
        cache.cache_pkl_from_file("legacy")

    assert not marker.exists()
    assert legacy.exists()


def test_corrupt_safe_json_is_quarantined(cache) -> None:
    path = cache.cache_pkl_path / "broken.json"
    path.write_text('{"schema":"wrong"}', encoding="utf-8")

    with pytest.raises(cache_module.SafeCacheCorruptionError, match="envelope"):
        cache.cache_pkl_from_file("broken")

    assert not path.exists()
    assert len(list(cache.cache_pkl_path.glob("broken.json.corrupt.*"))) == 1


def test_cache_filename_rejects_path_traversal(cache) -> None:
    for name in ("../secret", "nested/file", r"nested\\file", ".", ".."):
        with pytest.raises(ValueError, match="basename"):
            cache.cache_pkl_to_file(name, {"ok": True})


def test_tdx_xdxr_cache_uses_atomic_csv_not_pickle(tmp_path: Path) -> None:
    source = (ROOT / "src/tradingview_zy/exchange/exchange_tdx.py").read_text(
        encoding="utf-8"
    )
    start = source.index("    def xdxr(")
    end = source.index("    def klines_fq(", start)
    method = source[start:end]
    assert ".csv" in method
    assert "atomic_write_dataframe_csv" in method
    assert "read_dataframe_csv" in method
    assert "to_pickle" not in method
    assert "read_pickle" not in method

    path = tmp_path / "xdxr.csv"
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2026-08-03"]), "category": [1], "fenhong": [0.1]}
    )
    cache_module.FileCacheDB.atomic_write_dataframe_csv(path, frame)
    restored = cache_module.FileCacheDB.read_dataframe_csv(
        path, parse_dates=["date"]
    )
    pd.testing.assert_frame_equal(restored, frame)

    empty_path = tmp_path / "empty-xdxr.csv"
    empty_frame = pd.DataFrame(columns=["date"])
    cache_module.FileCacheDB.atomic_write_dataframe_csv(empty_path, empty_frame)
    restored_empty = cache_module.FileCacheDB.read_dataframe_csv(
        empty_path, parse_dates=["date"]
    )
    assert list(restored_empty.columns) == ["date"]
    assert restored_empty.empty
    assert "xdxr_file.stat().st_size == 0" in method
    assert 'data = pd.DataFrame(columns=["date"])' in method
