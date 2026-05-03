import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tradingview_zy.strategies.base import StrategyContext, StrategySignal
from tradingview_zy.strategies.loader import load_strategy


class LocalStrategy:
    name = "local_strategy"

    def run(self, context: StrategyContext):
        return [
            StrategySignal(
                code=context.code,
                name="测试标的",
                action="watch",
                score=88.0,
                message="close above open",
                frequency=context.frequency,
                event_time=context.now,
            )
        ]


def test_load_strategy_from_dotted_path():
    strategy = load_strategy("tests.test_strategy_loader:LocalStrategy")
    assert strategy.name == "local_strategy"


def test_load_strategy_rejects_object_without_run():
    with pytest.raises(TypeError, match="run"):
        load_strategy("pathlib:Path")
