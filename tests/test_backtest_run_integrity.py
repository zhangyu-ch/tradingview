import datetime
from types import SimpleNamespace

import pytest

from tradingview_zy.backtesting.backtest import BackTest
from tradingview_zy.backtesting.run_result import BackTestRunError


class FakeProgress:
    def __init__(self):
        self.total = None

    def reset(self, *, total):
        self.total = total


class FakeData:
    def __init__(self, dates):
        self.original_dates = list(dates)
        self.loop_datetime_list = {"1m": list(dates), "5m": list(dates)}
        self.bar = FakeProgress()
        self.now_date = dates[0] if dates else None
        self.load_data_to_cache = False
        self.init_calls = []

    def init(self, base_code, frequency):
        self.init_calls.append((base_code, frequency))

    def next(self, frequency):
        dates = self.loop_datetime_list[frequency]
        if not dates:
            return False
        self.now_date = dates.pop(0)
        return True


class FakeTrader:
    def __init__(self, *, fail_code=None, fail_position_update=False):
        self.datas = None
        self.buffer_opts = []
        self.fail_code = fail_code
        self.fail_position_update = fail_position_update
        self.run_calls = []
        self.end_calls = 0
        self.filter_calls = 0
        self.fee_total = 0

    def update_position_record(self):
        if self.fail_position_update:
            raise RuntimeError("position update failed")

    def run(self, code, is_filter=False):
        self.run_calls.append((self.datas.now_date, code, is_filter))
        if code == self.fail_code:
            # Simulate a strategy that appended an operation before it failed. The
            # partial-run path must not execute or carry this operation forward.
            self.buffer_opts.append(object())
            raise ValueError(f"strategy failed for {code}")

    def run_buffer_opts(self):
        if self.buffer_opts:
            raise AssertionError("failed timestamp operations must be discarded")
        self.buffer_opts = []

    def end(self):
        self.end_calls += 1


class FakeStrategy:
    def __init__(self):
        self.clear_calls = 0
        self.loop_starts = 0

    def on_bt_loop_start(self, bt):
        self.loop_starts += 1

    def is_filter_opts(self):
        return True

    def filter_opts(self, opts, trader):
        trader.filter_calls += 1
        return opts

    def clear(self):
        self.clear_calls += 1


def make_backtest(dates, *, codes=("OK",), trader=None):
    bt = BackTest()
    bt.frequencys = ["5m", "1m"]
    bt.base_code = "BASE"
    bt.codes = list(codes)
    bt.load_data_to_cache = True
    bt.datas = FakeData(dates)
    bt.trader = trader or FakeTrader()
    bt.trader.datas = bt.datas
    bt.strategy = FakeStrategy()
    bt.mode = "signal"
    return bt


def test_begin_start_dt_filters_the_real_replay_lists_and_progress_total():
    dates = [
        datetime.datetime(2024, 1, 2, 9, 30),
        datetime.datetime(2024, 1, 2, 9, 31),
        datetime.datetime(2024, 1, 2, 9, 32),
    ]
    bt = make_backtest(dates)

    assert bt.run(next_frequency="1m", begin_start_dt=dates[1]) is True

    assert [call[0] for call in bt.trader.run_calls] == dates[1:]
    assert bt.datas.bar.total == 2
    assert bt.last_run_result.status == "success"
    assert bt.last_run_result.attempted_timestamps == 2
    assert bt.last_run_result.completed_timestamps == 2
    assert bt.last_run_result.begin_start_dt == dates[1]
    assert bt.trader.end_calls == 1
    assert bt.strategy.clear_calls == 1


def test_begin_start_dt_type_or_timezone_mismatch_fails_explicitly():
    dates = [datetime.datetime(2024, 1, 2, 9, 30)]
    bt = make_backtest(dates)
    aware_start = datetime.datetime(
        2024, 1, 2, 9, 30, tzinfo=datetime.timezone.utc
    )

    with pytest.raises(BackTestRunError, match="initialization") as captured:
        bt.run(next_frequency="1m", begin_start_dt=aware_start)

    assert captured.value.failure.error_type == "ValueError"
    assert bt.last_run_result.status == "failed"
    assert bt.trader.end_calls == 0


def test_default_run_is_fail_fast_and_records_the_exact_failure():
    dates = [datetime.datetime(2024, 1, 2, 9, 30)]
    trader = FakeTrader(fail_code="BAD")
    bt = make_backtest(dates, codes=("BAD", "OK"), trader=trader)

    with pytest.raises(BackTestRunError, match="strategy/BAD") as captured:
        bt.run(next_frequency="1m")

    result = bt.last_run_result
    assert result.status == "failed"
    assert result.attempted_timestamps == 1
    assert result.completed_timestamps == 0
    assert len(result.failures) == 1
    assert captured.value.failure.code == "BAD"
    assert captured.value.failure.phase == "strategy"
    assert captured.value.failure.timestamp == dates[0]
    assert "strategy failed for BAD" in captured.value.failure.message
    assert trader.end_calls == 0
    assert bt.strategy.clear_calls == 1


def test_diagnostic_continue_mode_returns_partial_and_blocks_publishable_results(tmp_path):
    dates = [
        datetime.datetime(2024, 1, 2, 9, 30),
        datetime.datetime(2024, 1, 2, 9, 31),
    ]
    trader = FakeTrader(fail_code="BAD")
    bt = make_backtest(dates, codes=("BAD", "OK"), trader=trader)
    bt.save_file = str(tmp_path / "partial.pkl")

    assert bt.run(next_frequency="1m", continue_on_error=True) is False

    result = bt.last_run_result
    assert result.status == "partial"
    assert result.attempted_timestamps == 2
    assert result.completed_timestamps == 0
    assert len(result.failures) == 2
    assert trader.end_calls == 0
    assert trader.buffer_opts == []

    with pytest.raises(RuntimeError, match="不能生成绩效指标"):
        bt.result(is_print=False)
    with pytest.raises(RuntimeError, match="不能生成 PyFolio"):
        bt.result_by_pyfolio()
    with pytest.raises(RuntimeError, match="不能保存发布级结果"):
        bt.save()
    with pytest.raises(RuntimeError, match="不能生成回测图表"):
        bt.backtest_charts()
    with pytest.raises(RuntimeError, match="不能生成按平仓收益图表"):
        bt.backtest_charts_by_close_profit()
    assert not (tmp_path / "partial.pkl").exists()


def test_continue_mode_does_not_run_callback_or_filter_for_a_failed_timestamp():
    dates = [datetime.datetime(2024, 1, 2, 9, 30)]
    trader = FakeTrader(fail_code="BAD")
    bt = make_backtest(dates, codes=("BAD",), trader=trader)
    callbacks = []

    assert (
        bt.run(
            next_frequency="1m",
            continue_on_error=True,
            loop_callback_fun=lambda current: callbacks.append(current.datas.now_date),
        )
        is False
    )

    assert callbacks == []
    assert trader.filter_calls == 0
    assert trader.buffer_opts == []
