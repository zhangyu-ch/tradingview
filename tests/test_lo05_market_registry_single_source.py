from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
from dataclasses import replace
from pathlib import Path

import pytest

from tradingview_zy.base import Market
from tradingview_zy.domain import UnsupportedProviderError
from tradingview_zy.market_metadata import (
    default_market_value,
    market_catalog,
    market_chart_defaults,
    market_default_codes,
    market_frequencies,
    market_ui_metadata,
    market_web_metadata,
    tradingview_symbol_metadata,
)
from tradingview_zy.market_registry import (
    MARKET_REGISTRY,
    configured_provider,
    validate_market_registry,
)
from tradingview_zy.sync_batch import SyncBatchError, load_sync_config

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "src/tradingview_zy/market_registry.py"
METADATA = ROOT / "src/tradingview_zy/market_metadata.py"
CONFIG_DEMO = ROOT / "src/tradingview_zy/config.py.demo"
EXCHANGE_FACTORY = ROOT / "src/tradingview_zy/exchange/__init__.py"
WEB_APP = ROOT / "web/tradingview_zy_chart/cl_app/__init__.py"
INDEX_TEMPLATE = ROOT / "web/tradingview_zy_chart/cl_app/templates/index.html"
GENERIC_SYNC = ROOT / "script/crontab/reboot_sync_market_klines.py"
SYNC_CONFIG_ROOT = ROOT / "script/crontab/sync_configs"


def test_registry_is_exhaustive_and_contains_every_full_stack_descriptor() -> None:
    validate_market_registry()
    assert set(MARKET_REGISTRY) == set(Market)
    defaults = [spec.market for spec in MARKET_REGISTRY.values() if spec.is_default]
    assert defaults == [Market.A]

    for market, spec in MARKET_REGISTRY.items():
        assert spec.market is market
        assert spec.default_provider in spec.providers
        assert spec.ui_label and spec.tradingview_name and spec.description
        assert spec.default_code and spec.frequencies
        assert spec.tradingview_type and spec.tradingview_timezone
        assert spec.default_session_profile in spec.tradingview_sessions
        assert spec.payload_timezone
        assert spec.db_partition(spec.default_code)


def test_all_web_and_udf_views_are_exact_registry_projections() -> None:
    catalog = market_catalog()
    values = [spec.market.value for spec in MARKET_REGISTRY.values()]
    assert [item["value"] for item in catalog] == values
    assert default_market_value() == Market.A.value
    assert market_default_codes() == {
        spec.market.value: spec.default_code for spec in MARKET_REGISTRY.values()
    }
    assert market_frequencies() == {
        spec.market.value: list(spec.frequencies) for spec in MARKET_REGISTRY.values()
    }
    assert market_web_metadata() == {
        spec.market.value: {
            "default_code": spec.default_code,
            "frequencies": list(spec.frequencies),
        }
        for spec in MARKET_REGISTRY.values()
    }

    defaults = market_chart_defaults()
    assert defaults["market"] == Market.A.value
    for spec in MARKET_REGISTRY.values():
        key = spec.market.value
        assert defaults[f"{key}_code"] == spec.default_code
        assert market_ui_metadata(key) == {
            "has_seconds": spec.has_seconds,
            "search_name": spec.search_by_name,
            "plate_panel": spec.plate_panel,
        }
        metadata = tradingview_symbol_metadata(key, spec.default_code)
        assert metadata["type"] == spec.tradingview_type
        assert metadata["timezone"] == spec.tradingview_timezone


def test_one_descriptor_can_drive_every_consumer_without_a_second_map() -> None:
    class FakeMarket(str):
        pass

    paper = FakeMarket("paper")
    base = MARKET_REGISTRY[Market.A]
    paper_spec = replace(
        base,
        market=paper,
        config_attribute="EXCHANGE_PAPER",
        default_provider="db",
        ui_label="Paper",
        tradingview_name="Paper",
        description="Paper market",
        default_code="PAPER.TEST",
        frequencies=types.MappingProxyType({"d": "D", "1m": "1m"}),
        tradingview_sessions=types.MappingProxyType({"regular": "24x7"}),
        default_session_profile="regular",
        is_default=True,
        plate_panel=False,
    )
    registry = {paper: paper_spec}

    validate_market_registry(registry, expected_markets=frozenset({paper}))
    assert default_market_value(registry) == "paper"
    assert market_default_codes(registry) == {"paper": "PAPER.TEST"}
    assert market_frequencies(registry) == {"paper": ["d", "1m"]}
    assert market_catalog(registry)[0]["name"] == "Paper"
    assert tradingview_symbol_metadata("paper", registry=registry) == {
        "type": "stock",
        "session": "24x7",
        "timezone": "Asia/Shanghai",
    }


def test_registry_validation_rejects_missing_or_ambiguous_descriptors() -> None:
    missing = dict(MARKET_REGISTRY)
    missing.pop(Market.HK)
    with pytest.raises(RuntimeError, match="不完整"):
        validate_market_registry(missing)

    no_default = dict(MARKET_REGISTRY)
    no_default[Market.A] = replace(no_default[Market.A], is_default=False)
    with pytest.raises(RuntimeError, match="一个默认市场"):
        validate_market_registry(no_default)

    two_defaults = dict(MARKET_REGISTRY)
    two_defaults[Market.HK] = replace(two_defaults[Market.HK], is_default=True)
    with pytest.raises(RuntimeError, match="一个默认市场"):
        validate_market_registry(two_defaults)

    bad_provider = dict(MARKET_REGISTRY)
    bad_provider[Market.A] = replace(
        bad_provider[Market.A], default_provider="not-registered"
    )
    with pytest.raises(RuntimeError, match="默认数据源"):
        validate_market_registry(bad_provider)


