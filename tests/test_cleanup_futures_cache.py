import copy
import hashlib
import pickle
from pathlib import Path

import pandas as pd
import pytest

from tradingview_zy.backtesting import futures_contracts
from tradingview_zy.backtesting.backtest import BackTest
from tradingview_zy.backtesting.backtest_trader import BackTestTrader
from tradingview_zy.backtesting.process_output import build_process_output_path


class FakeBackTestKlines:
    def __init__(self, *args, **kwargs):
        pass


@pytest.fixture()
def backtests(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/bk").mkdir(parents=True)
    # Legacy tests reload this module; patch the globals used by this class.
    globals_ = BackTest.__init__.__globals__
    monkeypatch.setitem(globals_, "BackTestKlines", FakeBackTestKlines)
    monkeypatch.setitem(globals_, "BackTest", BackTest)
    runs = []

    def run(self, *args, **kwargs):
        runs.append((self.futures_parameter_version, self.save_file))
        return True

    monkeypatch.setattr(BackTest, "run", run)
    monkeypatch.setattr(
        BackTest, "positions", lambda self: pd.DataFrame({"profit_rate": [1.0]})
    )

    def create(version="2024-12-13-r2", market="futures"):
        code = "SHFE.AU" if market == "futures" else "SH.600000"
        config = {
            "mode": "trade",
            "market": market,
            "base_code": code,
            "codes": [code],
            "frequencys": ["d"],
            "start_datetime": "2025-01-01 00:00:00",
            "end_datetime": "2025-01-02 00:00:00",
            "init_balance": 100_000,
            "fee_rate": 0.0,
            "max_pos": 1,
            "strategy": None,
            "save_file": str(tmp_path / "result.pkl"),
        }
        if market == "futures":
            config["futures_parameter_version"] = version
        return BackTest(config)

    return create, runs


def old_optimization_path(bt):
    key = (
        f"{bt.base_code}_{bt.market}_{bt.codes}_{bt.frequencys}_"
        f"{bt.start_datetime}_{bt.end_datetime}_{type(bt.strategy)}_{bt.data_config}"
    )
    return Path(f"./data/bk/_optimization_{hashlib.md5(key.encode('UTF-8')).hexdigest()}.pkl")


def write_original_snapshot(bt, path):
    dataset = futures_contracts._load_dataset()
    manifest = copy.deepcopy(dataset["versions"][0])
    manifest.update(
        schema_version=1,
        dataset_id=dataset["dataset_id"],
        requested_products=["SHFE.AU"],
    )
    manifest["snapshot_sha256"] = futures_contracts._sha256(manifest)
    bt.futures_parameter_version = manifest["version"]
    bt.futures_parameter_manifest = manifest
    bt.trader = BackTestTrader(
        "old", mode="trade", market="futures", futures_parameter_manifest=manifest
    )
    bt.save_file = str(path)
    bt.save()
    return path.read_bytes()


def stored_snapshot(path):
    with Path(path).open("rb") as stream:
        return pickle.load(stream)["futures_parameter_manifest"]["snapshot_sha256"]


def test_optimization_isolates_versions_and_preserves_legacy_artifact(backtests):
    create, runs = backtests
    legacy = old_optimization_path(create())
    old_bytes = write_original_snapshot(create(), legacy)

    corrected = create().run_params({})
    fallback = create("legacy-static-r2").run_params({})
    repeated = create().run_params({})

    assert corrected["save_file"] != fallback["save_file"]
    assert Path(corrected["save_file"]) != legacy
    assert corrected == repeated
    assert [version for version, _ in runs] == ["2024-12-13-r2", "legacy-static-r2"]
    assert stored_snapshot(corrected["save_file"]) == create().futures_parameter_manifest["snapshot_sha256"]
    assert stored_snapshot(fallback["save_file"]) == create("legacy-static-r2").futures_parameter_manifest["snapshot_sha256"]
    assert legacy.read_bytes() == old_bytes


def test_process_worker_isolates_versions_and_preserves_legacy_artifact(backtests):
    create, runs = backtests
    legacy = build_process_output_path(create().save_file, "SHFE.AU")
    old_bytes = write_original_snapshot(create(), legacy)

    corrected = create().run_by_code("SHFE.AU")
    fallback = create("legacy-static-r2").run_by_code("SHFE.AU")
    repeated = create().run_by_code("SHFE.AU")

    assert corrected != fallback
    assert Path(corrected) != legacy
    assert repeated == corrected
    assert [version for version, _ in runs] == ["2024-12-13-r2", "legacy-static-r2"]
    assert stored_snapshot(corrected) == create().futures_parameter_manifest["snapshot_sha256"]
    assert stored_snapshot(fallback) == create("legacy-static-r2").futures_parameter_manifest["snapshot_sha256"]
    assert legacy.read_bytes() == old_bytes


def test_optimization_rejects_wrong_snapshot_at_expected_cache_path(backtests):
    create, runs = backtests
    result = create().run_params({})
    path = Path(result["save_file"])
    old_bytes = write_original_snapshot(create(), path)
    runs.clear()

    with pytest.raises(futures_contracts.FuturesParameterError, match="cached futures parameter snapshot mismatch"):
        create().run_params({})

    assert runs == []
    assert path.read_bytes() == old_bytes


@pytest.mark.parametrize("re_again", [False, True])
def test_process_worker_rejects_wrong_snapshot_without_overwrite(backtests, re_again):
    create, runs = backtests
    path = Path(create().run_by_code("SHFE.AU"))
    old_bytes = write_original_snapshot(create(), path)
    runs.clear()
    bt = create()
    bt._process_re_again = re_again

    with pytest.raises(futures_contracts.FuturesParameterError, match="cached futures parameter snapshot mismatch"):
        bt.run_by_code("SHFE.AU")

    assert runs == []
    assert path.read_bytes() == old_bytes


def test_non_futures_cache_names_and_reuse_are_unchanged(backtests):
    create, runs = backtests
    bt = create(market="a")
    optimization = bt.run_params({})
    assert Path(optimization["save_file"]) == old_optimization_path(bt)
    assert create(market="a").run_params({}) == optimization

    process = create(market="a").run_by_code("SH.600000")
    assert Path(process) == build_process_output_path(bt.save_file, "SH.600000")
    assert create(market="a").run_by_code("SH.600000") == process
    assert len(runs) == 2


def test_run_process_uses_version_isolated_worker_artifacts(backtests, monkeypatch):
    class InlineExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def map(self, fn, values):
            return [fn(value) for value in values]

    monkeypatch.setitem(
        BackTest.run_process.__globals__, "ProcessPoolExecutor", InlineExecutor
    )
    create, runs = backtests
    for version in ("2024-12-13-r2", "legacy-static-r2", "2024-12-13-r2"):
        bt = create(version)
        bt.mode = "signal"
        assert bt.run_process(max_workers=1) is True

    assert [version for version, _ in runs] == ["2024-12-13-r2", "legacy-static-r2"]
    assert runs[0][1] != runs[1][1]


def test_process_worker_can_explicitly_rerun_matching_snapshot(backtests):
    create, runs = backtests
    path = create().run_by_code("SHFE.AU")
    bt = create()
    bt._process_re_again = True
    assert bt.run_by_code("SHFE.AU") == path
    assert len(runs) == 2
