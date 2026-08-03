import datetime
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Union

import pandas as pd


class POSITION:
    """
    持仓对象
    """

    def __init__(
        self,
        code: str,
        signal: str,
        type: str = None,
        balance: float = 0,
        price: float = 0,
        amount: float = 0,
        loss_price: float = None,
        open_date: str = None,
        open_datetime: datetime.datetime = None,
        close_datetime: datetime.datetime = None,
        profit_rate: float = 0,
        max_profit_rate: float = 0,
        max_loss_rate: float = 0,
        open_msg: str = "",
        close_msg: str = "",
        info: Dict = None,
        open_uid: str = None,
    ):
        self.code: str = code
        self.signal: str = signal
        self.mmd: str = signal
        self.type: str = type
        self.balance: float = balance  # 持仓占用的金额
        self.release_balance: float = 0  # 平仓释放的金额
        self.price: float = price
        self.amount: float = amount  # 持仓数量，为 0 则表示没有持仓
        self.loss_price: float = loss_price
        self.open_date: str = open_date
        self.open_datetime: datetime = open_datetime
        self.close_datetime: datetime = close_datetime
        self.fee: float = 0  # 记录总过的手续费之和（开仓+平仓）
        self.profit: float = 0  # 收益金额
        self.profit_rate: float = profit_rate  # 收益率
        self.max_profit_rate: float = max_profit_rate  # 仅供参考，不太精确
        self.max_loss_rate: float = max_loss_rate  # 仅供参考，不太精确
        self.open_msg: str = open_msg
        self.close_msg: str = close_msg
        self.info: Dict = info
        self.open_uid: str = open_uid
        # 仓位控制相关
        # 记录当前开仓所占比例
        self.now_pos_rate: float = 0
        # 记录开仓的唯一key记录，避免多次重复开仓
        self.open_keys: Dict[str, float] = {}
        # 记录平仓的唯一key记录，避免多次重复平仓
        self.close_keys: Dict[str, float] = {}

        # 开仓记录信息
        self.open_records: List[dict] = []
        # 平仓记录信息
        self.close_records: List[dict] = []

    def __close_records_by_uids(self, uids: List[str] = None):
        """
        根据 uid 关闭记录
        """
        if uids is None:
            return None
        if "clear" not in uids:
            uids.append("clear")
        # 按照时间从早到晚排序
        close_profit = sorted(
            self.close_uid_profit.items(), key=lambda _r: _r[1]["close_datetime"]
        )
        for _r in close_profit:
            if _r[0] in uids:
                return _r[1]
        raise Exception(
            f"{self.code} - {self.mmd} - {self.open_datetime} 没有找到对应的平仓记录: {uids}"
        )

    def get_close_profit(self, uids: List[str] = None):
        if uids is None:
            return {
                "close_datetime": self.close_datetime,
                "profit": self.profit,
                "profit_rate": self.profit_rate,
                "max_profit_rate": self.max_profit_rate,
                "max_loss_rate": self.max_loss_rate,
                "close_msg": self.close_msg,
            }
        close_profit = self.__close_records_by_uids(uids)
        return {
            "close_datetime": close_profit["close_datetime"],
            "profit": close_profit["profit"],
            "profit_rate": close_profit["profit_rate"],
            "max_profit_rate": close_profit["max_profit_rate"],
            "max_loss_rate": close_profit["max_loss_rate"],
            "close_msg": close_profit["close_msg"],
        }

    # def __str__(self):
    #     return f'code : {self.code} mmd : {self.mmd} type : {self.type}'


class Operation:
    """
    策略返回的操作指示对象
    """

    def __init__(
        self,
        code: str,
        opt: str,
        signal: str,
        loss_price: float = 0,
        info=None,
        msg: str = "",
        pos_rate: float = 1,
        key: str = "id",
        open_uid: str = None,
        close_uid: str = "clear",
    ):
        # TODO 历史原因，后期 opt 值修改为 open  close ，分别表示 开仓与平仓
        # TODO 但是为了兼容之前的  buy sell ，这里单独做个转换，内部还是使用 buy sell 进行判断开平仓
        opt_map = {
            "open": "buy",
            "close": "sell",
        }
        # 旧的 操作指示  buy  买入  sell  卖出 （buy 表示开仓 sell 表示平仓，新的用 open  close 进行表示了）
        # 新的 操作指示  open 开仓  close  平仓
        self.opt: str = opt if opt not in opt_map.keys() else opt_map[opt]

        # 触发指示的
        # 买卖点 例如：1buy 2buy l2buy 3buy l3buy  1sell 2sell l2sell 3sell l3sell down_pz_bc_buy
        # 背驰点 例如：down_bi_bc_buy down_pz_bc_buy down_qs_bc_buy up_bi_bc_sell up_pz_bc_sell up_qs_bc_sell
        self.signal: str = signal
        self.mmd: str = signal
        self.loss_price: float = loss_price  # 止损价格
        self.info: Dict[str, object] = info  # 自定义保存的一些信息
        self.msg: str = msg
        self.pos_rate: float = pos_rate  # 开仓 or 平仓 所占的比例
        # 避免同一位置多次开平仓，需要在该位置设置一个独立的 key 值，例如当前笔结束的日期等
        self.key: str = key
        self.code: str = code  # 操作的标的代码
        # 开车的标记uid，同一个uid同时只能有一个持仓
        self.open_uid: str = f"{code}:{signal}" if open_uid is None else open_uid
        # 平仓的标记uid，在信号模式下，只有 clear 才算彻底清仓，其他只是标记
        self.close_uid: str = close_uid

    def __str__(self):
        return f"signal {self.signal} opt {self.opt} loss_price {self.loss_price} msg: {self.msg}"


