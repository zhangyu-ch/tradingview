"""Dedicated monitoring scheduler process.

Run this process separately from every Web worker::

    PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/scheduler.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
WEB = pathlib.Path(__file__).resolve().parent
CL_APP = WEB / "cl_app"
for path in (SRC, CL_APP):
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)

from scheduler_runtime import (  # noqa: E402
    SchedulerAlreadyRunningError,
    run_scheduler,
)


def main() -> int:
    try:
        run_scheduler()
        return 0
    except SchedulerAlreadyRunningError as exc:
        print(f"调度器未启动：{exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"调度器启动失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
