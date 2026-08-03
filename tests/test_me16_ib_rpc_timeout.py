from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "ib_rpc_under_test", ROOT / "src/tradingview_zy/exchange/ib_rpc.py"
)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
IBRequestTimeout = _module.IBRequestTimeout
redis_rpc = _module.redis_rpc


class FakeRedis:
    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def delete(self, key): self.calls.append(("delete", key))
    def lpush(self, queue, payload): self.calls.append(("lpush", queue, payload))
    def brpop(self, keys, timeout):
        self.calls.append(("brpop", tuple(keys), timeout))
        return self.response


def test_timeout_is_finite_explicit_and_cleans_the_response_key() -> None:
    client = FakeRedis(response=None)
    with pytest.raises(IBRequestTimeout, match="within 2s"):
        redis_rpc(client, "ib_ticks", {"key": "request-1", "codes": ["AAPL"]}, 1.2)
    assert ("brpop", ("request-1",), 2) in client.calls
    assert client.calls[0] == ("delete", "request-1")
    assert client.calls[-1] == ("delete", "request-1")


def test_success_decodes_json_and_also_cleans_the_response_key() -> None:
    client = FakeRedis(response=(b"request-2", b'{"ok": true}'))
    assert redis_rpc(client, "ib_info", {"key": "request-2"}, 3) == {"ok": True}
    assert client.calls[-1] == ("delete", "request-2")


def test_zero_or_negative_timeout_is_rejected_before_queueing() -> None:
    client = FakeRedis()
    with pytest.raises(ValueError, match="positive"):
        redis_rpc(client, "ib_ticks", {"key": "request-3"}, 0)
    assert client.calls == []


def test_ib_adapter_has_no_infinite_brpop_and_worker_expires_late_results() -> None:
    adapter = (ROOT / "src/tradingview_zy/exchange/exchange_ib.py").read_text(encoding="utf-8")
    worker = (ROOT / "script/crontab/script_ib_tasks.py").read_text(encoding="utf-8")
    assert "timeout=0" not in adapter
    assert "brpop([args[\"key\"]], 0)" not in adapter
    assert "redis_rpc(" in adapter
    assert 'expire(args["key"], 120)' in worker
