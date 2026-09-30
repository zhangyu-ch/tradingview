import inspect
from types import SimpleNamespace

import pandas as pd
import pytest

from tradingview_zy.backtesting.backtest import BackTest


def test_run_uses_configured_start_instead_of_removed_begin_start_dt():
    signature = inspect.signature(BackTest.run)
    assert "begin_start_dt" not in signature.parameters
    assert signature.parameters["loop_callback_fun"].kind is inspect.Parameter.KEYWORD_ONLY
    bt = BackTest()
    with pytest.raises(TypeError, match="begin_start_dt"):
        bt.run(begin_start_dt=pd.Timestamp("2025-01-02"))
    with pytest.raises(TypeError):
        bt.run("5m", pd.Timestamp("2025-01-02"))


@pytest.mark.parametrize("merge_fails", [False, True])
def test_run_process_reports_success_only_after_balance_merge(
    monkeypatch, tmp_path, caplog, merge_fails
):
    class InlineExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def map(self, fn, items):
            return []

    # A few legacy tests reload backtest; patch the globals this class actually uses.
    globals_ = BackTest.run_process.__globals__
    monkeypatch.setitem(globals_, "ProcessPoolExecutor", InlineExecutor)
    if merge_fails:
        def fail_merge(*args, **kwargs):
            raise ValueError("merge failed")

        monkeypatch.setitem(globals_, "pd", SimpleNamespace(DataFrame=fail_merge))

    bt = BackTest()
    bt.mode = "signal"
    bt.save_file = str(tmp_path / "results.pkl")
    bt.frequencys = ["5m"]
    bt.codes = []
    bt.trader = SimpleNamespace(balance_history={})

    assert bt.run_process() is True
    message = "合并回测结果完成，可调用 save 方法进行保存"
    assert (message in caplog.text) is not merge_fails
    assert ("合并资金历史记录异常" in caplog.text) is merge_fails