class MarketDatas(ABC):
    """
    市场数据类，用于在回测与实盘获取指定行情数据类
    """

    def __init__(self, market: str, frequencys: List[str]):
        """
        初始化
        """
        self.market = market
        self.frequencys = frequencys

    @abstractmethod
    def klines(self, code, frequency) -> pd.DataFrame:
        """
        获取标的周期内的k线数据
        """

    @abstractmethod
    def last_k_info(self, code) -> dict:
        """
        获取最后一根K线数据，根据 frequencys 最后一个 小周期获取数据
        return dict {'date', 'open', 'close', 'high', 'low'}
        """

    def custom_data(self, code, frequency, args=None):
        """
        获取自定义数据
        """
        return None


class Trader(ABC):

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
        # 策略基本信息
        self.name = name
        self.mode = mode
        self.market = market
        self.max_pos = max_pos

    @abstractmethod
    def get_price(self, code) -> dict:
        """
        回测中方法，获取股票代码当前的价格，根据最小周期 k 线收盘价
        """

    @abstractmethod
    def hold_positions(self) -> List[POSITION]:
        """
        返回所有持仓记录
        """


class Strategy(ABC):
    """
    交易策略基类
    """

    def __init__(self):
        # 实盘中起效果，允许执行的 close_uid 列表
        # 有两种格式
        #       列表格式：['a', 'b', 'c']，表示只在允许的 close_uid 中才允许操作
        #       字典格式：{'buy': ['a', 'b'], 'sell' : ['c', 'd']}，表示 buy 只在做多的仓位中允许，sell 只在做空的仓位中允许
        self.allow_close_uids = None
        self.use_times = {}
        pass

    def add_times(self, key: str, use_time: float):
        if key not in self.use_times.keys():
            self.use_times[key] = {"num": 1, "times": use_time}
        else:
            self.use_times[key]["num"] += 1
            self.use_times[key]["times"] += use_time
        return True

    def write_log(self, file_name: str, msg: str):
        log = logging.getLogger(file_name or __name__)
        if not log.handlers:
            log.addHandler(logging.StreamHandler())
        log.setLevel(logging.INFO)
        log.info(msg)
        return True

    @abstractmethod
    def open(
        self, code, market_data: MarketDatas, poss: List[POSITION]
    ) -> List[Operation]:
        """
        观察行情数据，给出开仓操作建议
        :param code:
        :param market_data:
        :param poss: 当前代码的持仓列表
        :return:
        """

    @abstractmethod
    def close(
        self, code, signal: str, pos: POSITION, market_data: MarketDatas
    ) -> Union[Operation, None, List[Operation]]:
        """
        盯当前持仓，给出平仓当下建议
        :param code:
        :param signal:
        :param pos:
        :param market_data:
        :return:
        """

    def on_bt_loop_start(self, bt):
        """
        回测专用，每次每个代码回测循环都会执行这个方法

        @param bt: 回测 BackTest 对象
        """
        pass

    def is_filter_opts(self):
        """
        是否对产生的开盘信号进行二次过滤操作，比如在统一的时间执行开盘信号检测，在对产生的所有信号进行二次过滤，最终只执行其中过滤后的操作
        需要再实际的策略中进行方法重写
        """
        return False

    def filter_opts(
        self,
        opts: List[Operation],
        trader: Trader = None,
    ):
        """
        过滤开盘信号，返回过滤后的操作列表
        需要再实际的策略中进行方法重写
        """
        return opts

    def clear(self):
        """
        回测专用，回测结束后，清理一些不需要的变量，避免被 pickle 保存
        """
        pass



def fee_a(opt: str, price: float, amount: float):
    """
    A 股交易所费用计算方法
    """
    fee_rate = 0.3  # 单位 %
    min_fee = 5
    yhs_rate = 0.1  # 印花税 单位 % 出让方（卖出）收取
    ghf_rate = 0.02  # 过户费 单位 % 双向收取

    trade_volume = price * amount
    fee_sum = max([min_fee, trade_volume * fee_rate / 100])
    if opt == "sell":
        fee_sum += trade_volume * yhs_rate / 100
    fee_sum += trade_volume * ghf_rate / 100
    return fee_sum


def fee_us(opt: str, price: float, amlunt: float):
    """
    美股的交易费用计算
    """
    pass

