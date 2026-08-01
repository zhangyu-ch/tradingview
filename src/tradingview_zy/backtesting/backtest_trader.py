import copy
import datetime
import math
import time
from typing import Dict, List, Tuple

from tradingview_zy.backtesting import futures_contracts
from tradingview_zy.backtesting.accounting import (
    BackTestAccountingError,
    PositionLot,
    add_quantity,
    available_lot_amount,
    close_settlement,
    consume_fifo_lots,
    is_zero_quantity,
    normalize_nonnegative_quantity,
    quantities_close,
    subtract_quantity,
    weighted_average_price,
)
from tradingview_zy.backtesting.base import POSITION, MarketDatas, Operation, Strategy, Trader


def _datetime_to_str(_dt: datetime.datetime, _format="%Y-%m-%d %H:%M:%S"):
    return _dt.strftime(_format)


def _datetime_to_int(_dt: datetime.datetime):
    return int(_dt.timestamp())


class BackTestTrader(Trader):
    """
    回测交易（可继承支持实盘）
    """

    def __init__(
        self,
        name,
        mode="signal",
        market="a",
        init_balance=100000,
        fee_rate=0.0005,
        max_pos=10,
        log=None,
    ):
        """
        交易者初始化
        :param name: 交易者名称
        :param mode: 执行模式 signal 测试信号模式，固定金额开仓；trade 实际买卖模式；real 线上实盘交易
        :param market: 市场 (a 沪深 us 美股  hk 香港  currency 数字货币 futures 期货)
        :param init_balance: 初始资金
        :param fee_rate: 手续费比例
        """

        # 策略基本信息
        self.name = name
        self.mode = mode
        self.market = market

        self.can_close_today: bool = False  # 是否可以平今
        self.can_short: bool = False  # 是否可以做空

        if self.market == "a":
            self.can_close_today = False
            self.can_short = False
        if self.market == "us":
            self.can_close_today = True
            self.can_short = False
        if self.market == "hk":
            self.can_close_today = True
            self.can_short = False
        if self.market == "currency":
            self.can_close_today = True
            self.can_short = True
        if self.market == "futures":
            self.can_close_today = True
            self.can_short = True

        self.allow_mmds = None

        # 资金情况
        self.balance = init_balance if mode == "trade" else 0
        self.fee_rate = fee_rate
        self.fee_total = 0
        self.max_pos = max_pos

        # 单次仓位最大占用资金，避免资金成指数基本扩展，后续市场深度无法提供大资金买入
        self.max_single_pos_balance = None

        # 是否打印日志
        self.log = log
        self.log_history = []

        # 时间统计
        self.use_times = {
            "strategy_close": 0,
            "strategy_open": 0,
            "execute": 0,
            "position_record": 0,
        }

        # TODO 期货合约信息
        # https://www.jiaoyixingqiu.com/shouxufei
        # http://www.hongyuanqh.com/download/20241213/%E4%BF%9D%E8%AF%81%E9%87%91%E6%A0%87%E5%87%8620241213.pdf
        # 手续费分为 百分比 和 每手固定金额，小于1的就是百分比设置，大于1的就是固定金额的
        self.futures_contracts = futures_contracts.futures_contracts

        # 策略对象
        self.strategy: Strategy = None

        # 回测数据对象
        self.datas: MarketDatas = None

        # 当前持仓信息
        self.positions: Dict[str, POSITION] = {}
        self.positions_history: Dict[str, List[POSITION]] = {}
        # 持仓资金历史
        self.positions_balance_history: Dict[str, Dict[str, float]] = {}
        # 持仓盈亏记录
        self.hold_profit_history = {}
        # 资产历史
        self.balance_history: Dict[str, float] = {}

        # 代码订单信息
        self.orders = {}

        # 统计结果数据
        self.results = {
            "1buy": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "2buy": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "l2buy": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "3buy": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "l3buy": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "down_bi_bc_buy": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "down_xd_bc_buy": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "down_pz_bc_buy": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "down_qs_bc_buy": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "1sell": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "2sell": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "l2sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "3sell": {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0},
            "l3sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "up_bi_bc_sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "up_xd_bc_sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "up_pz_bc_sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
            "up_qs_bc_sell": {
                "win_num": 0,
                "loss_num": 0,
                "win_balance": 0,
                "loss_balance": 0,
            },
        }

        # 记录持仓盈亏、资金历史的格式化日期形式
        self.record_dt_format = "%Y-%m-%d %H:%M:%S"

        # 在执行策略前，手动指定执行的开始时间
        self.begin_run_dt: datetime.datetime = None

        # 缓冲区的执行操作，用于在特定时间点批量进行开盘检测后，对要执行的开盘信号再次进行过滤筛选
        self.buffer_opts: List[Operation] = []

    @staticmethod
    def _normalise_fill(result):
        if result is False or result is None:
            return None
        if not isinstance(result, dict):
            raise BackTestAccountingError(
                f"fill result must be a dict, got {type(result).__name__}"
            )
        if "price" not in result or "amount" not in result:
            raise BackTestAccountingError("fill result must contain price and amount")

        amount = normalize_nonnegative_quantity(
            result["amount"], label="fill amount"
        )
        if amount == 0.0:
            return None
        price = float(result["price"])
        if not math.isfinite(price) or price <= 0:
            raise BackTestAccountingError(f"fill price must be positive: {price}")

        normalised = dict(result)
        normalised["price"] = price
        normalised["amount"] = amount
        return normalised

    @staticmethod
    def _remaining_position_after_close(
        pos: POSITION, closed_amount: float, closed_rate: float
    ) -> tuple[float, float, bool]:
        remaining_amount = subtract_quantity(
            pos.amount, closed_amount, label="position amount"
        )
        remaining_rate = subtract_quantity(
            pos.now_pos_rate, closed_rate, label="position rate"
        )
        amount_closed = remaining_amount == 0.0
        rate_closed = remaining_rate == 0.0
        if amount_closed != rate_closed:
            raise BackTestAccountingError(
                "position amount and position rate diverged after close: "
                f"amount={remaining_amount}, rate={remaining_rate}"
            )
        return remaining_amount, remaining_rate, amount_closed and rate_closed

    @staticmethod
    def _executed_close_rate(pos: POSITION, close_amount: float) -> float:
        """Return the logical position rate represented by an actual fill amount."""

        current_amount = normalize_nonnegative_quantity(
            pos.amount, label="position amount"
        )
        current_rate = normalize_nonnegative_quantity(
            pos.now_pos_rate, label="position rate"
        )
        closed_amount = normalize_nonnegative_quantity(
            close_amount, label="close amount"
        )
        if current_amount == 0.0 or current_rate == 0.0 or closed_amount == 0.0:
            raise BackTestAccountingError(
                "cannot calculate a close rate from an empty position or fill"
            )
        remaining_amount = subtract_quantity(
            current_amount, closed_amount, label="position amount"
        )
        if is_zero_quantity(remaining_amount):
            return current_rate
        return normalize_nonnegative_quantity(
            current_rate * closed_amount / current_amount,
            label="executed position rate",
        )

    @classmethod
    def _validated_executed_close_rate(
        cls, pos: POSITION, result: dict, requested_rate: float
    ) -> float:
        derived_rate = cls._executed_close_rate(pos, result["amount"])
        requested = normalize_nonnegative_quantity(
            requested_rate, label="requested position rate"
        )
        if requested == 0.0:
            raise BackTestAccountingError("requested close rate must be greater than zero")
        # Lot rounding may reduce a fill, but an adapter must never report more than
        # the requested logical position rate.
        if derived_rate > requested and not quantities_close(derived_rate, requested):
            raise BackTestAccountingError(
                "actual close fill diverged from and exceeds the requested position rate: "
                f"requested={requested}, executed={derived_rate}"
            )
        declared_rate = result.get("pos_rate")
        if declared_rate is not None:
            declared = normalize_nonnegative_quantity(
                declared_rate, label="declared executed position rate"
            )
            if not quantities_close(declared, derived_rate):
                raise BackTestAccountingError(
                    "fill amount and declared position rate diverged: "
                    f"amount_rate={derived_rate}, declared_rate={declared}"
                )
        return derived_rate

    @staticmethod
    def _apply_open_fill(pos: POSITION, result: dict, fill_rate: float) -> None:
        """Apply an opening fill atomically after all calculations have succeeded."""

        old_amount = normalize_nonnegative_quantity(
            pos.amount, label="position amount"
        )
        old_rate = normalize_nonnegative_quantity(
            pos.now_pos_rate, label="position rate"
        )
        new_price = weighted_average_price(
            pos.price, old_amount, result["price"], result["amount"]
        )
        new_amount = add_quantity(
            old_amount, result["amount"], label="position amount"
        )
        new_rate = min(
            1.0,
            add_quantity(
                old_rate,
                min(1.0, fill_rate),
                label="position rate",
            ),
        )

        pos.price = new_price
        pos.amount = new_amount
        pos.now_pos_rate = new_rate

    @staticmethod
    def _empty_result_stats():
        return {"win_num": 0, "loss_num": 0, "win_balance": 0, "loss_balance": 0}

    def ensure_result(self, signal: str):
        if signal not in self.results:
            self.results[signal] = self._empty_result_stats()
        return self.results[signal]

    def _record_closed_position(self, pos: POSITION, signal: str):
        result_stats = self.ensure_result(signal)
        if pos.profit > 0:
            # 盈利
            result_stats["win_num"] += 1
            result_stats["win_balance"] += pos.profit
        else:
            # 亏损
            result_stats["loss_num"] += 1
            result_stats["loss_balance"] += abs(pos.profit)

        if self.mode == "trade" and not pos.cash_settled_incrementally:
            self.balance += pos.balance + pos.profit

        # 将持仓添加到历史持仓
        if pos.code not in self.positions_history.keys():
            self.positions_history[pos.code] = []
        self.positions_history[pos.code].append(copy.deepcopy(pos))
        # 记录总计手续费
        self.fee_total += pos.fee

    def add_times(self, key, ts):
        if key not in self.use_times.keys():
            self.use_times[key] = 0

        self.use_times[key] += ts
        return True

    def set_strategy(self, _strategy: Strategy):
        """
        设置策略对象
        :param _strategy:
        :return:
        """
        self.strategy = _strategy

    def set_data(self, _data: MarketDatas):
        """
        设置数据对象
        """
        self.datas = _data

    def save_to_pkl(self, key: str):
        """
        将对象数据保存到 pkl 文件中
        """
        save_infos = {
            "name": self.name,
            "mode": self.mode,
            "market": self.market,
            "can_close_today": self.can_close_today,
            "can_short": self.can_short,
            "allow_mmds": self.allow_mmds,
            "balance": self.balance,
            "fee_rate": self.fee_rate,
            "fee_total": self.fee_total,
            "max_pos": self.max_pos,
            "positions": self.positions,
            "positions_history": self.positions_history,
            "positions_balance_history": self.positions_balance_history,
            "hold_profit_history": self.hold_profit_history,
            "balance_history": self.balance_history,
            "orders": self.orders,
            "results": self.results,
        }
        if key is not None:
            from tradingview_zy.file_db import fdb

            fdb.cache_pkl_to_file(key, save_infos)
        return save_infos

    def load_from_pkl(self, key: str, save_infos: dict = None):
        """
        从 pkl 文件 中恢复之前的数据
        """
        if save_infos is None:
            from tradingview_zy.file_db import fdb

            save_infos = fdb.cache_pkl_from_file(key)
            if save_infos is None:
                return False
        self.name = save_infos["name"]
        self.mode = save_infos["mode"]
        self.market = save_infos["market"] if "market" in save_infos.keys() else None
        self.can_close_today = (
            save_infos["can_close_today"]
            if "can_close_today" in save_infos.keys()
            else False
        )
        self.can_short = (
            save_infos["can_short"] if "can_short" in save_infos.keys() else False
        )
        self.allow_mmds = save_infos["allow_mmds"]
        self.balance = save_infos["balance"]
        self.fee_rate = save_infos["fee_rate"]
        self.fee_total = save_infos["fee_total"]
        self.max_pos = save_infos["max_pos"]
        self.results = save_infos["results"]

        self.positions = save_infos["positions"]
        self.positions_history = save_infos["positions_history"]
        self.positions_balance_history = save_infos["positions_balance_history"]
        self.hold_profit_history = save_infos["hold_profit_history"]
        self.balance_history = save_infos["balance_history"]
        self.orders = save_infos["orders"]

        return True

    def get_price(self, code):
        """
        回测中方法，获取股票代码当前的价格，根据最小周期 k 线收盘价
        """
        price_info = self.datas.last_k_info(code)
        return price_info

    def get_now_datetime(self):
        """
        获取当前时间
        """
        if self.mode in ["signal", "trade"]:
            # 回测时用回测的当前时间
            return self.datas.now_date
        return datetime.datetime.now()

    def get_opt_close_uids(
        self, code: str, signal: str, allow_close_uids: list, pos_type: str = None
    ):
        # 实盘中起效果，允许执行的 close_uid 列表
        # 有多种格式
        #       列表格式：['a', 'b', 'c']，表示只在允许的 close_uid 中才允许操作
        #       字典格式：{'buy': ['a', 'b'], 'sell' : ['c', 'd']}，表示 buy 只在做多的仓位中允许，sell 只在做空的仓位中允许
        #       字典格式：{'1buy': ['a', 'b'], '1sell' : ['c', 'd']}，按照给定的买卖点，分别设置平仓信号
        #       字典格式：{'SHFE.RB': ['a', 'b', 'c'], 'SHFE.FU': {'buy': ['a'], 'sell': ['b']}} ,按照代码分别设置
        if allow_close_uids is None:
            return ["clear"]

        # 列表格式的，直接返回
        if isinstance(allow_close_uids, list):
            return allow_close_uids

        # 按照持仓方向，返回对应的 close_uid
        opt_type = "buy" if pos_type == "做多" else "sell"
        if isinstance(allow_close_uids, dict) and opt_type in allow_close_uids.keys():
            return allow_close_uids[opt_type]

        # 按照信号名，返回对应的 close_uid
        if isinstance(allow_close_uids, dict) and signal in allow_close_uids.keys():
            return allow_close_uids[signal]

        # 按照代码分别设置的
        if isinstance(allow_close_uids, dict) and code in allow_close_uids.keys():
            return self.get_opt_close_uids(
                code, signal, allow_close_uids[code], pos_type=pos_type
            )
        return ["clear"]

    # 运行的唯一入口
    def run(self, code, is_filter=False):
        # 如果设置开始执行时间，并且当前时间小于等于设置的时间，则不执行策略
        if (
            self.begin_run_dt is not None
            and self.begin_run_dt >= self.get_now_datetime()
        ):
            return True

        # 优先检查持仓情况
        for _open_uid, pos in self.positions.items():
            if pos.code != code or is_zero_quantity(pos.amount):
                continue
            _time = time.time()
            opts = self.strategy.close(
                code=code, signal=pos.signal, pos=pos, market_data=self.datas
            )
            self.add_times("strategy_close", time.time() - _time)

            if opts is False or opts is None:
                continue
            if isinstance(opts, Operation):
                opts.code = code
                opts = [opts]
            for _opt in opts:
                _opt.code = code
                if self.mode != "signal":
                    allow_close_uids = self.get_opt_close_uids(
                        _opt.code, _opt.signal, self.strategy.allow_close_uids, pos_type=pos.type
                    )
                    if _opt.close_uid not in allow_close_uids:
                        continue
                self.execute(code, _opt, pos)

        # 再执行检查机会方法
        poss = [
            _p
            for _uid, _p in self.positions.items()
            if _p.code == code and not is_zero_quantity(_p.amount)
        ]  # 只获取有持仓的记录

        _time = time.time()
        opts = self.strategy.open(code=code, market_data=self.datas, poss=poss)
        self.add_times("strategy_open", time.time() - _time)

        for opt in opts:
            opt.code = code
            if is_filter:
                # 如果是过滤模式，将操作记录到缓冲区，等待批量执行
                self.buffer_opts.append(opt)
            else:
                self.execute(code, opt, None)

        # 只保留有资金的持仓
        self.positions = {
            _uid: _p for _uid, _p in self.positions.items() if not is_zero_quantity(_p.amount)
        }

        return True

    def run_buffer_opts(self):
        """
        执行缓冲区的操作
        """
        for opt in self.buffer_opts:
            self.execute(opt.code, opt, None)
        self.buffer_opts = []

    # 运行结束，统一清仓
    def end(self):
        for _uid, pos in self.positions.items():
            if (
                pos.balance > 0
                and not is_zero_quantity(pos.amount)
                and not is_zero_quantity(pos.now_pos_rate)
            ):
                self.execute(
                    pos.code,
                    Operation(
                        opt="sell",
                        signal=pos.mmd,
                        msg="退出",
                        code=pos.code,
                        close_uid="clear",
                    ),
                    pos,
                )
        return True

    def update_position_record(self):
        """
        更新所有持仓的盈亏情况
        """
        record_dt = self.get_now_datetime().strftime(self.record_dt_format)

        total_hold_profit = 0
        total_hold_balance = 0
        for _uid, pos in self.positions.items():
            if is_zero_quantity(pos.amount):
                continue
            now_profit, hold_balance = self.position_record(pos)
            total_hold_profit += now_profit
            total_hold_balance += hold_balance

        # 只有在交易模式下，才记录
        if self.mode != "trade":
            return True

        # 记录时间下的总持仓盈亏
        self.hold_profit_history[record_dt] = total_hold_profit

        # 记录当前的持仓金额
        position_balance = {}
        for _uid, pos in self.positions.items():
            if is_zero_quantity(pos.amount):
                continue
            code_price = self.get_price(pos.code)
            if pos.type == "做多":
                code_balance = pos.amount * code_price["close"]
                if self.market == "futures":
                    code_balance = pos.balance - pos.release_balance
            else:
                code_balance = -(pos.amount * code_price["close"])
                if self.market == "futures":
                    code_balance = pos.balance - pos.release_balance
            if pos.code not in position_balance.keys():
                position_balance[pos.code] = 0
            position_balance[pos.code] += code_balance
        position_balance["Cash"] = self.balance

        self.balance_history[record_dt] = (
            total_hold_profit + total_hold_balance + self.balance
        )
        self.positions_balance_history[record_dt] = position_balance

        return None

    def position_record(self, pos: POSITION) -> Tuple[float, float]:
        """
        持仓记录更新
        :param pos:
        :return: 返回持仓的总金额（包括持仓盈亏）
        """
        s_time = time.time()

        hold_balance = pos.balance
        now_profit = 0
        price_info = self.get_price(pos.code)
        if pos.type == "做多":
            # 最大最小盈利百分比，改为单独是价格的百分比
            high_profit_rate = round(
                (price_info["high"] - pos.price) / pos.price * 100, 4
            )
            low_profit_rate = round(
                (price_info["low"] - pos.price) / pos.price * 100, 4
            )
            # 计算盈亏
            now_profit = (price_info["close"] - pos.price) * pos.amount

            if self.market == "futures":
                contract_info = self.futures_contracts[pos.code]
                high_profit_rate = round(
                    (price_info["high"] - pos.price)
                    / pos.price
                    / contract_info["margin_rate_long"]
                    * 100,
                    4,
                )
                low_profit_rate = round(
                    (price_info["low"] - pos.price)
                    / pos.price
                    / contract_info["margin_rate_long"]
                    * 100,
                    4,
                )
                now_profit = (
                    (price_info["close"] - pos.price)
                    * pos.amount
                    * contract_info["symbol_size"]
                )

            pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
            pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

        if pos.type == "做空":
            high_profit_rate = round(
                (pos.price - price_info["low"]) / pos.price * 100, 4
            )
            low_profit_rate = round(
                (pos.price - price_info["high"]) / pos.price * 100, 4
            )
            now_profit = (pos.price - price_info["close"]) * pos.amount

            if self.market == "futures":
                contract_info = self.futures_contracts[pos.code]
                high_profit_rate = round(
                    (pos.price - price_info["low"])
                    / pos.price
                    / contract_info["margin_rate_short"]
                    * 100,
                    4,
                )
                low_profit_rate = round(
                    (pos.price - price_info["high"])
                    / pos.price
                    / contract_info["margin_rate_short"]
                    * 100,
                    4,
                )
                now_profit = (
                    (pos.price - price_info["close"])
                    * pos.amount
                    * contract_info["symbol_size"]
                )

            pos.max_profit_rate = max(pos.max_profit_rate, high_profit_rate)
            pos.max_loss_rate = min(pos.max_loss_rate, low_profit_rate)

        self.add_times("position_record", time.time() - s_time)
        return now_profit, hold_balance

    def position_codes(self):
        """
        获取当前持仓中的股票代码
        """
        codes = list(
            set([_p.code for _uid, _p in self.positions.items() if not is_zero_quantity(_p.amount)])
        )
        return codes

    def hold_positions(self) -> List[POSITION]:
        """
        返回所有持仓记录
        """
        return [_p for _uid, _p in self.positions.items() if not is_zero_quantity(_p.amount)]

    # 做多买入
    def open_buy(self, code, opt: Operation, amount: float = None):
        if self.mode == "signal":
            # 信号模式，固定交易金额
            use_balance = 100000 * min(1.0, opt.pos_rate)
            price = self.get_price(code)["close"]
            amount = round((use_balance / price) * 0.99, 4)
            if self.market == "a":
                # 沪深买入数量是100的整数倍
                amount = int(amount / 100) * 100
            if self.market == "futures":
                # 如果是期货，按照期货的规则，计算可买的最大手数
                contract_config = self.futures_contracts[code]
                amount = int(
                    use_balance
                    / contract_config["margin_rate_long"]
                    / price
                    / contract_config["symbol_size"]
                )
            return {"price": price, "amount": amount}
        else:
            if len(self.hold_positions()) >= self.max_pos:
                return False
            price = self.get_price(code)["close"]

            use_balance = (
                self.balance / (self.max_pos - len(self.hold_positions()))
            ) * 0.99
            use_balance *= min(1.0, opt.pos_rate)
            # 避免资金成指数级别上升设置每笔最大占用资金
            if self.max_single_pos_balance is not None:
                use_balance = min(use_balance, self.max_single_pos_balance)
            amount = use_balance / price
            if self.market == "a":
                amount = int(amount / 100) * 100
            if self.market == "futures":
                contract_config = self.futures_contracts[code]
                amount = int(
                    use_balance
                    / contract_config["margin_rate_long"]
                    / price
                    / contract_config["symbol_size"]
                )

            if amount < 0:
                return False

            return {"price": price, "amount": amount}

    # 做空卖出
    def open_sell(self, code, opt: Operation, amount: float = None):
        if self.mode == "signal":
            use_balance = 100000 * min(1.0, opt.pos_rate)
            price = self.get_price(code)["close"]
            amount = round((use_balance / price) * 0.99, 4)
            if self.market == "a":
                amount = int(amount / 100) * 100
            if self.market == "futures":
                # 如果是期货，按照期货的规则，计算可买的最大手数
                contract_config = self.futures_contracts[code]
                amount = int(
                    use_balance
                    / contract_config["margin_rate_short"]
                    / price
                    / contract_config["symbol_size"]
                )
            return {"price": price, "amount": amount}
        else:
            if len(self.hold_positions()) >= self.max_pos:
                return False
            price = self.get_price(code)["close"]

            use_balance = (
                self.balance / (self.max_pos - len(self.hold_positions()))
            ) * 0.99
            use_balance *= min(1.0, opt.pos_rate)
            # 避免资金成指数级别上升设置每笔最大占用资金
            if self.max_single_pos_balance is not None:
                use_balance = min(use_balance, self.max_single_pos_balance)
            amount = use_balance / price
            if self.market == "a":
                amount = int(amount / 100) * 100
            if self.market == "futures":
                contract_config = self.futures_contracts[code]
                amount = int(
                    use_balance
                    / contract_config["margin_rate_short"]
                    / price
                    / contract_config["symbol_size"]
                )

            if amount < 0:
                return False

            return {"price": price, "amount": amount}

    @staticmethod
    def _close_fill(pos: POSITION, opt: Operation, price, market: str):
        current_amount = normalize_nonnegative_quantity(
            pos.amount, label="position amount"
        )
        current_rate = normalize_nonnegative_quantity(
            pos.now_pos_rate, label="position rate"
        )
        requested_rate = min(
            current_rate,
            normalize_nonnegative_quantity(
                opt.pos_rate, label="requested position rate"
            ),
        )
        if current_amount == 0.0 or current_rate == 0.0 or requested_rate == 0.0:
            return False

        if is_zero_quantity(current_rate - requested_rate):
            amount = current_amount
        else:
            amount = current_amount * requested_rate / current_rate

        if market == "a":
            amount = int(amount / 100) * 100
        elif market == "futures":
            amount = int(amount)
        amount = normalize_nonnegative_quantity(amount, label="close amount")
        if amount == 0.0:
            return False

        executed_rate = BackTestTrader._executed_close_rate(pos, amount)
        return {"price": price, "amount": amount, "pos_rate": executed_rate}

    # 做多平仓
    def close_buy(self, code, pos: POSITION, opt: Operation):
        price = opt.loss_price if opt.loss_price != 0 else self.get_price(code)["close"]
        return self._close_fill(pos, opt, price, self.market)

    # 做空平仓
    def close_sell(self, code, pos: POSITION, opt: Operation):
        price = opt.loss_price if opt.loss_price != 0 else self.get_price(code)["close"]
        return self._close_fill(pos, opt, price, self.market)

    def cal_fee(
        self, code, price: float, balance: float, amount: float, other_info: dict = {}
    ):
        # 普通的计算方式就是 成交金额*手续费率
        fee = balance * self.fee_rate

        # 如果是期货，按照期货的规则，计算手续费
        if self.market == "futures":
            contract_config = self.futures_contracts[code]
            fee_rate = contract_config["fee_rate_open"]
            if "close" in other_info.keys() and other_info["close"]:
                fee_rate = contract_config["fee_rate_close"]
            if "close_today" in other_info.keys() and other_info["close_today"]:
                fee_rate = contract_config["fee_rate_close_today"]
            # 如果 < 1 , 按照成交金额的百分比收取， > 1 按照手数收取
            if fee_rate == 0:
                fee = 0
            elif fee_rate < 1:
                fee = balance * fee_rate
            else:
                fee = fee_rate * amount

        # 沪深A股交易手续费计算
        if self.market == "a":
            # 过户费 + 经手费 + 证管费 + 印花税 + 佣金
            # 过户费率 : 0.01‰
            gh_fee_rate = 0.00001
            # 经手费：0.0341‰
            js_fee_rate = 0.0000341
            # 证管费：0.02‰
            zg_fee_rate = 0.00002
            # 印花费率 : 0.5‰
            yh_fee_rate = 0.0005

            # 费用 = 过户费 + 经手费 + 证管费 + 佣金(最少5元)
            fee = (
                (balance * gh_fee_rate)
                + (balance * js_fee_rate)
                + (balance * zg_fee_rate)
                + max((balance * self.fee_rate), 5)
            )
            if "sell" in other_info.keys() and other_info["sell"]:
                # 卖出有印花税
                fee += balance * yh_fee_rate

        return fee

    # 打印日志信息
    def _print_log(self, msg):
        self.log_history.append(msg)
        if self.log:
            self.log(msg)
        return

    # 执行操作
    def execute(self, code, opt: Operation, pos: POSITION = None):
        _time = time.time()
        try:
            # 如果是交易模式，将 close_uid 都修改为 clear ，使用 strategy 类中的 allow_close_uid 进行控制
            if self.mode != "signal":
                opt.close_uid = "clear"

            # 传递有持仓对象，则表示要进行平仓操作，判断当前是否有正确的持仓信息
            if opt.opt not in {"buy", "sell"}:
                return False

            if pos is not None:
                amount_is_zero = is_zero_quantity(pos.amount)
                rate_is_zero = is_zero_quantity(pos.now_pos_rate)
                if amount_is_zero != rate_is_zero:
                    raise BackTestAccountingError(
                        "position amount and position rate are inconsistent before execution"
                    )
                if pos.balance == 0.0 or amount_is_zero:
                    return True

            signal = opt.signal
            direction = (
                "short"
                if isinstance(opt.info, dict) and opt.info.get("type") in {"short", "做空"}
                else "long"
            )
            # 检查是否在允许做的信号上
            if self.allow_mmds is not None and signal not in self.allow_mmds:
                return True

            if opt.opt == "buy":
                # 检查当前是否有该持仓，如果持仓存在的话，则不进行操作
                if (
                    opt.open_uid in self.positions.keys()
                    and not is_zero_quantity(self.positions[opt.open_uid].amount)
                ):
                    pos = self.positions[opt.open_uid]
                    if pos.now_pos_rate >= 1:
                        return True
                else:
                    pos = POSITION(code=code, signal=signal, open_uid=opt.open_uid)
                    self.positions[opt.open_uid] = pos

            res = None
            order_type = None

            # 买入操作，开仓做多
            if direction == "long" and opt.opt == "buy":
                # 开仓后，不同位置分仓买入的key
                if opt.key in pos.open_keys.keys():
                    return False
                # 修正错误的开仓比例
                opt.pos_rate = min(1.0 - pos.now_pos_rate, opt.pos_rate)

                res = self._normalise_fill(self.open_buy(code, opt))
                if res is None:
                    return False

                hold_balance = 0  # 此次成交占用的资金
                fee = 0  # 此次成交的手续费
                if self.market == "futures":
                    # 期货计算占用保证金，手续费
                    contract_config = self.futures_contracts[code]
                    hold_balance = (
                        res["price"]
                        * res["amount"]
                        * contract_config["symbol_size"]
                        * contract_config["margin_rate_long"]
                    )
                    # 计算总的成交额
                    turnover_balance = (
                        res["price"] * res["amount"] * contract_config["symbol_size"]
                    )
                    fee = self.cal_fee(
                        code, res["price"], turnover_balance, res["amount"]
                    )
                else:
                    # 其他市场默认都是 成交价格 * 成交数量
                    hold_balance = res["price"] * res["amount"]
                    fee = self.cal_fee(code, res["price"], hold_balance, res["amount"])

                pos.type = "做多"
                self._apply_open_fill(pos, res, opt.pos_rate)

                # 记录占用资金与手续费
                pos.balance += hold_balance
                pos.fee += fee

                if self.mode == "trade":
                    self.balance -= hold_balance + fee
                    pos.cash_settled_incrementally = True

                pos.loss_price = opt.loss_price
                pos.open_date = (
                    self.get_now_datetime().strftime("%Y-%m-%d")
                    if pos.open_date is None
                    else pos.open_date
                )
                pos.open_datetime = (
                    self.get_now_datetime()
                    if pos.open_datetime is None
                    else pos.open_datetime
                )
                pos.open_msg = opt.msg
                pos.info = opt.info
                pos.open_keys[opt.key] = opt.pos_rate

                # 本次开仓的记录
                pos.open_records.append(
                    {
                        "datetime": self.get_now_datetime(),
                        "price": res["price"],
                        "amount": res["amount"],
                        "hold_balance": hold_balance,
                        "fee": fee,
                        "open_msg": opt.msg,
                        "open_key": opt.key,
                        "open_uid": opt.open_uid,
                        "pos_rate": opt.pos_rate,
                    }
                )

                pos.lots.append(
                    PositionLot(
                        opened_at=self.get_now_datetime(),
                        amount=res["amount"],
                        price=res["price"],
                        hold_balance=hold_balance,
                        opening_fee=fee,
                        pos_rate=opt.pos_rate,
                    )
                )
                pos.total_open_balance += hold_balance

                order_type = "open_long"

                self._print_log(
                    f"[{code} - {self.get_now_datetime()}] // {signal} 做多买入（{res['price']} - {res['amount']}），原因： {opt.msg}"
                )

            # 买入操作，开仓做空（期货）
            if self.can_short and direction == "short" and opt.opt == "buy":
                # 唯一key判断
                if opt.key in pos.open_keys.keys():
                    return False
                # 修正错误的开仓比例
                opt.pos_rate = min(1.0 - pos.now_pos_rate, opt.pos_rate)

                res = self._normalise_fill(self.open_sell(code, opt))
                if res is None:
                    return False
                hold_balance = 0
                fee = 0
                if self.market == "futures":  # 期货计算占用保证金
                    contract_config = self.futures_contracts[code]
                    hold_balance = (
                        res["price"]
                        * res["amount"]
                        * contract_config["symbol_size"]
                        * contract_config["margin_rate_short"]
                    )
                    turnover_balance = (
                        res["price"] * res["amount"] * contract_config["symbol_size"]
                    )
                    fee = self.cal_fee(
                        code, res["price"], turnover_balance, res["amount"]
                    )
                else:
                    hold_balance = res["price"] * res["amount"]
                    fee = self.cal_fee(code, res["price"], hold_balance, res["amount"])

                pos.type = "做空"
                self._apply_open_fill(pos, res, opt.pos_rate)

                # 记录占用资金与手续费
                pos.balance += hold_balance
                pos.fee += fee

                if self.mode == "trade":
                    self.balance -= hold_balance + fee
                    pos.cash_settled_incrementally = True

                pos.loss_price = opt.loss_price
                pos.open_date = (
                    self.get_now_datetime().strftime("%Y-%m-%d")
                    if pos.open_date is None
                    else pos.open_date
                )
                pos.open_datetime = (
                    self.get_now_datetime()
                    if pos.open_datetime is None
                    else pos.open_datetime
                )
                pos.open_msg = opt.msg
                pos.info = opt.info
                pos.open_keys[opt.key] = opt.pos_rate

                # 本次开仓的记录
                pos.open_records.append(
                    {
                        "datetime": self.get_now_datetime(),
                        "price": res["price"],
                        "amount": res["amount"],
                        "hold_balance": hold_balance,
                        "fee": fee,
                        "open_msg": opt.msg,
                        "open_key": opt.key,
                        "open_uid": opt.open_uid,
                        "pos_rate": opt.pos_rate,
                    }
                )

                pos.lots.append(
                    PositionLot(
                        opened_at=self.get_now_datetime(),
                        amount=res["amount"],
                        price=res["price"],
                        hold_balance=hold_balance,
                        opening_fee=fee,
                        pos_rate=opt.pos_rate,
                    )
                )
                pos.total_open_balance += hold_balance

                order_type = "open_short"

                self._print_log(
                    f"[{code} - {self.get_now_datetime()}] // {signal} 做空卖出（{res['price']} - {res['amount']}），原因： {opt.msg}"
                )

            # 卖出操作，平仓做空（期货）
            if self.can_short and pos.type == "做空" and opt.opt == "sell":
                # 唯一key判断
                if opt.key in pos.close_keys.keys():
                    return False
                if opt.close_uid != "clear" and opt.close_uid in [
                    _or["close_uid"] for _or in pos.close_records
                ]:
                    return False
                # 修正错误的平仓比例
                opt.pos_rate = (
                    pos.now_pos_rate
                    if pos.now_pos_rate < opt.pos_rate
                    else opt.pos_rate
                )

                now_datetime = self.get_now_datetime()
                sellable_amount = available_lot_amount(
                    pos.lots,
                    as_of=now_datetime,
                    can_close_today=self.can_close_today,
                )
                if is_zero_quantity(sellable_amount):
                    return False
                max_sellable_rate = (
                    pos.now_pos_rate * sellable_amount / pos.amount
                    if not is_zero_quantity(pos.amount)
                    else 0.0
                )
                opt.pos_rate = min(opt.pos_rate, max_sellable_rate)
                if is_zero_quantity(opt.pos_rate):
                    return False

                res = self._normalise_fill(self.close_sell(code, pos, opt))
                if res is None:
                    return False

                release_balance = 0  # 平仓释放资金
                fee = 0
                if self.market == "futures":
                    # 计算期货释放保证金与手续费
                    contract_config = self.futures_contracts[code]
                    # 占用保证金
                    release_balance = (
                        res["price"]
                        * contract_config["symbol_size"]
                        * res["amount"]
                        * contract_config["margin_rate_short"]
                    )
                    # 成交金额
                    turnover_balance = (
                        res["price"] * contract_config["symbol_size"] * res["amount"]
                    )

                    # 判断是否平今
                    fee_other = {"close": True}
                    if pos.open_date == _datetime_to_str(
                        self.get_now_datetime(), "%Y-%m-%d"
                    ):
                        fee_other = {"close_today": True}
                    fee = self.cal_fee(
                        code, res["price"], turnover_balance, res["amount"], fee_other
                    )
                else:
                    release_balance = res["price"] * res["amount"]
                    fee = self.cal_fee(
                        code, res["price"], release_balance, res["amount"]
                    )

                executed_pos_rate = self._validated_executed_close_rate(
                    pos, res, opt.pos_rate
                )
                remaining_position = None
                consumption = None
                cash_delta = 0.0
                realised_delta = 0.0
                if opt.close_uid == "clear":
                    remaining_position = self._remaining_position_after_close(
                        pos, res["amount"], executed_pos_rate
                    )
                    consumption = consume_fifo_lots(
                        pos.lots,
                        res["amount"],
                        as_of=self.get_now_datetime(),
                        can_close_today=self.can_close_today,
                    )
                    symbol_size = (
                        self.futures_contracts[code]["symbol_size"]
                        if self.market == "futures"
                        else None
                    )
                    cash_delta, realised_delta = close_settlement(
                        direction="short",
                        consumption=consumption,
                        close_price=res["price"],
                        closing_fee=fee,
                        futures_symbol_size=symbol_size,
                    )

                self._print_log(
                    "[%s - %s] // %s 平仓做空（%s - %s），原因： %s"
                    % (
                        code,
                        self.get_now_datetime(),
                        signal,
                        res["price"],
                        res["amount"],
                        opt.msg,
                    )
                )
                # 本次平仓的记录
                pos.close_records.append(
                    {
                        "datetime": self.get_now_datetime(),
                        "price": res["price"],
                        "amount": res["amount"],
                        "release_balance": release_balance,
                        "fee": fee,
                        "max_profit_rate": pos.max_profit_rate,
                        "max_loss_rate": pos.max_loss_rate,
                        "close_msg": opt.msg,
                        "close_key": opt.key,
                        "close_uid": opt.close_uid,
                        "pos_rate": executed_pos_rate,
                    }
                )

                # 平仓的uid不是 clear，不进行实质性的平仓，只记录当前的盈亏情况
                if opt.close_uid == "clear":
                    assert remaining_position is not None
                    pos.amount, pos.now_pos_rate, position_closed = remaining_position
                    pos.close_keys[opt.key] = executed_pos_rate
                    pos.close_msg = opt.msg
                    pos.close_datetime = self.get_now_datetime()

                    # 记录释放的保证金、手续费和逐笔已实现盈亏。
                    pos.release_balance += release_balance
                    pos.fee += fee
                    pos.realized_profit += realised_delta
                    if self.mode == "trade":
                        self.balance += cash_delta
                    if position_closed:
                        profit = pos.realized_profit
                        denominator = pos.total_open_balance or pos.balance
                        profit_rate = 0.0 if denominator == 0 else profit / denominator * 100

                        pos.profit = profit
                        pos.profit_rate = profit_rate

                        # 打印记录
                        self._print_log(
                            f"[{code} - {signal}] // 平仓做空 (开仓：{pos.open_datetime} / {pos.price} 平仓：{pos.close_datetime} / {res['price']}) (开仓资金：{pos.balance} 平仓资金：{pos.release_balance} 手续费：{pos.fee}) 盈亏：{profit} ({profit_rate:.2f}%)"
                        )

                        self._record_closed_position(pos, signal)

                order_type = "close_short"

            # 卖出操作，平仓做多
            if pos.type == "做多" and opt.opt == "sell":
                # 唯一key判断
                if opt.key in pos.close_keys.keys():
                    return False
                if opt.close_uid != "clear" and opt.close_uid in [
                    _or["close_uid"] for _or in pos.close_records
                ]:
                    return False
                # 修正错误的平仓比例
                opt.pos_rate = (
                    pos.now_pos_rate
                    if pos.now_pos_rate < opt.pos_rate
                    else opt.pos_rate
                )

                now_datetime = self.get_now_datetime()
                sellable_amount = available_lot_amount(
                    pos.lots,
                    as_of=now_datetime,
                    can_close_today=self.can_close_today,
                )
                if is_zero_quantity(sellable_amount):
                    return False
                max_sellable_rate = (
                    pos.now_pos_rate * sellable_amount / pos.amount
                    if not is_zero_quantity(pos.amount)
                    else 0.0
                )
                opt.pos_rate = min(opt.pos_rate, max_sellable_rate)
                if is_zero_quantity(opt.pos_rate):
                    return False

                res = self._normalise_fill(self.close_buy(code, pos, opt))
                if res is None:
                    return False

                release_balance = 0  # 平仓释放资金
                fee = 0
                if self.market == "futures":
                    # 计算期货释放保证金与手续费
                    contract_config = self.futures_contracts[code]
                    # 占用保证金
                    release_balance = (
                        res["price"]
                        * contract_config["symbol_size"]
                        * res["amount"]
                        * contract_config["margin_rate_long"]
                    )
                    # 成交金额
                    turnover_balance = (
                        res["price"] * contract_config["symbol_size"] * res["amount"]
                    )

                    # 判断是否平今
                    fee_other = {"close": True}
                    if pos.open_date == _datetime_to_str(
                        self.get_now_datetime(), "%Y-%m-%d"
                    ):
                        fee_other = {"close_today": True}
                    fee = self.cal_fee(
                        code, res["price"], turnover_balance, res["amount"], fee_other
                    )
                else:
                    release_balance = res["price"] * res["amount"]
                    fee = self.cal_fee(
                        code,
                        res["price"],
                        release_balance,
                        res["amount"],
                        other_info={"sell": True},
                    )

                executed_pos_rate = self._validated_executed_close_rate(
                    pos, res, opt.pos_rate
                )
                remaining_position = None
                consumption = None
                cash_delta = 0.0
                realised_delta = 0.0
                if opt.close_uid == "clear":
                    remaining_position = self._remaining_position_after_close(
                        pos, res["amount"], executed_pos_rate
                    )
                    consumption = consume_fifo_lots(
                        pos.lots,
                        res["amount"],
                        as_of=self.get_now_datetime(),
                        can_close_today=self.can_close_today,
                    )
                    symbol_size = (
                        self.futures_contracts[code]["symbol_size"]
                        if self.market == "futures"
                        else None
                    )
                    cash_delta, realised_delta = close_settlement(
                        direction="long",
                        consumption=consumption,
                        close_price=res["price"],
                        closing_fee=fee,
                        futures_symbol_size=symbol_size,
                    )

                self._print_log(
                    "[%s - %s] // %s 平仓做多（%s - %s），原因： %s"
                    % (
                        code,
                        self.get_now_datetime(),
                        signal,
                        res["price"],
                        res["amount"],
                        opt.msg,
                    )
                )
                # 本次平仓的记录
                pos.close_records.append(
                    {
                        "datetime": self.get_now_datetime(),
                        "price": res["price"],
                        "amount": res["amount"],
                        "release_balance": release_balance,
                        "fee": fee,
                        "max_profit_rate": pos.max_profit_rate,
                        "max_loss_rate": pos.max_loss_rate,
                        "close_msg": opt.msg,
                        "close_key": opt.key,
                        "close_uid": opt.close_uid,
                        "pos_rate": executed_pos_rate,
                    }
                )

                # 平仓的uid不是 clear，不进行实质性的平仓，只记录当前的盈亏情况
                if opt.close_uid == "clear":
                    assert remaining_position is not None
                    pos.amount, pos.now_pos_rate, position_closed = remaining_position
                    pos.close_keys[opt.key] = executed_pos_rate
                    pos.close_msg = opt.msg
                    pos.close_datetime = self.get_now_datetime()

                    # 记录释放的保证金、手续费和逐笔已实现盈亏。
                    pos.release_balance += release_balance
                    pos.fee += fee
                    pos.realized_profit += realised_delta
                    if self.mode == "trade":
                        self.balance += cash_delta
                    if position_closed:
                        profit = pos.realized_profit
                        denominator = pos.total_open_balance or pos.balance
                        profit_rate = 0.0 if denominator == 0 else profit / denominator * 100

                        pos.profit = profit
                        pos.profit_rate = profit_rate

                        # 打印记录
                        self._print_log(
                            f"[{code} - {signal}] // 平仓做多 (开仓：{pos.open_datetime} / {pos.price} 平仓：{pos.close_datetime} / {res['price']}) (开仓资金：{pos.balance} 平仓资金：{pos.release_balance} 手续费：{pos.fee}) 盈亏：{profit} ({profit_rate:.2f}%)"
                        )

                        self._record_closed_position(pos, signal)

                order_type = "close_long"

            if res:
                # 记录订单信息
                if code not in self.orders:
                    self.orders[code] = []
                self.orders[code].append(
                    {
                        "datetime": self.get_now_datetime(),
                        "type": order_type,
                        "price": res["price"],
                        "amount": res["amount"],
                        "info": opt.msg,
                        "open_uid": opt.open_uid,
                        "close_uid": opt.close_uid,
                    }
                )
                return True

            return False
        finally:
            self.add_times("execute", time.time() - _time)

    def order_draw_tv_mark(
        self,
        market: str,
        mark_label: str,
        close_uid: List[str] = None,
        start_dt: datetime = None,
    ):
        # 先删除所有的订单
        from tradingview_zy.db import db

        db.marks_del(market=market, mark_label=mark_label)
        order_colors = {
            "open_long": "red",
            "open_short": "green",
            "close_long": "green",
            "close_short": "red",
        }
        order_shape = {
            "open_long": "earningUp",
            "open_short": "earningDown",
            "close_long": "earningDown",
            "close_short": "earningUp",
        }
        for _code, _orders in self.orders.items():
            # print(f"Draw Mark {_code} : {len(_orders) / 2}")
            for _o in _orders:
                if close_uid is not None:
                    if "close_" in _o["type"] and _o["close_uid"] not in close_uid:
                        continue
                if start_dt is not None:
                    if _datetime_to_int(_o["datetime"]) < _datetime_to_int(
                        start_dt
                    ):
                        continue
                db.marks_add(
                    market,
                    _code,
                    _code,
                    "",
                    _datetime_to_int(_o["datetime"]),
                    mark_label,
                    _o["info"],
                    order_shape[_o["type"]],
                    order_colors[_o["type"]],
                )
        print("Done")
        return True
