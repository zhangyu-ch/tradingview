import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tradingview_zy.strategies.loader import load_strategy


def test_load_strategy_from_dotted_path(tmp_path):
    module_path = tmp_path / "temporary_strategy_module.py"
    module_path.write_text(
        "class LocalStrategy:\n"
        "    name = 'local_strategy'\n"
        "\n"
        "    def run(self, context):\n"
        "        return []\n",
        encoding="utf-8",
    )

    sys.modules.pop("temporary_strategy_module", None)
    sys.path.insert(0, str(tmp_path))
    try:
        strategy = load_strategy("temporary_strategy_module:LocalStrategy")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("temporary_strategy_module", None)

    assert strategy.name == "local_strategy"


def test_load_strategy_rejects_object_without_run():
    with pytest.raises(TypeError, match="run"):
        load_strategy("pathlib:Path")
