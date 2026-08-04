from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from tradingview_zy.secret_store import SecretReferenceError, resolve_config_secret

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src/tradingview_zy/config.py.demo"
WORKER = ROOT / "script/crontab/script_ib_tasks.py"


def test_repository_templates_and_runtime_sources_contain_no_concrete_ib_account() -> None:
    concrete_account = re.compile(r"\bDU\d{5,}\b")
    files = [
        CONFIG,
        WORKER,
        ROOT / "src/tradingview_zy/exchange/exchange_ib.py",
    ]
    for path in files:
        assert concrete_account.search(path.read_text(encoding="utf-8")) is None, path
    assert "IB_ACCOUNT = 'env://TRADINGVIEW_ZY_IB_ACCOUNT'" in CONFIG.read_text(
        encoding="utf-8"
    )


def test_ib_worker_resolves_account_before_connecting() -> None:
    source = WORKER.read_text(encoding="utf-8")
    resolver = 'resolve_config_secret(config, "IB_ACCOUNT", required=True)'
    assert resolver in source
    assert source.index(resolver) < source.index("ib.connect(")
    assert "account=configured_account" in source
    assert "account=config.IB_ACCOUNT" not in source


def test_ib_account_reference_is_fail_closed_and_rotatable(monkeypatch) -> None:
    with pytest.raises(SecretReferenceError):
        resolve_config_secret(SimpleNamespace(IB_ACCOUNT="DU1234567"), "IB_ACCOUNT", required=True)

    monkeypatch.delenv("MX11_IB_ACCOUNT", raising=False)
    with pytest.raises(SecretReferenceError):
        resolve_config_secret(
            SimpleNamespace(IB_ACCOUNT="env://MX11_IB_ACCOUNT"),
            "IB_ACCOUNT",
            required=True,
        )

    monkeypatch.setenv("MX11_IB_ACCOUNT", "paper-account")
    assert (
        resolve_config_secret(
            SimpleNamespace(IB_ACCOUNT="env://MX11_IB_ACCOUNT"),
            "IB_ACCOUNT",
            required=True,
        )
        == "paper-account"
    )
