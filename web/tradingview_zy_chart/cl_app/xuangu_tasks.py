import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from tradingview_zy import config
from tradingview_zy.exchange import Market, get_exchange
from tradingview_zy.selection import SelectionRunner
from tradingview_zy.strategies.loader import load_registered_strategy
from tradingview_zy.zixuan import ZiXuan


class XuanguTasks(object):
    def __init__(self, scheduler: BackgroundScheduler):
        self.scheduler = scheduler
        self.running_tasks = {}

    def xuangu_task_config_list(self):
        return getattr(config, "XUANGU_STRATEGIES", {})

    def _run_xuangu_job(self, market, task_name, frequencys, opt_type, zx_group, target_zx_group):
        registry = self.xuangu_task_config_list()
        strategy = load_registered_strategy(registry, task_name)
        ex = get_exchange(Market(market))
        zx = ZiXuan(market)
        if zx_group == "all":
            stocks = ex.all_stocks()
            if market == "a":
                stocks = [
                    s
                    for s in stocks
                    if s["code"][0:5] in ["SZ.00", "SZ.30", "SH.60", "SH.68"]
                ]
            if market == "futures":
                stocks = [s for s in stocks if s["code"][-2:] == "L8"]
        else:
            stocks = zx.zx_stocks(zx_group)
        runner = SelectionRunner(exchange=ex, strategy=strategy)
        results = []
        for frequency in frequencys:
            results.extend(runner.run(market, stocks, frequency))
        if target_zx_group:
            zx.clear_zx_stocks(target_zx_group)
            for event in results:
                zx.add_stock(target_zx_group, event.code, event.name, memo=event.message)
        self.running_tasks[task_name] = results
        return True

    def run_xuangu(self, market, task_name, frequencys, opt_type, zx_group, target_zx_group=None):
        """执行选股。"""
        if task_name not in self.xuangu_task_config_list().keys():
            return False

        task_id = f"{market}_{task_name}"
        if (
            self.scheduler is not None
            and task_id in self.scheduler.my_task_list.keys()
            and self.scheduler.my_task_list[task_id]["state"] != "已完成"
        ):
            return False

        if self.scheduler is None:
            return self._run_xuangu_job(
                market, task_name, frequencys, opt_type, zx_group, target_zx_group
            )

        task_config = self.xuangu_task_config_list()[task_name]
        task_display_name = task_config.get("name", task_name)
        task_name_for_scheduler = f"{market}:{task_display_name} {frequencys} -> 【{target_zx_group}】"

        self.scheduler.add_job(
            func=self._run_xuangu_job,
            args=(
                market,
                task_name,
                frequencys,
                opt_type,
                zx_group,
                target_zx_group,
            ),
            trigger="date",
            next_run_time=datetime.datetime.now(),
            id=task_id,
            name=task_name_for_scheduler,
        )
        return True


if __name__ == "__main__":
    xt = XuanguTasks(None)
    print(xt.xuangu_task_config_list())
