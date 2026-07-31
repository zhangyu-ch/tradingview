import json
from typing import Dict, List

from apscheduler.schedulers.background import BackgroundScheduler
from tqdm.auto import tqdm

from tradingview_zy import config, fun, utils
from tradingview_zy.db import AlertTaskValidationError, TableByAlertTask, db
from tradingview_zy.exchange import Market, get_exchange
from tradingview_zy.monitoring import MonitoringRunner
from tradingview_zy.strategies.loader import (
    StrategyRegistryError,
    find_registered_strategy_id_by_path,
    load_registered_strategy,
)
from tradingview_zy.zixuan import ZiXuan


MIN_ALERT_INTERVAL_MINUTES = 1
MAX_ALERT_INTERVAL_MINUTES = 1440


def validate_interval_minutes(value) -> int:
    try:
        interval = int(value)
    except (TypeError, ValueError) as error:
        raise AlertTaskValidationError("运行间隔必须是整数分钟") from error
    if (
        isinstance(value, bool)
        or (isinstance(value, float) and not value.is_integer())
        or interval < MIN_ALERT_INTERVAL_MINUTES
        or interval > MAX_ALERT_INTERVAL_MINUTES
    ):
        raise AlertTaskValidationError(
            f"运行间隔必须在 {MIN_ALERT_INTERVAL_MINUTES}-{MAX_ALERT_INTERVAL_MINUTES} 分钟之间"
        )
    return interval


class AlertTasks(object):
    def __init__(self, scheduler: BackgroundScheduler):
        """
        异步执行后台定时任务
        """
        self.scheduler: BackgroundScheduler = scheduler
        self.task_ids = []
        self.log = fun.get_logger()

    @staticmethod
    def strategy_registry():
        return getattr(config, "ALERT_STRATEGIES", {})

    def run(self):
        for _id in self.task_ids:
            self.scheduler.remove_job(_id)
        self.task_ids = []

        for task in self.task_list():
            if task.is_run != 1:
                continue
            try:
                interval = validate_interval_minutes(task.interval_minutes)
            except AlertTaskValidationError as error:
                self.log.error(f"监控任务 {task.id} 配置无效：{error}")
                continue

            job = self.scheduler.add_job(
                func=self.alert_run,
                trigger="interval",
                args=(task.id,),
                id=str(task.id),
                name=f"监控-{task.task_name}",
                minutes=interval,
            )
            self.task_ids.append(job.id)
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
        notification_lines = []
        for s in tqdm(stocks):
            try:
                events = runner.run_code(
                    alert_config.market,
                    s["code"],
                    s["name"],
                    alert_config.frequency,
                )
                for event in events:
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
                    notification_lines.append(
                        f"{event.name}({event.code}) {event.frequency} "
                        f"{event.action}: {event.message}"
                    )
            except Exception as e:
                self.log.error(f'run {s["code"]} alert exception {e}')

        if alert_config.is_send_msg == 1 and notification_lines:
            try:
                utils.send_fs_msg(
                    alert_config.market,
                    f"{alert_config.task_name} 监控提醒",
                    notification_lines,
                )
            except Exception as error:
                self.log.error(f"{alert_config.task_name} 发送监控消息失败：{error}")

        return True

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
        alert_config["interval_minutes"] = validate_interval_minutes(
            alert_config.get("interval_minutes")
        )
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