def test_provider_selection_defaults_and_overrides_are_registry_driven() -> None:
    assert configured_provider(Market.A, types.SimpleNamespace()) == "tdx"
    assert (
        configured_provider(Market.US, types.SimpleNamespace(MARKET_PROVIDERS={}))
        == "tdx_us"
    )
    assert (
        configured_provider(
            Market.US,
            types.SimpleNamespace(
                MARKET_PROVIDERS={"us": "polygon"}, EXCHANGE_US="tdx_us"
            ),
        )
        == "polygon"
    )
    assert (
        configured_provider(Market.US, types.SimpleNamespace(EXCHANGE_US="polygon"))
        == "polygon"
    )
    with pytest.raises(UnsupportedProviderError):
        configured_provider(Market.A, types.SimpleNamespace(MARKET_PROVIDERS=[]))
    with pytest.raises(UnsupportedProviderError):
        configured_provider(
            Market.A, types.SimpleNamespace(MARKET_PROVIDERS={"a": "unknown"})
        )


def test_old_duplicate_maps_and_executable_provider_assignments_are_removed() -> None:
    metadata_source = METADATA.read_text(encoding="utf-8")
    for token in (
        "_MARKET_WEB_METADATA",
        "_TRADINGVIEW_STATIC_METADATA",
        "_CN_FUTURES_SESSIONS",
    ):
        assert token not in metadata_source

    config_tree = ast.parse(CONFIG_DEMO.read_text(encoding="utf-8"))
    assigned = {
        target.id
        for node in config_tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else [node.target]
        )
        if isinstance(target, ast.Name)
    }
    assert "MARKET_PROVIDERS" in assigned
    assert not {
        "EXCHANGE_A",
        "EXCHANGE_HK",
        "EXCHANGE_FX",
        "EXCHANGE_US",
        "EXCHANGE_FUTURES",
        "EXCHANGE_NY_FUTURES",
        "EXCHANGE_CURRENCY",
        "EXCHANGE_CURRENCY_SPOT",
    } & assigned

    factory = EXCHANGE_FACTORY.read_text(encoding="utf-8")
    assert 'Market.A: "EXCHANGE_A"' not in factory
    assert "selected_provider(market, config)" in factory
    assert "getattr(config, \"EXCHANGE_" not in factory


def test_web_routes_and_template_consume_only_registry_projections() -> None:
    app = WEB_APP.read_text(encoding="utf-8")
    udf = (
        ROOT / "web/tradingview_zy_chart/cl_app/blueprints/udf.py"
    ).read_text(encoding="utf-8")
    web_runtime = app + udf
    assert "market_catalog_items = market_catalog()" in app
    assert "default_market_key = default_market_value()" in app
    assert "market_ui_metadata(market)" in udf
    assert "market_ui_metadata(exchange)" in udf
    assert '"value": "a"' not in web_runtime
    assert 'market in ["futures", "ny_futures"]' not in web_runtime
    assert 'market in ["currency", "currency_spot"]' not in web_runtime

    template = INDEX_TEMPLATE.read_text(encoding="utf-8")
    assert "{% for item in market_catalog %}" in template
    assert "{{ market_default_codes | tojson }}" in template
    assert "{{ default_market | tojson }}" in template
    for market in Market:
        assert f'market_default_codes.{market.value}' not in template
        assert f'<option value="{market.value}"' not in template


def test_all_sync_configs_are_validated_by_the_registry(tmp_path: Path) -> None:
    paths = sorted(SYNC_CONFIG_ROOT.glob("*_klines.json"))
    assert paths
    for path in paths:
        config = load_sync_config(path)
        spec = MARKET_REGISTRY[Market(config["market"])]
        assert set(config["frequencies"]) <= (
            set(spec.frequencies) | set(spec.additional_sync_frequencies)
        )

    template = json.loads(paths[0].read_text(encoding="utf-8"))
    template["market"] = "not-a-market"
    invalid_market = tmp_path / "invalid-market.json"
    invalid_market.write_text(json.dumps(template), encoding="utf-8")
    with pytest.raises(SyncBatchError, match="market is not registered"):
        load_sync_config(invalid_market)

    template["market"] = Market.A.value
    template["frequencies"] = {"99x": {}}
    invalid_frequency = tmp_path / "invalid-frequency.json"
    invalid_frequency.write_text(json.dumps(template), encoding="utf-8")
    with pytest.raises(SyncBatchError, match="unsupported frequencies"):
        load_sync_config(invalid_frequency)


def test_generic_sync_entrypoint_is_import_safe_and_requires_an_explicit_config() -> None:
    source = GENERIC_SYNC.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(GENERIC_SYNC))
    assert "configured_sync_cli(None, argv)" in source
    assert "tradingview_zy.exchange." not in source
    assert not any(
        isinstance(node, (ast.For, ast.While, ast.With, ast.Try)) for node in tree.body
    )

    spec = importlib.util.spec_from_file_location("lo05_generic_sync", GENERIC_SYNC)
    assert spec and spec.loader
    before = {name for name in sys.modules if name.startswith("tradingview_zy.exchange.exchange_")}
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    after = {name for name in sys.modules if name.startswith("tradingview_zy.exchange.exchange_")}
    assert after == before
    with pytest.raises(SystemExit) as exc_info:
        module.main([])
    assert exc_info.value.code == 2
