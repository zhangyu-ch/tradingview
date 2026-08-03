#:  -*- coding: utf-8 -*-
"""Checkpointed K-line synchronization entry point.

Importing this module is side-effect free.  Provider construction, universe
loading and synchronization only happen from :func:`main`.
"""
from pathlib import Path
from typing import Sequence

from tradingview_zy.sync_batch import configured_sync_cli

DEFAULT_CONFIG = Path(__file__).with_name("sync_configs") / "us_klines.json"


def main(argv: Sequence[str] | None = None) -> int:
    return configured_sync_cli(DEFAULT_CONFIG, argv)


if __name__ == "__main__":
    raise SystemExit(main())
