from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_dingding_helpers_and_config_contract_are_removed() -> None:
    offenders: list[str] = []
    for root_name in ("src", "script", "web"):
        for path in (ROOT / root_name).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in ("send_dd_msg", "config_get_dingding_keys", "DINGDING_KEY_"):
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{token}")
    assert offenders == []


def test_retired_feishu_channel_is_not_part_of_shared_utilities() -> None:
    source = (ROOT / "src/tradingview_zy/utils.py").read_text(encoding="utf-8")
    assert "send_fs_msg" not in source
    assert "config_get_feishu_keys" not in source
    assert "def config_get_proxy(" in source


def test_channel_documentation_sets_reintroduction_requirements() -> None:
    text = (ROOT / "docs/messaging-channels.md").read_text(encoding="utf-8")
    assert "legacy DingTalk" in text
    assert "bounded HTTP timeouts" in text
    assert "per-market routing tests" in text
