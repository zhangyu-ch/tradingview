"""Finite, correlation-keyed Redis RPC for the IB adapter."""

from __future__ import annotations

import json
import math
from typing import Any


class IBRequestTimeout(TimeoutError):
    pass


def redis_rpc(client: Any, queue_name: str, payload: dict[str, Any], timeout: float) -> Any:
    if timeout <= 0:
        raise ValueError("IB RPC timeout must be positive")
    response_key = str(payload.get("key", "")).strip()
    if not response_key:
        raise ValueError("IB RPC payload requires a correlation key")
    wait_seconds = max(1, int(math.ceil(timeout)))

    # A UUID key should be unique, but deleting first also protects tests and callers
    # that supply a deterministic key from accidentally consuming a stale response.
    client.delete(response_key)
    client.lpush(queue_name, json.dumps(payload))
    try:
        response = client.brpop([response_key], timeout=wait_seconds)
        if response is None:
            raise IBRequestTimeout(
                f"IB worker did not answer {queue_name!r} within {wait_seconds}s"
            )
        if len(response) < 2:
            raise RuntimeError("IB worker returned a malformed Redis response")
        return json.loads(response[1])
    finally:
        client.delete(response_key)
