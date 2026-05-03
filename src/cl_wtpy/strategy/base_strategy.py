import pandas as pd
from pandas.core.api import DataFrame as DataFrame
from typing import Dict, List

try:
    from wtpy import BaseCtaStrategy, CtaContext, WtBarRecords
except ModuleNotFoundError:
    class BaseCtaStrategy:
        def __init__(self, name):
            self.name = name

    CtaContext = object
    WtBarRecords = object

from tradingview_zy.backtesting.base import MarketDatas, Operation, POSITION, Strategy


class WTPYMarketData(MarketDatas):

    def __init__(self, context: CtaContext, frequencys: List[str]):
        self.context: CtaContext = context
        super().__init__("futures", frequencys)

    @staticmethod
    def bars_to_df_klines(code: str, bars: WtBarRecords) -> pd.DataFrame:
        """
        将 wtpy 的 K 线数据转换成通用 DataFrame 数据
        """
        bars_df = bars.to_df()
        # Index(['date', 'bartime', 'open', 'high', 'low', 'close', 'settle', 'money',
        #        'volume', 'hold', 'diff'],
        #       dtype='object')
        bars_df["code"] = code
        bars_df["date"] = pd.to_datetime(bars_df["bartime"])
        return bars_df[["code", "date", "open", "close", "high", "low", "volume"]]

    def klines(self, code, frequency) -> DataFrame:
        df_bars = self.context.stra_get_bars(code, frequency, 2000, isMain=True)
        return self.bars_to_df_klines(code, df_bars)

    def last_k_info(self, code) -> dict:
        kline = self.klines(code, self.frequencys[-1])
        return {
            "date": kline.iloc[-1]["date"],
            "open": float(kline.iloc[-1]["open"]),
            "close": float(kline.iloc[-1]["close"]),
            "high": float(kline.iloc[-1]["high"]),
            "low": float(kline.iloc[-1]["low"]),
        }

    def get_cl_data(self, code, frequency, cl_config: dict = None):
        raise NotImplementedError("缠论运行路径已移除，WTPYMarketData 仅提供通用 K 线数据")


class BaseStrategy(BaseCtaStrategy):
    """
    WTPY 通用策略类
    """

    def __init__(self, name: str, strategy: Strategy, code: str, period: str):
        BaseCtaStrategy.__init__(self, name)

        self.code = code
        self.period = period

        # 通用策略
        self.STR = strategy

        # wtpy 数据转换
        self.datas = None

        # 记录持仓 TODO 实盘需要进行持久化
        self.positions: Dict[str, POSITION] = {}

    def on_init(self, context: CtaContext):
        """
        初始化策略数据
        """
        if self.datas is None:
            self.datas = WTPYMarketData(context, [self.period])

        context.stra_log_text("Strategy inited")

    def get_poss(self, code) -> List[POSITION]:
        """
        获取代码的持仓记录
        """
        poss = []
        for _k in self.positions.keys():
            if code in poss:
                poss.append(self.positions[_k])
        return poss

    def open_buy(self, context: CtaContext, code: str, amount: float, opt: Operation):
        """
        开仓买入
        """
        res = context.stra_enter_long(code, amount, "enterlong")
        context.stra_log_text(opt.msg)
        pos: POSITION = POSITION(
            code=code,
            signal=opt.signal,
            type="long",
            balance=1,
            price=0,
            amount=amount,
            loss_price=opt.loss_price,
            open_msg=opt.msg,
            info=opt.info,
        )
        pos_key = "%s_%s" % (code, opt.mmd)
        self.positions[pos_key] = pos
        return res

    def open_sell(self, context: CtaContext, code: str, amount: float, opt: Operation):
        """
        开仓卖出
        """
        res = context.stra_enter_short(code, amount, "entershort")
        context.stra_log_text(opt.msg)
        pos: POSITION = POSITION(
            code=code,
            signal=opt.signal,
            type="short",
            balance=1,
            price=0,
            amount=amount,
            loss_price=opt.loss_price,
            open_msg=opt.msg,
            info=opt.info,
        )
        pos_key = "%s_%s" % (code, opt.mmd)
        self.positions[pos_key] = pos
        return res

    def close_buy(self, context: CtaContext, code, opt: Operation):
        pos_key = "%s_%s" % (code, opt.mmd)
        if pos_key not in self.positions.keys():
            context.stra_log_text("平多仓，没有查找到对应的持仓记录：%s" % pos_key)
            return None
        pos: POSITION = self.positions[pos_key]
        res = context.stra_exit_long(code, pos.amount, "exitlong")
        context.stra_log_text(opt.msg)

        del self.positions[pos_key]
        return res

    def close_sell(self, context: CtaContext, code, opt: Operation):
        pos_key = "%s_%s" % (code, opt.mmd)
        if pos_key not in self.positions.keys():
            context.stra_log_text("平空仓，没有查找到对应的持仓记录：%s" % pos_key)
            return None
        pos: POSITION = self.positions[pos_key]
        res = context.stra_exit_short(code, pos.amount, "exitshort")
        context.stra_log_text(opt.msg)

        del self.positions[pos_key]
        return res

    def on_calculate(self, context: CtaContext):

        for code in [self.code]:
            # 根据实际交易品种，定义交易数量
            trdUnit = 1

            # 读取最新行情数据
            self.datas.klines(code, self.period)
            # 读取当前仓位
            curPos = context.stra_get_position(code)

            if curPos == 0:
                # 当前空仓，判断是否可以开仓
                open_opts = self.STR.open(code, self.datas)
                for opt in open_opts:
                    if opt.opt == "buy":
                        self.open_buy(context, code, trdUnit, opt)
                    elif opt.opt == "sell" and self.datas.market in {"currency", "futures"}:
                        self.open_sell(context, code, trdUnit, opt)
            elif curPos > 0:
                # 查找当前运行代码的持仓记录
                poss = self.get_poss(code)
                for pos in poss:
                    opt = self.STR.close(code, pos.mmd, pos, self.datas)
                    if opt is not False:
                        self.close_buy(context, code, opt)
            elif curPos < 0:
                # 查找当前运行代码的持仓记录
                poss = self.get_poss(code)
                for pos in poss:
                    opt = self.STR.close(code, pos.mmd, pos, self.datas)
                    if opt is not False:
                        self.close_sell(context, code, opt)
        return

    def on_tick(self, context: CtaContext, stdCode: str, newTick: dict):
        # context.stra_log_text ("on tick fired")
        return
