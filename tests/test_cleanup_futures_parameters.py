import copy
import logging

import pytest

from tradingview_zy.backtesting import futures_contracts as parameters


CORRECTED_VERSION = "2024-12-13-r2"
LEGACY_VERSION = "legacy-static-r2"
CORRECTED_SIZES = {"CZCE.TA": 5, "DCE.I": 100, "DCE.Y": 10, "SHFE.AU": 1000}


def manifest(version, start="2025-01-01"):
    return parameters.build_futures_parameter_manifest(
        version=version,
        start_datetime=start,
        end_datetime="2025-01-02",
        codes=list(CORRECTED_SIZES),
    )


@pytest.mark.parametrize("version", [CORRECTED_VERSION, LEGACY_VERSION])
def test_corrected_multipliers_apply_to_both_selectable_versions(version):
    result = manifest(version)
    assert parameters.validate_futures_parameter_manifest(result) == result
    for product, size in CORRECTED_SIZES.items():
        assert result["contracts"][product]["symbol_size"] == size
    assert result["contracts"]["DCE.M"]["fee_rate_open"] == 1.51


def test_legacy_version_is_explicit_and_warns_about_approximate_history(caplog):
    caplog.set_level(logging.WARNING)
    result = manifest(LEGACY_VERSION, start="2010-01-01")
    assert result["provenance"]["usage"] == "static-approximation"
    assert result["effective_from"] == "1900-01-01"
    assert "static approximation" in caplog.text
    assert LEGACY_VERSION in caplog.text
    with pytest.raises(parameters.FuturesParameterError, match="does not cover"):
        manifest(CORRECTED_VERSION, start="2010-01-01")
    with pytest.raises(parameters.FuturesParameterError, match="required"):
        manifest(None, start="2010-01-01")


def test_erroneous_version_is_load_only_without_invalidating_old_snapshots():
    with pytest.raises(parameters.FuturesParameterError, match="2024-12-13-r2"):
        manifest("2024-12-13")
    assert "2024-12-13" not in parameters.available_futures_parameter_versions()

    dataset = parameters._load_dataset()
    original = dataset["versions"][0]
    assert original["dataset_sha256"] == (
        "80b0e29337f9b74e92bd71ed0175330d4c2a78e348904e4ac109aa3e4752a77f"
    )
    old = copy.deepcopy(original)
    old.update(schema_version=1, dataset_id=dataset["dataset_id"], requested_products=["SHFE.AU"])
    old["snapshot_sha256"] = parameters._sha256(old)
    assert old["snapshot_sha256"] == (
        "3d56b05b6af5c104deaac0ba931f99c85bd485e5f2489dc56b00b302e8ceda37"
    )
    assert parameters.validate_futures_parameter_manifest(old) == old


def test_fallback_uses_corrected_snapshot_without_claiming_historical_accuracy():
    corrected = manifest(CORRECTED_VERSION)
    fallback = manifest(LEGACY_VERSION, start="2010-01-01")
    assert fallback["contracts"] == corrected["contracts"]
    assert fallback["dataset_sha256"] != corrected["dataset_sha256"]
    assert fallback["provenance"]["independent_verification"] is False
    with pytest.raises(parameters.FuturesParameterError, match="does not cover"):
        manifest(LEGACY_VERSION, start="1899-12-31")
