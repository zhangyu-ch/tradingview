import json
from typing import Dict, List

from tradingview_zy import config, fun
from tradingview_zy.db import TableByAlertTask, db
from tradingview_zy.exchange import Market, get_exchange
from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.strategies.base import BatchRunResult
from tradingview_zy.strategies.loader import (
    StrategyRegistryError,
    find_registered_strategy_id_by_path,
    load_registered_strategy,
)
from tradingview_zy.zixuan import ZiXuan


class AlertTasks(object):
    def __init__(self, scheduler=None):
        """
        异步执行后台定时任务
        """
        self.scheduler = scheduler
        self.task_ids = []
        self.log = fun.get_logger()
        self.last_batch_result = None

    @staticmethod
    def strategy_registry():
        return getattr(config, "ALERT_STRATEGIES", {})

    def run(self):
        # Web workers persist task configuration only.  The dedicated scheduler
        # runner supplies the scheduler instance and owns reconciliation.
        if self.scheduler is None:
            return True

        for _id in self.task_ids:
            if self.scheduler.get_job(_id) is not None:
                self.scheduler.remove_job(_id)
        self.task_ids = []

        task_list = self.task_list()
        for _t in task_list:
            if _t.is_run == 1:
                # 根据interval_minutes设置定时任务
                if _t.interval_minutes < 60:
                    # 60分钟以下，按分钟运行
                    _job = self.scheduler.add_job(
                        func=self.alert_run,
                        trigger="cron",
                        args=(_t.id,),
                        id=str(_t.id),
                        name=f"监控-{_t.task_name}",
                        minute=f"*/{_t.interval_minutes}",
                        second="0",
                    )
                else:
                    # 60分钟及以上，按小时运行
                    hours = _t.interval_minutes // 60
                    _job = self.scheduler.add_job(
                        func=self.alert_run,
                        trigger="cron",
                        args=(_t.id,),
                        id=str(_t.id),
                        name=f"监控-{_t.task_name}",
                        hour=f"*/{hours}",
                        minute="0",
                        second="0",
                    )

                self.task_ids.append(_job.id)
        return True

    def _resolve_strategy_id(self, strategy_config: dict) -> str | None:
        strategy_id = strategy_config.get("strategy_id", "")
        if isinstance(strategy_id, str) and strategy_id:
            return strategy_id

        # Backward compatibility for already-saved tasks: a legacy path is accepted only
        # when it exactly matches a server-side registered strategy. It is never imported
        # directly from the database/request value.
        legacy_path = strategy_config.get("strategy_path", "")
        if isinstance(legacy_path, str) and legacy_path:
            return find_registered_strategy_id_by_path(
                self.strategy_registry(), legacy_path
            )
        return None

    @staticmethod
    def _batch_result(value):
        if isinstance(value, BatchRunResult):
            return value
        if isinstance(value, list):
            return BatchRunResult(hits=value)
        raise TypeError("monitoring runner must return BatchRunResult")

    def alert_run(self, alert_id):
        alert_config = self.alert_get(alert_id)
        if alert_config is None:
            self.log.error(f"未找到监控任务 {alert_id}")
            return False

        ex = get_exchange(Market(alert_config.market))
        if ex.now_trading() is False:
            return True

        zx = ZiXuan(alert_config.market)
        stocks = zx.zx_stocks(alert_config.zx_group)
        self.log.info(
            f"执行 {alert_config.task_name} 警报提醒，获取 {alert_config.zx_group} 自选组中 {len(stocks)} 数量股票"
        )

        try:
            strategy_config = json.loads(alert_config.strategy_config or "{}")
        except json.JSONDecodeError as e:
            self.log.error(f"{alert_config.task_name} strategy_config JSON 解析失败：{e}")
            return False
        if not isinstance(strategy_config, dict):
            self.log.error(f"{alert_config.task_name} strategy_config 必须是 JSON 对象")
            return False

        strategy_id = self._resolve_strategy_id(strategy_config)
        strategy_kwargs = strategy_config.get("strategy_kwargs", {})
        if strategy_id is None:
            self.log.error(
                f"{alert_config.task_name} 未配置已注册的 strategy_id；"
                "请在 ALERT_STRATEGIES 中登记策略后重新保存任务"
            )
            return False
        if not isinstance(strategy_kwargs, dict):
            self.log.error(f"{alert_config.task_name} strategy_kwargs 必须是 JSON 对象")
            return False

        try:
            strategy = load_registered_strategy(
                self.strategy_registry(), strategy_id, strategy_kwargs
            )
        except Exception as e:
            # Registry paths are trusted server configuration, but a strategy module or
            # constructor may still fail. Keep the scheduler alive and record the reason.
            self.log.error(f"{alert_config.task_name} 加载已注册策略失败：{e}")
            return False

        runner = MonitoringRunner(exchange=ex, strategy=strategy)
        if callable(getattr(runner, "run", None)):
            batch = self._batch_result(
                runner.run(
                    alert_config.market,
                    stocks,
                    alert_config.frequency,
                )
            )
        else:
            # Temporary compatibility for trusted custom runners that have not yet
            # implemented the batch method. Each result is still aggregated explicitly.
            batch = BatchRunResult()
            for stock in stocks:
                batch.extend(
                    self._batch_result(
                        runner.run_code(
                            alert_config.market,
                            stock["code"],
                            stock.get("name", stock["code"]),
                            alert_config.frequency,
                        )
                    )
                )

        self.last_batch_result = batch
        persistence_ok = True
        for event in batch.hits:
            try:
                db.alert_event_save(
                    market=alert_config.market,
                    task_name=alert_config.task_name,
                    stock_code=event.code,
                    stock_name=event.name,
                    frequency=event.frequency,
                    alert_msg=event.message,
                    action=event.action,
                    score=f"{event.score:.4g}"[:10],
                    event_type="sig",
                    event_time=event.event_time,
                )
            except Exception as error:
                persistence_ok = False
                self.log.error(
                    f"保存 {event.code} 监控信号失败：{error.__class__.__name__}: {error}"
                )

        for failure in batch.failures:
            self.log.error(
                f"监控标的失败 code={failure.code} stage={failure.stage} "
                f"error={failure.error_type}: {failure.message}"
            )

        return batch.ok and persistence_ok

    @staticmethod
    def task_list(market: str = None) -> List[TableByAlertTask]:
        alert_list = db.task_query(market=market)
        return alert_list

    @staticmethod
    def alert_get(_id) -> TableByAlertTask:
        alert_config = db.task_query(id=_id)
        if alert_config is None or len(alert_config) == 0:
            return None
        return alert_config[0]

    def alert_save(self, alert_config: Dict):
        if alert_config["id"] == "":
            del alert_config["id"]
            db.task_save_strategy(**alert_config)
        else:
            alert_config["id"] = int(alert_config["id"])
            db.task_update_strategy(**alert_config)

        self.run()
        return True

    def alert_del(self, alert_id):
        db.task_delete(alert_id)
        self.run()
        return True


if __name__ == "__main__":
    at = AlertTasks(None)
    ls = at.task_list("a")
