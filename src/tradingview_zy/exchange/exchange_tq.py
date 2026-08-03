from __future__ import annotations

import datetime
import math
import queue
import threading
import time
from typing import Dict, List, Union

import pandas as pd
import pytz
import tqsdk
from tenacity import retry, retry_if_result, stop_after_attempt, wait_random
from tqsdk.objs import Account, Position

from tradingview_zy import config
from tradingview_zy.exchange.exchange import Exchange, Tick
from tradingview_zy.exchange.worker_lifecycle import ManagedWorker


class ExchangeTq(Exchange):
    """天勤期货行情与交易适配器。"""

    g_all_stocks = []

    def __init__(self, use_simulate_account: bool = True):
        # 构造函数只建立本地状态；外部 SDK 和线程在第一次命令时惰性启动。
        self.use_simulate_account = use_simulate_account
        self.command_tasks: queue.Queue[str] = queue.Queue()
        self.past_commands: set[str] = set()
        self.requested_commands: set[str] = set()
        self.res_klines: Dict[str, pd.DataFrame] = {}
        self.res_ticks: Dict[str, Dict[str, float]] = {}
        self.tz = pytz.timezone("Asia/Shanghai")

        self.g_api: tqsdk.TqApi | None = None
        self.g_account: object | None = None
        self.g_account_enable = False
        self._api_lock = threading.RLock()
        self._cache_lock = threading.RLock()
        self._worker = ManagedWorker("tradingview-tq-worker")

    @property
    def t(self) -> threading.Thread | None:
        """Backward-compatible access to the managed worker thread."""
        return self._worker.thread

    def start(self) -> bool:
        """Start the daemon market-data worker explicitly and idempotently."""
        return self._worker.start(self.thread_run_tasks)

    def close(self, timeout: float = 5.0) -> bool:
        """Stop and join the worker, then release the TQ API deterministically."""
        try:
            return self._worker.stop(timeout=timeout)
        except TimeoutError:
            # Closing the API can release a worker blocked inside SDK wait_update.
            self.close_api()
            return self._worker.stop(timeout=timeout)
        finally:
            self.close_api()

    def __enter__(self) -> "ExchangeTq":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close_task_thread(self):
        return self.close()

    def restart_task_thread(self):
        self.close()
        return self.start()

    def _ensure_started(self) -> None:
        self.start()

    def _put_command(self, command: str) -> None:
        self._ensure_started()
        with self._cache_lock:
            if command in self.requested_commands:
                return
            self.requested_commands.add(command)
        self.command_tasks.put(command)

    def _wait_for_cache(self, cache: Dict[str, object], key: str, timeout: float):
        deadline = time.monotonic() + timeout
        while not self._worker.stop_event.is_set():
            with self._cache_lock:
                value = cache.get(key)
                if isinstance(value, pd.DataFrame):
                    return value.copy(deep=True)
                if value is not None:
                    return dict(value) if isinstance(value, dict) else value
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self._worker.stop_event.wait(min(0.05, remaining))
        return None

    @staticmethod
    def _quote_snapshot(quote) -> Dict[str, float]:
        fields = (
            "last_price",
            "bid_price1",
            "ask_price1",
            "highest",
            "lowest",
            "open",
            "volume",
            "pre_settlement",
        )
        snapshot: Dict[str, float] = {}
        for field in fields:
            try:
                snapshot[field] = quote[field]
            except (KeyError, TypeError):
                snapshot[field] = getattr(quote, field)
        return snapshot

    def default_code(self):
        return "KQ.m@SHFE.rb"

    def support_frequencys(self):
        return {
            "w": "W",
            "d": "D",
            "120m": "2H",
            "60m": "1H",
            "30m": "30m",
            "15m": "15m",
            "10m": "10m",
            "6m": "6m",
            "5m": "5m",
            "3m": "3m",
            "2m": "2m",
            "1m": "1m",
            "30s": "30s",
            "10s": "10s",
        }

    def thread_run_tasks(self):
        """Own all asynchronous subscriptions in one managed worker thread."""
        print("启动天勤工作线程-更新K线与tick数据")

        async def get_tick(code):
            api = self.get_api()
            quote = await api.get_quote(code)
            with self._cache_lock:
                self.res_ticks[code] = self._quote_snapshot(quote)
            async with api.register_update_notify() as update_chan:
                async for _ in update_chan:
                    if self._worker.stop_event.is_set():
                        break
                    if api.is_changing(quote):
                        with self._cache_lock:
                            self.res_ticks[code] = self._quote_snapshot(quote)

        async def get_kline(code, frequency):
            api = self.get_api()
            kline = await api.get_kline_serial(
                code, duration_seconds=frequency, data_length=8000
            )
            cache_key = f"{code}_{frequency}"
            with self._cache_lock:
                self.res_klines[cache_key] = kline.copy(deep=True)
            async with api.register_update_notify() as update_chan:
                async for _ in update_chan:
                    if self._worker.stop_event.is_set():
                        break
                    if api.is_changing(kline):
                        with self._cache_lock:
                            self.res_klines[cache_key] = kline.copy(deep=True)

        def reset_api():
            print("天勤 : 重启服务")
            self.close_api()
            with self._cache_lock:
                self.res_klines.clear()
                self.res_ticks.clear()
                self.past_commands.clear()
                commands = tuple(self.requested_commands)
            for command in commands:
                self.command_tasks.put(command)

        while not self._worker.stop_event.is_set():
            try:
                while not self._worker.stop_event.is_set():
                    try:
                        command = self.command_tasks.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        if command in self.past_commands:
                            continue
                        self.past_commands.add(command)
                        parts = command.split(":")
                        if parts[0] == "kline":
                            print("执行 Kline 命令：", command)
                            self.get_api().create_task(
                                get_kline(parts[1], int(parts[2]))
                            )
                        elif parts[0] == "tick":
                            print("执行 Tick 命令：", command)
                            self.get_api().create_task(get_tick(parts[1]))
                    finally:
                        self.command_tasks.task_done()
                if self._worker.stop_event.is_set():
                    break
                self.get_api().wait_update(time.time() + 1)
            except Exception as exc:
                if self._worker.stop_event.is_set():
                    break
                print(f"天勤 循环等待更新行情数据异常 {exc}，重启")
                reset_api()
                self._worker.wait(5.0)
        print("退出天勤任务工作线程")

    def get_api(self, use_account: bool = False):
        """Return the lazily-created API, serializing creation and replacement."""
        with self._api_lock:
            if (
                use_account
                and not self.g_account_enable
                and self.g_api is not None
            ):
                self.g_api.close()
                self.g_api = None

            if self.g_api is None:
                account = self.get_account()
                if use_account and account is None:
                    raise RuntimeError(
                        "使用实盘账户操作，但是并没有配置实盘账户，请检查实盘配置"
                    )
                try:
                    self.g_api = tqsdk.TqApi(
                        account=account,
                        auth=tqsdk.TqAuth(config.TQ_USER, config.TQ_PWD),
                    )
                    self.g_account_enable = True
                except Exception as exc:
                    print("初始化默认的天勤 API 报错，重新尝试初始化无账户的 API：", str(exc))
                    self.g_api = tqsdk.TqApi(
                        auth=tqsdk.TqAuth(config.TQ_USER, config.TQ_PWD)
                    )
                    self.g_account_enable = False
            return self.g_api

    def close_api(self):
        with self._api_lock:
            api, self.g_api = self.g_api, None
            self.g_account_enable = False
        if api is not None:
            api.close()
        return True

    def get_account(self):
        # 使用快期的模拟账号
        if self.use_simulate_account:
            if self.g_account is None:
                self.g_account = tqsdk.TqKq()
            return self.g_account

        # 天勤的实盘账号，如果有设置则使用
        if config.TQ_SP_ACCOUNT == "":
            return None
        if self.g_account is None:
            self.g_account = tqsdk.TqAccount(
                config.TQ_SP_NAME, config.TQ_SP_ACCOUNT, config.TQ_SP_PWD
            )
        return self.g_account

    def all_stocks(self):
        """
        获取支持的所有股票列表
        :return:
        """
        if len(self.g_all_stocks) > 0:
            return self.g_all_stocks

        codes = []
        for c in ["FUTURE", "CONT"]:
            codes += self.get_api().query_quotes(ins_class=c, expired=False)
            # print(f'tq type {c} codes : {len(codes)}')
        infos = self.get_api().query_symbol_info(codes)

        __all_stocks = []
        for code in codes:
            code_df = infos[infos["instrument_id"] == code].iloc[0]
            if code_df["expired"]:
                continue
            __all_stocks.append(
                {
                    "code": code,
                    "name": code_df["instrument_name"],
                }
            )
        self.g_all_stocks = __all_stocks
        return self.g_all_stocks

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_random(min=1, max=5),
        retry=retry_if_result(lambda _r: _r is None),
    )
    def klines(
        self,
        code: str,
        frequency: str,
        start_date: str = None,
        end_date: str = None,
        args=None,
    ) -> Union[pd.DataFrame, None]:
        """
        获取 Kline 线
        :param code:
        :param frequency:
        :param start_date:
        :param end_date:
        :param args:
        :return:
        """
        if args is None:
            args = {}
        if "limit" not in args.keys():
            args["limit"] = 2000
        frequency_maps = {
            "w": 7 * 24 * 60 * 60,
            "d": 24 * 60 * 60,
            "60m": 60 * 60,
            "30m": 30 * 60,
            "15m": 15 * 60,
            "10m": 10 * 60,
            "6m": 6 * 60,
            "5m": 5 * 60,
            "3m": 3 * 60,
            "2m": 2 * 60,
            "1m": 1 * 60,
            "30s": 30,
            "10s": 10,
        }
        if start_date is not None and end_date is not None:
            raise Exception("期货行情不支持历史数据查询，因为账号不是专业版，没权限")

        # 添加命令，并在有界等待中读取由工作线程复制的快照。
        duration = frequency_maps[frequency]
        kline_key = f"{code}_{duration}"
        self._put_command(f"kline:{code}:{duration}")
        klines = self._wait_for_cache(self.res_klines, kline_key, timeout=5.0)
        if klines is None:
            return None
        klines.loc[:, "date"] = klines["datetime"].apply(
            lambda x: datetime.datetime.fromtimestamp(x / 1e9)
        )
        # 转换时区
        klines["date"] = klines["date"].dt.tz_localize(self.tz)
        klines.loc[:, "code"] = code

        return klines[["code", "date", "open", "close", "high", "low", "volume"]]

    def ticks(self, codes: List[str]) -> Dict[str, Tick]:
        """
        获取代码列表的 Tick 信息
        :param codes:
        :return:
        """
        for code in codes:
            self._put_command(f"tick:{code}")
        res_ticks = {}
        for code in codes:
            tick = self._wait_for_cache(self.res_ticks, code, timeout=3.0)
            if tick is None:
                continue
            res_ticks[code] = Tick(
                code=code,
                last=0 if math.isnan(tick["last_price"]) else tick["last_price"],
                buy1=0 if math.isnan(tick["bid_price1"]) else tick["bid_price1"],
                sell1=0 if math.isnan(tick["ask_price1"]) else tick["ask_price1"],
                high=0 if math.isnan(tick["highest"]) else tick["highest"],
                low=0 if math.isnan(tick["lowest"]) else tick["lowest"],
                open=0 if math.isnan(tick["open"]) else tick["open"],
                volume=0 if math.isnan(tick["volume"]) else tick["volume"],
                rate=(
                    0
                    if math.isnan(tick["pre_settlement"])
                    else round(
                        (tick["last_price"] - tick["pre_settlement"])
                        / tick["pre_settlement"]
                        * 100,
                        2,
                    )
                ),
            )
        return res_ticks

    def stock_info(self, code: str) -> Union[Dict, None]:
        """
        获取股票的基本信息
        :param code:
        :return:
        """
        all_stocks = self.all_stocks()
        return next(
            (stock for stock in all_stocks if stock["code"] == code),
            {"code": code, "name": code},
        )

    def now_trading(self):
        """
        返回当前是否是交易时间
        TODO 简单判断 ：9-12 , 13:30-15:00 21:00-02:30
        """
        hour = int(time.strftime("%H"))
        minute = int(time.strftime("%M"))
        if (
            hour in {9, 10, 11, 14, 21, 22, 23, 0, 1}
            or (hour == 13 and minute >= 30)
            or (hour == 2 and minute <= 30)
        ):
            return True
        return False

    def balance(self) -> Account:
        """
        获取账户资产
        """
        api = self.get_api(use_account=True)
        if self.g_account_enable is False:
            raise Exception("账户链接失败，暂时不可用，请稍后尝试")

        account = api.get_account()
        api.wait_update(time.time() + 2)
        return account

    def positions(self, code: str = None) -> Dict[str, Position]:
        """
        获取持仓
        """
        api = self.get_api(use_account=True)
        if self.g_account_enable is False:
            raise Exception("账户链接失败，暂时不可用，请稍后尝试")

        positions = api.get_position(symbol=code)
        api.wait_update(time.time() + 2)
        if isinstance(positions, Position):
            if positions["pos_long"] != 0 or positions["pos_short"] != 0:
                return {code: positions}
            else:
                return {}
        else:
            return {
                _code: positions[_code]
                for _code in positions.keys()
                if positions[_code]["pos_long"] != 0
                or positions[_code]["pos_short"] != 0
            }

    def order(self, code: str, o_type: str, amount: float, args=None):
        return super().order(code, o_type, amount, args=args)

    def all_orders(self):
        """
        获取所有订单 (有效订单)
        """
        api = self.get_api(use_account=True)
        if self.g_account_enable is False:
            raise Exception("账户链接失败，暂时不可用，请稍后尝试")

        orders = api.get_order()
        api.wait_update(time.time() + 5)

        res_orders = []
        for _id in orders:
            _o = orders[_id]
            if _o.status == "ALIVE":
                res_orders.append(_o)

        return res_orders

    def cancel_all_orders(self):
        return self._raise_live_trading_disabled("cancel_all_orders")

    def cancel_order(self, order):
        return self._raise_live_trading_disabled("cancel_order")

    def stock_owner_plate(self, code: str):
        raise Exception("交易所不支持")

    def plate_stocks(self, code: str):
        raise Exception("交易所不支持")


if __name__ == "__main__":
    ex = ExchangeTq(use_simulate_account=False)

    # print("all_stocks", len(ex.all_stocks()))
    # for c in ['FUTURE', 'CONT']:
    #     res = ex.get_api().query_quotes(ins_class=c)
    #     print(c, len(res))

    # main_codes = ex.get_api().query_cont_quotes()
    # print(main_codes)

    # klines = ex.klines("KQ.m@SHFE.ss", "10m")
    # print(klines.tail())

    # klines = klines[klines['date'] <= '2023-10-16 15:00:00']

    # print(len(klines), klines.tail(20))

    # tick = ex.ticks(['DCE.l2401'])
    # print(tick)

    balance = ex.balance()
    print(balance)

    # ex.close_task_thread()
    # ex.restart_task_thread()
    # ex.close_task_thread()
    # ex.close_api()
    print("Done")

    # ex.close_api()
