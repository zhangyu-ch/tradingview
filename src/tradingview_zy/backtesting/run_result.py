from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Literal


RunStatus = Literal["success", "partial", "failed"]


@dataclass(frozen=True)
class BackTestRunFailure:
    phase: str
    code: str | None
    timestamp: datetime.datetime | None
    error_type: str
    message: str
    traceback: str


@dataclass(frozen=True)
class BackTestRunResult:
    status: RunStatus
    attempted_timestamps: int
    completed_timestamps: int
    begin_start_dt: datetime.datetime | None
    duration_seconds: float
    failures: tuple[BackTestRunFailure, ...] = ()

    @property
    def is_success(self) -> bool:
        return self.status == "success"

    @property
    def is_complete(self) -> bool:
        return self.is_success and not self.failures

    def __bool__(self) -> bool:
        return self.is_success


class BackTestRunError(RuntimeError):
    def __init__(self, failure: BackTestRunFailure, result: BackTestRunResult):
        location = failure.phase
        if failure.code is not None:
            location += f"/{failure.code}"
        if failure.timestamp is not None:
            location += f"@{failure.timestamp}"
        super().__init__(
            f"backtest failed during {location}: {failure.error_type}: {failure.message}"
        )
        self.failure = failure
        self.result = result
