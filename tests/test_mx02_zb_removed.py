from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_zb_runtime_and_configuration_contract_are_removed() -> None:
    assert not (ROOT / "src/tradingview_zy/exchange/exchange_zb.py").exists()

    config_paths = [ROOT / "src/tradingview_zy/config.py.demo"]
    local_config = ROOT / "src/tradingview_zy/config.py"
    if local_config.exists():
        config_paths.append(local_config)

    for config_path in config_paths:
        text = config_path.read_text(encoding="utf-8").lower()
        assert " / zb" not in text
        assert "zb_apikey" not in text
        assert "zb_secret" not in text


def test_runtime_tree_has_no_zb_adapter_references() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            if "exchange_zb" in text or "ccxt.zb" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_removed_provider_is_documented() -> None:
    text = (ROOT / "docs/unsupported-providers.md").read_text(encoding="utf-8")
    assert "## ZB cryptocurrency provider (`MX-02`)" in text
    assert "Supported built-in cryptocurrency-futures providers are `binance` and `db`" in text
