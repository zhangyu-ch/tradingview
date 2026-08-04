#:  -*- coding: utf-8 -*-
"""Generic, registry-validated historical K-line synchronization entry point."""
from __future__ import annotations

from typing import Sequence

from tradingview_zy.sync_batch import configured_sync_cli


def main(argv: Sequence[str] | None = None) -> int:
    return configured_sync_cli(None, argv)


if __name__ == "__main__":
    raise SystemExit(main())
