import copy
import datetime
import time
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd

try:
    import talib as ta
except ImportError:  # pragma: no cover - depends on local native package availability
    ta = None

from chanlun.cl_interface import (
    BC,
    BI,
    FX,
    ICL,
    LINE,
    MMD,
    TZXL,
    XD,
    XLFX,
    ZS,
    CLKline,
    Config,
    Kline,
    compare_ld_beichi,
    query_macd_ld,
    user_custom_mmd,
)

__author__ = "wangxu"

__all__ = [
    "pd",
    "np",
    "ta",
    "copy",
    "datetime",
    "time",
    "Union",
    "List",
    "Dict",
    "Tuple",
    "ICL",
    "Config",
    "BI",
    "Kline",
    "CLKline",
    "LINE",
    "XD",
    "FX",
    "ZS",
    "MMD",
    "BC",
    "TZXL",
    "XLFX",
    "compare_ld_beichi",
    "user_custom_mmd",
    "query_macd_ld",
    "CL",
]


DEFAULT_CONFIG = {
    "kline_qk": Config.KLINE_QK_NONE.value,
    "judge_zs_qs_level": "1",
    "kline_type": Config.KLINE_TYPE_DEFAULT.value,
    "fx_qy": Config.FX_QY_THREE.value,
    "fx_qj": Config.FX_QJ_K.value,
    "fx_bh": Config.FX_BH_YES.value,
    "bi_type": Config.BI_TYPE_OLD.value,
    "bi_bzh": Config.BI_BZH_YES.value,
    "bi_qj": Config.BI_QJ_DD.value,
    "bi_fx_cgd": Config.BI_FX_CHD_YES.value,
    "bi_split_k_cross_nums": "20,1",
    "fx_check_k_nums": 13,
    "allow_bi_fx_strict": "0",
    "xd_qj": Config.XD_QJ_DD.value,
    "zsd_qj": Config.ZSD_QJ_DD.value,
    "xd_zs_max_lines_split": 11,
    "xd_allow_bi_pohuai": Config.XD_BI_POHUAI_YES.value,
    "xd_allow_split_no_highlow": "1",
    "xd_allow_split_zs_kz": "0",
    "xd_allow_split_zs_more_line": "1",
    "xd_allow_split_zs_no_direction": "1",
    "zs_bi_type": [Config.ZS_TYPE_BZ.value],
    "zs_xd_type": [Config.ZS_TYPE_BZ.value],
    "zs_qj": Config.ZS_QJ_DD.value,
    "zs_cd": Config.ZS_CD_THREE.value,
    "zs_wzgx": Config.ZS_WZGX_GD.value,
    "zs_optimize": "0",
    "idx_macd_fast": 12,
    "idx_macd_slow": 26,
    "idx_macd_signal": 9,
    "cl_mmd_cal_qs_1mmd": "1",
    "cl_mmd_cal_not_qs_3mmd_1mmd": "1",
    "cl_mmd_cal_qs_3mmd_1mmd": "1",
    "cl_mmd_cal_qs_not_lh_2mmd": "1",
    "cl_mmd_cal_qs_bc_2mmd": "1",
    "cl_mmd_cal_3mmd_not_lh_bc_2mmd": "1",
    "cl_mmd_cal_1mmd_not_lh_2mmd": "1",
    "cl_mmd_cal_3mmd_xgxd_not_bc_2mmd": "1",
    "cl_mmd_cal_not_in_zs_3mmd": "1",
    "cl_mmd_cal_not_in_zs_gt_9_3mmd": "1",
}


class CL(ICL):
    """行情数据缠论分析。"""

    def __init__(
        self,
        code: str,
        frequency: str,
        config: Union[dict, None] = None,
        start_datetime: datetime.datetime = None,
    ):
        self.code = code
        self.frequency = frequency
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        if config:
            self.config.update(copy.deepcopy(config))
        self.start_datetime = start_datetime
        self.src_klines: List[Kline] = []
        self.klines: List[Kline] = self.src_klines
        self.cl_klines: List[CLKline] = []
        self.idx: dict = {}
        self.fxs: List[FX] = []
        self.bis: List[BI] = []
        self.xds: List[XD] = []
        self.zsds: List[XD] = []
        self.qsds: List[XD] = []
        self.bi_zss: Dict[str, List[ZS]] = {}
        self.xd_zss: Dict[str, List[ZS]] = {}
        self.zsd_zss: List[ZS] = []
        self.qsd_zss: List[ZS] = []
        self.debug = False
        self.use_time = {}

    def write_debug_log(self, msg):
        if self.debug:
            print(msg)

    def _add_time(self, key: str, use_time: float):
        if key not in self.use_time:
            self.use_time[key] = {"num": 1, "time": use_time}
            return None
        self.use_time[key]["num"] += 1
        self.use_time[key]["time"] += use_time
        return None

    def get_code(self) -> str:
        return self.code

    def get_frequency(self) -> str:
        return self.frequency

    def get_config(self) -> dict:
        return self.config

    def get_src_klines(self) -> List[Kline]:
        return self.src_klines

    def get_klines(self) -> List[Kline]:
        if self.config["kline_type"] == Config.KLINE_TYPE_CHANLUN.value:
            return [
                Kline(k.index, k.date, k.h, k.l, k.o, k.c, k.a)
                for k in self.cl_klines
            ]
        return self.src_klines

    def get_cl_klines(self) -> List[CLKline]:
        return self.cl_klines

    def get_idx(self) -> dict:
        return self.idx

    def get_fxs(self) -> List[FX]:
        return self.fxs

    def get_bis(self) -> List[BI]:
        return self.bis

    def get_xds(self) -> List[XD]:
        return self.xds

    def get_zsds(self) -> List[XD]:
        return self.zsds

    def get_qsds(self) -> List[XD]:
        return self.qsds

    def get_bi_zss(self, zs_type: str = None) -> List[ZS]:
        if zs_type is None:
            zs_type = self.default_bi_zs_type()
        return self.bi_zss.get(zs_type, [])

    def get_xd_zss(self, zs_type: str = None) -> List[ZS]:
        if zs_type is None:
            zs_type = self.default_xd_zs_type()
        return self.xd_zss.get(zs_type, [])

    def get_zsd_zss(self) -> List[ZS]:
        zss = list(sorted(self.zsd_zss, key=lambda zs: zs.start.k.date))
        for index, zs in enumerate(zss):
            zs.index = index
        return zss

    def get_qsd_zss(self) -> List[ZS]:
        zss = list(sorted(self.qsd_zss, key=lambda zs: zs.start.k.date))
        for index, zs in enumerate(zss):
            zs.index = index
        return zss

    def get_last_bi_zs(self) -> Union[ZS, None]:
        zss = self.get_bi_zss()
        return zss[-1] if zss else None

    def get_last_xd_zs(self) -> Union[ZS, None]:
        zss = self.get_xd_zss()
        return zss[-1] if zss else None

    def default_bi_zs_type(self):
        return self.config["zs_bi_type"][0]

    def default_xd_zs_type(self):
        return self.config["zs_xd_type"][0]

    def process_klines(self, klines: pd.DataFrame):
        if klines is None or len(klines) == 0:
            return self

        new_klines = self._df_to_klines(klines)
        by_date = {k.date: k for k in self.src_klines}
        for kline in new_klines:
            by_date[kline.date] = kline

        self.src_klines = list(sorted(by_date.values(), key=lambda k: k.date))
        if self.start_datetime is not None:
            self.src_klines = [k for k in self.src_klines if k.date >= self.start_datetime]
        for index, kline in enumerate(self.src_klines):
            kline.index = index
        self.klines = self.src_klines

        self.process_cl_kline()
        self.process_idx()
        self.process_fx()
        self.process_bi()
        self.process_up_line("bi")
        self.process_up_line("xd")
        self.process_up_line("zsd")
        self.process_zs(["bi", "xd", "zsd", "qsd"])
        self.process_mmd(["bi", "xd", "zsd", "qsd"])
        return self

    def process_idx(self):
        close = np.array([k.c for k in self.src_klines], dtype=float)
        if len(close) == 0:
            self.idx = {"macd": {"dif": [], "dea": [], "hist": []}}
            return self.idx

        fast = int(self.config["idx_macd_fast"])
        slow = int(self.config["idx_macd_slow"])
        signal = int(self.config["idx_macd_signal"])
        if ta is not None:
            dif, dea, hist = ta.MACD(
                close,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal,
            )
            hist = hist * 2
        else:
            close_series = pd.Series(close)
            dif = close_series.ewm(span=fast, adjust=False).mean() - close_series.ewm(
                span=slow, adjust=False
            ).mean()
            dea = dif.ewm(span=signal, adjust=False).mean()
            hist = (dif - dea) * 2
            dif = dif.to_numpy()
            dea = dea.to_numpy()
            hist = hist.to_numpy()

        self.idx = {
            "macd": {
                "dif": np.nan_to_num(dif).tolist(),
                "dea": np.nan_to_num(dea).tolist(),
                "hist": np.nan_to_num(hist).tolist(),
            }
        }
        return self.idx

    def process_cl_kline(self):
        self.cl_klines = []
        self._klines_baohan(self.src_klines, self.cl_klines)
        for index, ck in enumerate(self.cl_klines):
            ck.index = index
        return self.cl_klines

    def _new_cl_kline(self, kline: Kline, index: int) -> CLKline:
        if kline.c > kline.o:
            open_price = kline.l
            close_price = kline.h
        else:
            open_price = kline.h
            close_price = kline.l
        return CLKline(
            kline.index,
            kline.date,
            kline.h,
            kline.l,
            open_price,
            close_price,
            kline.a,
            [kline],
            index,
            1,
            False,
        )

    def _klines_baohan(self, klines: List[Kline], up_cl_klines: List[CLKline]):
        for kline in klines:
            new_ck = self._new_cl_kline(kline, len(up_cl_klines))
            if not up_cl_klines:
                up_cl_klines.append(new_ck)
                continue

            last_ck = up_cl_klines[-1]
            if not self._kline_contains(last_ck, new_ck):
                up_cl_klines.append(new_ck)
                continue

            direction = self._merge_direction(up_cl_klines, new_ck)
            if direction == "down":
                last_ck.h = min(last_ck.h, new_ck.h)
                last_ck.l = min(last_ck.l, new_ck.l)
            else:
                last_ck.h = max(last_ck.h, new_ck.h)
                last_ck.l = max(last_ck.l, new_ck.l)
            last_ck.c = new_ck.c
            last_ck.a += new_ck.a
            last_ck.date = new_ck.date
            last_ck.klines.extend(new_ck.klines)
            last_ck.k_index = last_ck.klines[-1].index
            last_ck.n = len(last_ck.klines)
            last_ck.up_qs = direction
        return up_cl_klines

    @staticmethod
    def _kline_contains(one: CLKline, two: CLKline) -> bool:
        return (one.h >= two.h and one.l <= two.l) or (two.h >= one.h and two.l <= one.l)

    @staticmethod
    def _merge_direction(up_cl_klines: List[CLKline], new_ck: CLKline) -> str:
        if len(up_cl_klines) < 2:
            last_ck = up_cl_klines[-1]
            return "up" if new_ck.h >= last_ck.h else "down"
        pre_ck = up_cl_klines[-2]
        last_ck = up_cl_klines[-1]
        if last_ck.h > pre_ck.h and last_ck.l > pre_ck.l:
            return "up"
        if last_ck.h < pre_ck.h and last_ck.l < pre_ck.l:
            return "down"
        return last_ck.up_qs or "up"

    def process_fx(self):
        if len(self.cl_klines) < 3:
            self.fxs = []
            return False
        self.fxs = []
        for index in range(1, len(self.cl_klines) - 1):
            fx = self._create_fx(self.cl_klines[index - 1 : index + 2])
            if fx is None:
                continue
            fx.index = len(self.fxs)
            self.fxs.append(fx)
        return self.fxs

    def _create_fx(self, klines: List[CLKline]) -> Union[FX, None]:
        if len(klines) == 3:
            left, middle, right = klines
        elif len(klines) == 2:
            left, middle = klines
            right = None
        else:
            return None

        if right is None:
            return None
        if middle.h >= left.h and middle.h >= right.h and middle.l >= left.l and middle.l >= right.l:
            return FX("ding", middle, [left, middle, right], middle.h, 0, True)
        if middle.l <= left.l and middle.l <= right.l and middle.h <= left.h and middle.h <= right.h:
            return FX("di", middle, [left, middle, right], middle.l, 0, True)
        return None

    def process_bi(self):
        if len(self.fxs) < 2:
            self.bis = []
            return False
        self.bis = []
        last_fx = None
        for fx in self.fxs:
            if last_fx is None:
                last_fx = fx
                continue
            if fx.type == last_fx.type:
                if (fx.type == "ding" and fx.val >= last_fx.val) or (
                    fx.type == "di" and fx.val <= last_fx.val
                ):
                    last_fx = fx
                continue
            if not self._bi_check_bi_fx_ok(last_fx, fx):
                continue
            bi_type = "up" if last_fx.type == "di" and fx.type == "ding" else "down"
            bi = BI(last_fx, fx, bi_type, len(self.bis), self.default_bi_zs_type())
            self._process_line_hl(bi, "bi")
            split_bis = self._bi_special_bi_split(bi)
            if split_bis:
                for split_bi in split_bis:
                    split_bi.index = len(self.bis)
                    self._process_line_hl(split_bi, "bi")
                    self.bis.append(split_bi)
            else:
                self.bis.append(bi)
            last_fx = fx
        return self.bis

    def _bi_check_bi_fx_ok(self, start_fx: FX, end_fx: FX) -> bool:
        if start_fx.type == end_fx.type:
            return False

        fx_qj = self.config["fx_qj"]
        fx_qy = self.config["fx_qy"]
        fx_check_k_nums = int(self.config["fx_check_k_nums"])
        k_distance = end_fx.k.k_index - start_fx.k.k_index

        if self.config["bi_type"] in (
            Config.BI_TYPE_OLD.value,
            Config.BI_TYPE_NEW.value,
        ) and k_distance < fx_check_k_nums:
            if (
                start_fx.k.h > end_fx.k.h
                or start_fx.k.l < end_fx.k.l
                or start_fx.k.h < end_fx.k.h
            ) and start_fx.k.l > end_fx.k.l:
                return False

        if start_fx.type == "ding" and start_fx.k.h < end_fx.k.l:
            return False
        if start_fx.type == "di" and start_fx.k.l > end_fx.k.h:
            return False

        if self._config_is_enabled(self.config["allow_bi_fx_strict"]) and k_distance < fx_check_k_nums:
            if not start_fx.type == "ding" or start_fx.low(fx_qj, fx_qy) < end_fx.low(fx_qj, fx_qy):
                if not start_fx.type == "di" or start_fx.high(fx_qj, fx_qy) > end_fx.high(fx_qj, fx_qy):
                    if (
                        end_fx.type == "ding"
                        or end_fx.low(fx_qj, fx_qy) < start_fx.low(fx_qj, fx_qy)
                        or end_fx.type == "di"
                    ) and end_fx.high(fx_qj, fx_qy) > start_fx.high(fx_qj, fx_qy):
                        return False

                    if self.config["bi_fx_cgd"] == Config.BI_FX_CHD_NO.value:
                        between_fxs = self.fxs[start_fx.index : end_fx.index + 1]
                        max_fx_val = max(_fx.val for _fx in between_fxs)
                        min_fx_val = min(_fx.val for _fx in between_fxs)
                        if k_distance < fx_check_k_nums and end_fx.type == "ding" and end_fx.val < max_fx_val:
                            return False
                        if k_distance < fx_check_k_nums and end_fx.type == "di" and end_fx.val > min_fx_val:
                            return False

        if (
            end_fx.type == "ding"
            and self.config["fx_bh"] in (Config.FX_BH_DINGDI.value,)
            and k_distance < fx_check_k_nums
            and end_fx.high(fx_qj, fx_qy) <= start_fx.high(fx_qj, fx_qy)
            and end_fx.low(fx_qj, fx_qy) >= start_fx.low(fx_qj, fx_qy)
        ):
            return False
        if (
            end_fx.type == "di"
            and self.config["fx_bh"] in (Config.FX_BH_DIDING.value,)
            and k_distance < fx_check_k_nums
            and end_fx.high(fx_qj, fx_qy) <= start_fx.high(fx_qj, fx_qy)
            and end_fx.low(fx_qj, fx_qy) >= start_fx.low(fx_qj, fx_qy)
        ):
            return False
        if (
            self.config["fx_bh"] in (Config.FX_BH_NO_QBH.value,)
            and k_distance < fx_check_k_nums
            and start_fx.high(fx_qj, fx_qy) >= end_fx.high(fx_qj, fx_qy)
            and start_fx.low(fx_qj, fx_qy) <= end_fx.low(fx_qj, fx_qy)
        ):
            return False
        if (
            self.config["fx_bh"] in (Config.FX_BH_NO_HBQ.value,)
            and k_distance < fx_check_k_nums
            and end_fx.high(fx_qj, fx_qy) >= start_fx.high(fx_qj, fx_qy)
            and end_fx.low(fx_qj, fx_qy) <= start_fx.low(fx_qj, fx_qy)
        ):
            return False
        if self.config["fx_bh"] in (Config.FX_BH_NO.value,) and k_distance < fx_check_k_nums:
            if (
                end_fx.high(fx_qj, fx_qy) >= start_fx.high(fx_qj, fx_qy)
                or end_fx.low(fx_qj, fx_qy) <= start_fx.low(fx_qj, fx_qy)
                or end_fx.high(fx_qj, fx_qy) <= start_fx.high(fx_qj, fx_qy)
            ) and end_fx.low(fx_qj, fx_qy) >= start_fx.low(fx_qj, fx_qy):
                return False
        return True

    def _bi_special_bi_split(self, bi: BI):
        split_config = str(self.config["bi_split_k_cross_nums"])
        if "," not in split_config:
            return False

        try:
            split_k_num, split_min_fx_num = [int(item) for item in split_config.split(",", 1)]
        except ValueError:
            return False

        split_k_num = max(13, split_k_num)
        if split_min_fx_num < 0 or split_min_fx_num > 5:
            split_min_fx_num = 1
        if split_k_num >= 99:
            return False

        fxs = self.fxs[bi.start.index + 1 : bi.end.index]
        if len(fxs) < 3:
            return False

        candidates = []
        for left_fx in fxs:
            if left_fx.type == bi.start.type:
                continue
            for right_fx in fxs:
                if right_fx.index <= left_fx.index:
                    continue
                if right_fx.type == left_fx.type or right_fx.type != bi.start.type:
                    continue
                left_fx_num = left_fx.index - bi.start.index
                middle_fx_num = right_fx.index - left_fx.index
                right_fx_num = bi.end.index - right_fx.index
                if min(left_fx_num, middle_fx_num, right_fx_num) < split_min_fx_num:
                    continue
                left_k_num = left_fx.k.k_index - bi.start.k.k_index
                middle_k_num = right_fx.k.k_index - left_fx.k.k_index
                right_k_num = bi.end.k.k_index - right_fx.k.k_index
                if min(left_k_num, middle_k_num, right_k_num) < split_k_num:
                    continue
                if not self._bi_check_bi_fx_ok(bi.start, left_fx):
                    continue
                if not self._bi_check_bi_fx_ok(left_fx, right_fx):
                    continue
                if not self._bi_check_bi_fx_ok(right_fx, bi.end):
                    continue
                candidates.append((left_fx, right_fx))

        if len(candidates) == 0:
            return False

        left_fx, right_fx = max(
            candidates,
            key=lambda item: min(
                item[0].k.k_index - bi.start.k.k_index,
                item[1].k.k_index - item[0].k.k_index,
                bi.end.k.k_index - item[1].k.k_index,
            ),
        )
        split_bis = [
            BI(bi.start, left_fx, "up" if bi.start.type == "di" else "down", bi.index, bi.default_zs_type),
            BI(left_fx, right_fx, "up" if left_fx.type == "di" else "down", bi.index + 1, bi.default_zs_type),
            BI(right_fx, bi.end, "up" if right_fx.type == "di" else "down", bi.index + 2, bi.default_zs_type),
        ]
        for split_bi in split_bis:
            split_bi.is_split = "特殊笔拆分"
            self._process_line_hl(split_bi, "bi")
        return split_bis


    def _process_line_hl(self, line: LINE, line_type: str) -> bool:
        if line_type == "bi":
            high, low = self._line_qj(line, self.config["bi_qj"])
        elif line_type == "xd":
            high, low = self._line_qj(line, self.config["xd_qj"])
        elif line_type in ("zsd", "qsd"):
            high, low = self._line_qj(line, self.config["zsd_qj"])
        else:
            raise Exception(f"计算线段高低点，线的对象类型错误 {line_type}")

        line.high = high
        line.low = low
        if isinstance(line, XD):
            line.start = line.start_line.start
            line.end = line.end_line.end
        line.zs_high, line.zs_low = self._line_zs_hl(line)
        return True

    def _line_qj(self, line: LINE, qj_type: str) -> List[float]:
        if qj_type in (
            Config.BI_QJ_DD.value,
            Config.XD_QJ_DD.value,
            Config.ZSD_QJ_DD.value,
        ):
            return [line.ding_high(), line.di_low()]
        if qj_type in (
            Config.BI_QJ_CK.value,
            Config.XD_QJ_CK.value,
            Config.ZSD_QJ_CK.value,
        ):
            return self._fx_qj_high_low(line.start, line.end, "ck")
        if qj_type in (
            Config.BI_QJ_K.value,
            Config.XD_QJ_K.value,
            Config.ZSD_QJ_K.value,
        ):
            return self._fx_qj_high_low(line.start, line.end, "k")
        raise Exception(f"获取线段的区间，指定的类型错误 {qj_type}")

    def _line_zs_hl(self, line: LINE) -> List[float]:
        if self.config["zs_qj"] == Config.ZS_QJ_DD.value:
            return [line.ding_high(), line.di_low()]
        if self.config["zs_qj"] == Config.ZS_QJ_CK.value:
            return self._fx_qj_high_low(line.start, line.end, "ck")
        if self.config["zs_qj"] == Config.ZS_QJ_K.value:
            return self._fx_qj_high_low(line.start, line.end, "k")
        raise Exception(f"计算线的高低点类型错误：{self.config['zs_qj']}")

    def _fx_qj_high_low(self, start: FX, end: FX, qj_type: str) -> List[float]:
        start_k_index = min(start.k.klines[0].index, end.k.klines[-1].index)
        end_k_index = max(start.k.klines[0].index, end.k.klines[-1].index)
        start_ck_index = min(start.k.index, end.k.index)
        end_ck_index = max(start.k.index, end.k.index)
        if qj_type == "k":
            klines = self.src_klines[start_k_index : end_k_index + 1]
        elif qj_type == "ck":
            klines = self.cl_klines[start_ck_index : end_ck_index + 1]
        else:
            raise Exception(f"获取分型区间高低点类型错误 {qj_type}")
        return [max(k.h for k in klines), min(k.l for k in klines)]

    def _line_get_zs_hl(self, line: LINE) -> List[float]:
        return [line.zs_high, line.zs_low]

    def _qk_num(self, klines: List[Kline]) -> Tuple[int, int]:
        up_gaps = []
        down_gaps = []
        for index in range(1, len(klines)):
            pre_kline = klines[index - 1]
            now_kline = klines[index]
            up_gaps = [gap_low for gap_low in up_gaps if now_kline.l > gap_low]
            down_gaps = [gap_high for gap_high in down_gaps if now_kline.h < gap_high]
            if now_kline.l > pre_kline.h:
                up_gaps.append(pre_kline.h)
            elif now_kline.h < pre_kline.l:
                down_gaps.append(pre_kline.l)
        return len(up_gaps), len(down_gaps)

    def _get_fx_qj_exists_qk(self, start_fx: FX, end_fx: FX) -> bool:
        if end_fx.index <= start_fx.index:
            return False
        klines = self.src_klines[start_fx.k.k_index : end_fx.k.k_index + 1]
        up_qk_num, down_qk_num = self._qk_num(klines)
        if start_fx.type == "di" and end_fx.type == "ding":
            return up_qk_num > 0
        if start_fx.type == "ding" and end_fx.type == "di":
            return down_qk_num > 0
        return up_qk_num + down_qk_num > 0

    @staticmethod
    def _copy_zs(copy_zs: ZS, to_zs: ZS):
        to_zs.zs_type = copy_zs.zs_type
        to_zs.start = copy_zs.start
        to_zs.lines = copy_zs.lines
        to_zs.end = copy_zs.end
        to_zs.zg = copy_zs.zg
        to_zs.zd = copy_zs.zd
        to_zs.gg = copy_zs.gg
        to_zs.dd = copy_zs.dd
        to_zs.type = copy_zs.type
        to_zs.line_num = copy_zs.line_num
        to_zs.level = copy_zs.level
        to_zs.done = copy_zs.done
        to_zs.real = copy_zs.real
        return to_zs

    @staticmethod
    def __up_cross(one_list, two_list):
        assert len(one_list) == len(two_list), "信号输入维度不相等"
        if len(one_list) < 2:
            return []
        return [
            index
            for index in range(1, len(two_list))
            if one_list[index - 1] < two_list[index - 1] and one_list[index] > two_list[index]
        ]

    @staticmethod
    def __down_cross(one_list, two_list):
        assert len(one_list) == len(two_list), "信号输入维度不相等"
        if len(one_list) < 2:
            return []
        return [
            index
            for index in range(1, len(two_list))
            if one_list[index - 1] > two_list[index - 1] and one_list[index] < two_list[index]
        ]

    @staticmethod
    def _cross_qujian(qj_one: List[float], qj_two: List[float]) -> Union[dict, None]:
        high = min(max(qj_two[0], qj_two[1]), max(qj_one[0], qj_one[1]))
        low = max(min(qj_two[0], qj_two[1]), min(qj_one[0], qj_one[1]))
        if high >= low:
            return {"max": high, "min": low}
        return None

    @staticmethod
    def _config_is_enabled(value) -> bool:
        return value is True or str(value) == "1" or str(value).lower() == "true"

    def process_up_line(self, base_line_type: str):
        if base_line_type == "bi":
            self.xds = []
            up_lines = self.xds
            up_line_type = "xd"
            base_lines = self.bis
            default_zs_type = self.default_xd_zs_type()
        elif base_line_type == "xd":
            self.zsds = []
            up_lines = self.zsds
            up_line_type = "zsd"
            base_lines = self.xds
            default_zs_type = Config.ZS_TYPE_BZ.value
        elif base_line_type == "zsd":
            self.qsds = []
            up_lines = self.qsds
            up_line_type = "qsd"
            base_lines = self.zsds
            default_zs_type = Config.ZS_TYPE_BZ.value
        else:
            raise Exception(f"处理高级别线段类型错误：{base_line_type}")

        if len(base_lines) < 3:
            return False

        tzxl_info = self._xd_get_up_line_tzxl_info(base_lines, [], cal_type=["di", "ding"])
        xlfxs = sorted(
            tzxl_info["di"]["fxs"] + tzxl_info["ding"]["fxs"],
            key=lambda fx: fx.xl.pre_line.index,
        )
        last_fx = None
        for xlfx in xlfxs:
            if last_fx is None:
                last_fx = xlfx
                continue
            if xlfx.type == last_fx.type:
                if (xlfx.type == "ding" and xlfx.high >= last_fx.high) or (
                    xlfx.type == "di" and xlfx.low <= last_fx.low
                ):
                    last_fx = xlfx
                continue
            up_line = self._create_up_line_from_xlfx(
                last_fx,
                xlfx,
                len(up_lines),
                default_zs_type,
            )
            if up_line is None:
                continue
            tzxls = xlfx.xls if xlfx.type == up_line.type else last_fx.xls
            self._xd_add_up_line(
                base_line_type,
                base_lines,
                up_lines,
                default_zs_type,
                up_line_type,
                up_line,
                xlfx,
                tzxls,
                "",
                False,
                False,
            )
            last_fx = xlfx
        return len(up_lines) > 0

    def _xd_get_up_line_tzxl_info(self, base_lines, up_lines, cal_type):
        if len(up_lines) == 0:
            next_base_lines = base_lines
            line_base_lines = base_lines
        else:
            up_line = up_lines[-1]
            next_base_lines = self._xd_get_up_line_next_line(base_lines, up_line)
            line_base_lines = self._xd_get_up_line_next_line(base_lines, up_line, is_next_line=False)

        di_xls, di_fxs = self._xd_cal_line_xlfx(
            next_base_lines,
            fx_type="di",
            bh_type="no_bh",
            no_done_fx=True,
            three_fx=True,
        ) if "di" in cal_type else ([], [])
        bh_di_xls, bh_di_fxs = self._xd_cal_line_xlfx(
            next_base_lines,
            fx_type="di",
            bh_type="bh",
        ) if "bh_di" in cal_type else ([], [])
        ding_xls, ding_fxs = self._xd_cal_line_xlfx(
            next_base_lines,
            fx_type="ding",
            bh_type="no_bh",
            no_done_fx=True,
            three_fx=True,
        ) if "ding" in cal_type else ([], [])
        bh_ding_xls, bh_ding_fxs = self._xd_cal_line_xlfx(
            next_base_lines,
            fx_type="ding",
            bh_type="bh",
        ) if "bh_ding" in cal_type else ([], [])
        line_di_xls, line_di_fxs = self._xd_cal_line_xlfx(
            line_base_lines,
            fx_type="di",
            bh_type="no_bh",
            no_done_fx=True,
            three_fx=True,
        ) if "line_di" in cal_type else ([], [])
        bh_line_di_xls, bh_line_di_fxs = self._xd_cal_line_xlfx(
            line_base_lines,
            fx_type="di",
            bh_type="bh",
        ) if "bh_line_di" in cal_type else ([], [])
        line_ding_xls, line_ding_fxs = self._xd_cal_line_xlfx(
            line_base_lines,
            fx_type="ding",
            bh_type="no_bh",
            no_done_fx=True,
            three_fx=True,
        ) if "line_ding" in cal_type else ([], [])
        bh_line_ding_xls, bh_line_ding_fxs = self._xd_cal_line_xlfx(
            line_base_lines,
            fx_type="ding",
            bh_type="bh",
        ) if "bh_line_ding" in cal_type else ([], [])

        return {
            "bh_line_ding": {"xls": bh_line_ding_xls, "fxs": bh_line_ding_fxs},
            "line_ding": {"xls": line_ding_xls, "fxs": line_ding_fxs},
            "bh_line_di": {"xls": bh_line_di_xls, "fxs": bh_line_di_fxs},
            "line_di": {"xls": line_di_xls, "fxs": line_di_fxs},
            "bh_ding": {"xls": bh_ding_xls, "fxs": bh_ding_fxs},
            "ding": {"xls": ding_xls, "fxs": ding_fxs},
            "bh_di": {"xls": bh_di_xls, "fxs": bh_di_fxs},
            "di": {"xls": di_xls, "fxs": di_fxs},
            "line_base_lines": line_base_lines,
            "next_base_lines": next_base_lines,
        }

    def _create_up_line_from_xlfx(
        self,
        one_fx: XLFX,
        two_fx: XLFX,
        index: int,
        default_zs_type: str,
    ) -> Union[XD, None]:
        ding_fx = one_fx if one_fx.type == "ding" else two_fx
        di_fx = one_fx if one_fx.type == "di" else two_fx
        if ding_fx.high < di_fx.low:
            return None
        if abs(ding_fx.xl.pre_line.index - di_fx.xl.pre_line.index) < 2:
            return None

        if ding_fx.xl.pre_line.index > di_fx.xl.pre_line.index:
            up_line = XD(
                start=di_fx.xl.line.start,
                end=ding_fx.xl.pre_line.end,
                start_line=di_fx.xl.line,
                end_line=ding_fx.xl.pre_line,
                _type="up",
                ding_fx=ding_fx,
                di_fx=di_fx,
                index=index,
                default_zs_type=default_zs_type,
            )
            up_line.done = bool(ding_fx.done)
        else:
            up_line = XD(
                start=ding_fx.xl.line.start,
                end=di_fx.xl.pre_line.end,
                start_line=ding_fx.xl.line,
                end_line=di_fx.xl.pre_line,
                _type="down",
                ding_fx=ding_fx,
                di_fx=di_fx,
                index=index,
                default_zs_type=default_zs_type,
            )
            up_line.done = bool(di_fx.done)

        if up_line.end_line.index <= up_line.start_line.index:
            return None
        up_line.tzxls = ding_fx.xls if up_line.type == "up" else di_fx.xls
        return up_line

    def _xd_add_up_line(
        self,
        base_line_type,
        base_lines,
        up_lines,
        default_zs_type,
        up_line_type,
        up_line,
        tzxlfx,
        tzxls,
        is_split,
        not_del,
        not_yx,
    ):
        if up_line is None:
            return False

        up_line.index = len(up_lines)
        up_line.default_zs_type = default_zs_type
        up_line.tzxls = tzxls
        up_line.is_split = is_split
        up_line.not_del = not_del
        up_line.not_yx = not_yx
        up_line.done = bool(tzxlfx.done and tzxlfx.qk is False)
        self._process_line_hl(up_line, up_line_type)

        if up_line.start_line.type != up_line.end_line.type:
            raise Exception(f"线段起始与结束方向不一致: {up_line}")
        if len(up_lines) > 0 and up_line.start_line.index <= up_lines[-1].start_line.index:
            return False

        if len(up_lines) > 0 and up_lines[-1].type == up_line.type:
            pre_line = up_lines[-1]
            if up_line.type == "up" and up_line.high >= pre_line.high:
                up_lines[-1] = up_line
            elif up_line.type == "down" and up_line.low <= pre_line.low:
                up_lines[-1] = up_line
            else:
                return False
        else:
            up_lines.append(up_line)

        self._xd_done_pre_xd(up_lines[:-1])
        self._xd_check_and_split_up_line(base_line_type, base_lines, up_lines, default_zs_type, up_line_type, up_line)
        return up_line

    def _xd_update_tzfx(
        self,
        base_line_type,
        base_lines,
        up_lines,
        up_line_type,
        default_zs_type,
        up_line,
        tzxls,
        tzxlfx,
        is_split,
    ):
        start_line = up_line.start_line
        end_line = tzxlfx.xl.pre_line
        if tzxlfx.done is False:
            next_lines = self._xd_get_up_line_next_line(base_lines, up_line)
            if len(next_lines) > 0:
                end_line = next_lines[0]

        if end_line.index < start_line.index:
            raise Exception("线段结束位置不能小于线段起始位置")
        if up_line.type == "up" and end_line.high < start_line.low:
            raise Exception("线段结束价格不能小于线段起始价格")
        if up_line.type == "down" and end_line.low > start_line.high:
            raise Exception("线段结束价格不能大于线段起始价格")

        up_line.end_line = end_line
        up_line.end = end_line.end
        up_line.tzxls = tzxls
        up_line.done = bool(tzxlfx.done and tzxlfx.qk is False)
        up_line.is_split = is_split
        self._process_line_hl(up_line, up_line_type)
        if up_line.start_line.type != up_line.end_line.type:
            raise Exception(f"线段起始与结束方向不一致: {up_line}")
        self._xd_check_and_split_up_line(base_line_type, base_lines, up_lines, default_zs_type, up_line_type, up_line)
        return up_line

    def _xd_split_enabled(self, reason: str) -> bool:
        if reason == "段内中枢线段数量超过9":
            return self._config_is_enabled(self.config.get("xd_allow_split_zs_more_line", "0"))
        if reason == "段内存在两个相反方向中枢":
            return self._config_is_enabled(self.config.get("xd_allow_split_zs_no_direction", "0"))
        if reason == "段内存在重叠中枢":
            return self._config_is_enabled(self.config.get("xd_allow_split_zs_kz", "0"))
        if reason == "":
            return self._config_is_enabled(self.config.get("xd_allow_split_no_highlow", "0"))
        return False

    def _xd_check_and_split_up_line(self, base_line_type, base_lines, up_lines, default_zs_type, up_line_type, up_line):
        if len(up_lines) <= 1:
            return False
        start_index = up_line.start_line.index
        end_index = up_line.end_line.index
        if end_index < start_index:
            return False
        is_ok, line_ups, line_downs, reason = self._xd_check_xd_is_ok(
            base_lines,
            up_line,
            base_lines[start_index : end_index + 1],
        )
        if is_ok:
            return False
        split_hl, split_ll = self._xd_split_optimal_hl_ll(base_lines, up_line, line_ups, line_downs)
        if not self._xd_split_enabled(reason):
            up_line.is_split = reason or "线段待拆分"
            return False
        if split_hl is None or split_ll is None:
            up_line.is_split = reason or "线段待拆分"
            return False
        up_line.is_split = reason or "线段拆分"
        return split_hl, split_ll

    def _xd_get_next_tzfx(self, dings, dis, find_type):
        fxs = sorted(dings + dis, key=lambda fx: fx.xl.pre_line.index)
        if find_type in ("ding", "di"):
            for fx in fxs:
                if fx.type == find_type:
                    return fx
            return None
        if find_type in ("up", "down"):
            first_type = "ding" if find_type == "up" else "di"
            for fx in fxs:
                if fx.type == first_type:
                    return fx
            return None
        return fxs[0] if len(fxs) > 0 else None

    def _xd_line_to_tzxl(self, base_lines, bh_direction, line):
        try:
            line_pos = base_lines.index(line)
        except ValueError:
            line_pos = -1
        if line_pos <= 0:
            return None
        return TZXL(bh_direction, line, base_lines[line_pos - 1], False, True)

    def _xd_get_up_line_next_line(self, base_lines, up_line, is_next_line=True):
        if up_line.type == "up":
            if is_next_line:
                next_lines = base_lines[up_line.ding_fx.xl.pre_line.index + 1 :]
                if len(next_lines) == 0:
                    return []
                if next_lines[0].type == "up":
                    next_lines = next_lines[1:]
                else:
                    next_lines = base_lines[up_line.di_fx.xl.pre_line.index + 1 :]
            else:
                next_lines = base_lines[up_line.di_fx.xl.pre_line.index + 1 :]
        else:
            if is_next_line:
                next_lines = base_lines[up_line.di_fx.xl.pre_line.index + 1 :]
                if len(next_lines) == 0:
                    return []
                if next_lines[0].type == "down":
                    next_lines = next_lines[1:]
                else:
                    next_lines = base_lines[up_line.ding_fx.xl.pre_line.index + 1 :]
            else:
                next_lines = base_lines[up_line.ding_fx.xl.pre_line.index + 1 :]
        if len(next_lines) == 0:
            return []
        return next_lines

    def _xd_cal_line_xlfx(
        self,
        lines,
        fx_type,
        bh_type="no_bh",
        no_done_fx=False,
        three_fx=False,
    ):
        if len(lines) == 0:
            return [], []

        bh_direction = "up" if fx_type == "ding" else "down"
        line_type = "down" if fx_type == "ding" else "up"
        tzxls = []
        for line in lines:
            if line.type != line_type:
                continue
            tzxl = self._xd_line_to_tzxl(lines, bh_direction, line)
            if tzxl is None:
                continue
            if bh_type == "bh" and len(tzxls) > 0:
                pre_tzxl = tzxls[-1]
                has_include = (tzxl.max >= pre_tzxl.max and tzxl.min <= pre_tzxl.min) or (
                    tzxl.max <= pre_tzxl.max and tzxl.min >= pre_tzxl.min
                )
                if has_include:
                    pre_tzxl.lines += tzxl.lines
                    pre_tzxl.line_bad = True
                    pre_tzxl.done = tzxl.done
                    pre_tzxl.update_maxmin()
                    continue
            tzxls.append(tzxl)
        if len(tzxls) < 3:
            return tzxls, []

        xlfxs = []
        for index in range(1, len(tzxls) - 1):
            left = tzxls[index - 1]
            middle = tzxls[index]
            right = tzxls[index + 1]
            if fx_type == "ding":
                is_fx = middle.max >= left.max and middle.max >= right.max and middle.min >= left.min and middle.min >= right.min
            else:
                is_fx = middle.min <= left.min and middle.min <= right.min and middle.max <= left.max and middle.max <= right.max
            if not is_fx:
                continue
            xlfx = XLFX(fx_type, middle, [left, middle, right], done=right.done)
            xlfx.qk = self._get_fx_qj_exists_qk(left.pre_line.end, right.pre_line.end)
            xlfx.is_line_bad = middle.line_bad
            xlfx.bh_type = bh_type
            xlfxs.append(xlfx)

        if no_done_fx and len(tzxls) >= 2:
            left = tzxls[-2]
            middle = tzxls[-1]
            if fx_type == "ding":
                is_fx = middle.max >= left.max and middle.min >= left.min
            else:
                is_fx = middle.min <= left.min and middle.max <= left.max
            if is_fx and (len(xlfxs) == 0 or xlfxs[-1].xl is not middle):
                xlfx = XLFX(fx_type, middle, [left, middle], done=False)
                xlfx.qk = self._get_fx_qj_exists_qk(left.pre_line.end, middle.pre_line.end)
                xlfx.is_line_bad = middle.line_bad
                xlfx.bh_type = bh_type
                xlfxs.append(xlfx)
        return tzxls, xlfxs

    def _xd_check_xd_is_ok(self, base_lines, up_line, lines):
        if len(lines) in (1, 3, 5):
            return True, [], [], ""
        if len(lines) % 2 == 0:
            return False, [], [], ""

        line_ups = [line for line in lines if line.type == "up"]
        line_downs = [line for line in lines if line.type == "down"]
        zss = self.create_dn_zs("bi", lines)
        if len(zss) == 0:
            return True, [], [], ""

        if any(zs.line_num > 9 for zs in zss):
            return False, line_ups, line_downs, "段内中枢线段数量超过9"

        for pre_zs, now_zs in zip(zss, zss[1:]):
            if pre_zs.type != now_zs.type:
                return False, line_ups, line_downs, "段内存在两个相反方向中枢"
            if self._cross_qujian([pre_zs.zg, pre_zs.zd], [now_zs.zg, now_zs.zd]) is not None:
                return False, line_ups, line_downs, "段内存在重叠中枢"
        return True, [], [], ""

    def _xd_split_optimal_hl_ll(self, base_lines, split_up_line, line_ups, line_downs):
        if len(line_downs) < 3 and len(line_ups) < 3:
            return None, None

        candidates = []
        if split_up_line.type == "up":
            for hl in line_ups:
                for ll in line_downs:
                    if ll.index - hl.index < 2:
                        continue
                    if hl.index - split_up_line.start_line.index < 2:
                        continue
                    if split_up_line.end_line.index - ll.index < 2:
                        continue
                    if ll.end.val < hl.end.val:
                        candidates.append({"hl": hl, "ll": ll, "diff_val": abs(hl.end.val - ll.end.val)})
        else:
            for ll in line_downs:
                for hl in line_ups:
                    if hl.index - ll.index < 2:
                        continue
                    if ll.index - split_up_line.start_line.index < 2:
                        continue
                    if split_up_line.end_line.index - hl.index < 2:
                        continue
                    if hl.end.val > ll.end.val:
                        candidates.append({"hl": hl, "ll": ll, "diff_val": abs(hl.end.val - ll.end.val)})

        if len(candidates) == 0:
            return None, None
        candidates = sorted(candidates, key=lambda item: item["diff_val"])
        return candidates[0]["hl"], candidates[0]["ll"]

    def _xd_done_pre_xd(self, up_lines):
        for up_line in up_lines:
            if up_line.done is False:
                up_line.done = True
        return True

    def _line_ukey(self, line):
        key = f"{line.index}_{line.start.k.date}_{line.end.k.date}_{line.start.val}_{line.end.val}_{line.start.index}_{line.end.index}_{line.start.done}_{line.end.done}_{line.is_done()}"
        if isinstance(line, XD):
            key += "__start_line__" + self._line_ukey(line.start_line)
            key += "__end_line__" + self._line_ukey(line.end_line)
            key += "__xl_ding__" + self._line_ukey(line.ding_fx.xl.pre_line)
            key += "__xl_di__" + self._line_ukey(line.di_fx.xl.pre_line)
        return key

    def process_zs(self, cal_line_types: List[str]):
        self.bi_zss = {zs_type: [] for zs_type in self.config["zs_bi_type"]}
        self.xd_zss = {zs_type: [] for zs_type in self.config["zs_xd_type"]}
        self.zsd_zss = []
        self.qsd_zss = []

        if "bi" in cal_line_types:
            for zs_type in self.config["zs_bi_type"]:
                self.bi_zss[zs_type] = self._create_zss_by_type(zs_type, "bi", self.bis)

        if "xd" in cal_line_types:
            for zs_type in self.config["zs_xd_type"]:
                self.xd_zss[zs_type] = self._create_zss_by_type(zs_type, "xd", self.xds)

        self.zsd_zss = self._create_bz_zss("zsd", self.zsds)
        self.qsd_zss = self._create_bz_zss("qsd", self.qsds)
        return self.bi_zss

    def _process_dn_zs(self, lines, up_lines, zss, cal_line_type):
        zss[:] = self.create_dn_zs(cal_line_type, lines, zs_include_last_line=False)
        return zss

    def _process_fl_zs(self, lines, up_lines, zss, cal_line_type):
        zss[:] = self._create_fl_zss(cal_line_type, lines)
        return zss

    def _process_bz_zs(self, lines, zss, cal_line_type):
        zss[:] = self._create_bz_zss(cal_line_type, lines)
        return zss

    def _process_fx_zs(self, lines, zss, cal_line_type):
        zss[:] = self._create_fx_zss(cal_line_type, lines)
        return zss

    def _create_zss_by_type(self, zs_type: str, line_type: str, lines: List[LINE]) -> List[ZS]:
        if zs_type == Config.ZS_TYPE_BZ.value:
            return self._create_bz_zss(line_type, lines)
        if zs_type == Config.ZS_TYPE_DN.value:
            return self.create_dn_zs(line_type, lines, zs_include_last_line=False)
        if zs_type == Config.ZS_TYPE_FX.value:
            return self._create_fx_zss(line_type, lines)
        if zs_type == Config.ZS_TYPE_FL.value:
            return self._create_fl_zss(line_type, lines)
        return []

    def _create_bz_zss(self, zs_type: str, lines: List[LINE]) -> List[ZS]:
        zss = []
        start_index = 0
        while start_index + 4 <= len(lines):
            zs = self.create_zs(zs_type, None, lines[start_index:])
            if zs is None:
                start_index += 1
                continue
            zs.index = len(zss)
            zss.append(zs)
            start_index = zs.lines[-1].index + 1 if zs.lines else start_index + 1
        return zss

    def create_zs(self, zs_type, zs, lines, max_line_num=999):
        if len(lines) <= 3:
            return None

        zs_lines = []
        interval = self._cross_qujian(
            self._line_get_zs_hl(lines[1]), self._line_get_zs_hl(lines[2])
        )
        if interval is None:
            return None

        zg = interval["max"]
        zd = interval["min"]
        gg = max(lines[1].zs_high, lines[2].zs_high)
        dd = min(lines[1].zs_low, lines[2].zs_low)
        zs_lines.extend([lines[1], lines[2]])

        done = False
        for line in lines[3 : max_line_num + 1]:
            line_interval = self._line_get_zs_hl(line)
            next_interval = self._cross_qujian([zg, zd], line_interval)
            if next_interval is None:
                done = True
                break
            zs_lines.append(line)
            if self.config["zs_cd"] == Config.ZS_CD_MORE.value:
                zg = next_interval["max"]
                zd = next_interval["min"]
            gg = max(gg, line.zs_high)
            dd = min(dd, line.zs_low)

        if len(zs_lines) < 3:
            return None

        zs_start = zs_lines[0].start
        zs_end = zs_lines[-1].end
        zs_direction = "up" if lines[0].type == "up" else "down"
        new_zs = ZS(
            zs_type,
            zs_start,
            zs_end,
            zg,
            zd,
            gg,
            dd,
            zs_direction,
            0,
            len(zs_lines),
            zs.level if zs is not None else 0,
        )
        new_zs.lines = zs_lines
        new_zs.done = done
        return new_zs

    def create_dn_zs(
        self,
        zs_type: str,
        lines: List[LINE],
        max_line_num: int = 999,
        zs_include_last_line=True,
    ) -> List[ZS]:
        zss = []
        if len(lines) < 4:
            return zss

        max_line_num = min(int(max_line_num), len(lines))
        start_pos = 0
        while start_pos + 4 <= len(lines):
            end_limit = min(len(lines), start_pos + max_line_num)
            interval = self._cross_qujian(
                self._line_get_zs_hl(lines[start_pos]),
                self._line_get_zs_hl(lines[start_pos + 1]),
            )
            if interval is None:
                start_pos += 1
                continue

            interval = self._cross_qujian(
                [interval["max"], interval["min"]],
                self._line_get_zs_hl(lines[start_pos + 2]),
            )
            if interval is None:
                start_pos += 1
                continue

            zs_lines = lines[start_pos : start_pos + 3]
            zg = interval["max"]
            zd = interval["min"]
            gg = max(line.zs_high for line in zs_lines)
            dd = min(line.zs_low for line in zs_lines)
            done = False

            for line in lines[start_pos + 3 : end_limit]:
                line_interval = self._line_get_zs_hl(line)
                next_interval = self._cross_qujian([zg, zd], line_interval)
                if next_interval is None:
                    done = True
                    break
                if zs_include_last_line or line is not lines[-1]:
                    zs_lines.append(line)
                    gg = max(gg, line.zs_high)
                    dd = min(dd, line.zs_low)
                if self.config["zs_cd"] == Config.ZS_CD_MORE.value:
                    zg = next_interval["max"]
                    zd = next_interval["min"]

            new_zs = ZS(
                zs_type,
                zs_lines[0].start,
                zs_lines[-1].end,
                zg,
                zd,
                gg,
                dd,
                zs_lines[0].type,
                len(zss),
                len(zs_lines),
            )
            new_zs.lines = zs_lines
            new_zs.done = done
            zss.append(new_zs)
            start_pos = lines.index(zs_lines[-1]) + 1
        return zss

    def _create_fx_zss(self, zs_type: str, lines: List[LINE]) -> List[ZS]:
        zss = []
        for zs in self.create_dn_zs(zs_type, lines):
            if len(zs.lines) < 3:
                continue
            in_line = lines[zs.lines[0].index - 1] if zs.lines[0].index > 0 else None
            out_line = lines[zs.lines[-1].index + 1] if zs.lines[-1].index + 1 < len(lines) else None
            if in_line is None or out_line is None or in_line.type == out_line.type:
                continue
            zs.type = out_line.type
            zs.index = len(zss)
            zss.append(zs)
        return zss

    def _create_fl_zss(self, zs_type: str, lines: List[LINE]) -> List[ZS]:
        zss = []
        for zs in self.create_dn_zs(zs_type, lines):
            zs.index = len(zss)
            zss.append(zs)
        return zss

    def _mmd_config_enabled(self, key: str) -> bool:
        return self._config_is_enabled(self.config.get(key, "0"))

    @staticmethod
    def _line_has_mmd(line: LINE, name: str, zs_type: str) -> bool:
        return name in line.line_mmds(zs_type)

    def _add_mmd_once(self, line: LINE, name: str, zs: ZS, zs_type: str, msg: str = "") -> bool:
        if self._line_has_mmd(line, name, zs_type):
            return False
        return line.add_mmd(name, zs, zs_type, msg=msg)

    @staticmethod
    def _line_leave_zs(line: LINE, zs: ZS) -> bool:
        if zs.zg is None or zs.zd is None:
            return False
        if line.type == "down":
            return line.low > zs.zg
        if line.type == "up":
            return line.high < zs.zd
        return False

    @staticmethod
    def _line_not_break_pre_same(line: LINE, pre_same_line: LINE) -> bool:
        if line.type == "down":
            return line.low > pre_same_line.low
        if line.type == "up":
            return line.high < pre_same_line.high
        return False

    def process_mmd(self, line_types: List[str]):
        line_groups = []
        if "bi" in line_types:
            line_groups.append(("bi", self.bis, self.bi_zss, self.config["zs_bi_type"], self.default_bi_zs_type()))
        if "xd" in line_types:
            line_groups.append(("xd", self.xds, self.xd_zss, self.config["zs_xd_type"], self.default_xd_zs_type()))
        if "zsd" in line_types:
            line_groups.append(("zsd", self.zsds, {Config.ZS_TYPE_BZ.value: self.zsd_zss}, [Config.ZS_TYPE_BZ.value], Config.ZS_TYPE_BZ.value))
        if "qsd" in line_types:
            line_groups.append(("qsd", self.qsds, {Config.ZS_TYPE_BZ.value: self.qsd_zss}, [Config.ZS_TYPE_BZ.value], Config.ZS_TYPE_BZ.value))

        for line_type, lines, zss_map, zs_types, default_zs_type in line_groups:
            for line in lines:
                line.mmds = []
                line.bcs = []
                line.zs_type_mmds = {}
                line.zs_type_bcs = {}

            for line in lines:
                for zs_type in zs_types:
                    zss = zss_map.get(zs_type, []) if isinstance(zss_map, dict) else []
                    if line.index >= 2:
                        compare_line = lines[line.index - 2]
                        line_bc = self.beichi_line(compare_line, line)
                        line.add_bc(line_type, None, compare_line, [compare_line], line_bc, zs_type)
                        if line_bc and self._mmd_config_enabled("cl_mmd_cal_qs_1mmd"):
                            self._add_mmd_once(
                                line,
                                "1buy" if line.type == "down" else "1sell",
                                zss[-1] if zss else ZS(default_zs_type, line.start, line.end),
                                zs_type,
                                msg=f"{line_type} 背驰",
                            )

                    match_zss = [zs for zs in zss if zs.lines and zs.lines[-1].index == line.index]
                    if match_zss:
                        pz_bc, compare_line = self.beichi_pz(match_zss[-1], line)
                        line.add_bc("pz", match_zss[-1], compare_line, [compare_line] if compare_line else [], pz_bc, zs_type)
                        if pz_bc:
                            if self._mmd_config_enabled("cl_mmd_cal_not_qs_3mmd_1mmd"):
                                self._add_mmd_once(
                                    line,
                                    "1buy" if line.type == "down" else "1sell",
                                    match_zss[-1],
                                    zs_type,
                                    msg="盘整背驰",
                                )
                            if self._mmd_config_enabled("cl_mmd_cal_qs_3mmd_1mmd"):
                                self._add_mmd_once(
                                    line,
                                    "3buy" if line.type == "down" else "3sell",
                                    match_zss[-1],
                                    zs_type,
                                    msg="盘整背驰三买卖点",
                                )

                    qs_bc, compare_lines = self.beichi_qs(lines, zss, line)
                    line.add_bc("qs", zss[-1] if zss else None, None, compare_lines, qs_bc, zs_type)
                    if qs_bc and zss:
                        if self._mmd_config_enabled("cl_mmd_cal_qs_1mmd"):
                            self._add_mmd_once(
                                line,
                                "1buy" if line.type == "down" else "1sell",
                                zss[-1],
                                zs_type,
                                msg="趋势背驰",
                            )
                        if self._mmd_config_enabled("cl_mmd_cal_qs_3mmd_1mmd"):
                            self._add_mmd_once(
                                line,
                                "3buy" if line.type == "down" else "3sell",
                                zss[-1],
                                zs_type,
                                msg="趋势背驰三买卖点",
                            )

                    if line.index >= 2:
                        pre_same_line = lines[line.index - 2]
                        latest_zs = zss[-1] if zss else None
                        if latest_zs is not None:
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_not_in_zs_3mmd")
                                and self._line_leave_zs(line, latest_zs)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "3buy" if line.type == "down" else "3sell",
                                    latest_zs,
                                    zs_type,
                                    msg="离开中枢后不回中枢",
                                )
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_not_in_zs_gt_9_3mmd")
                                and latest_zs.line_num >= 9
                                and self._line_leave_zs(line, latest_zs)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "3buy" if line.type == "down" else "3sell",
                                    latest_zs,
                                    zs_type,
                                    msg="九段以上中枢后不回中枢",
                                )

                        if self._line_not_break_pre_same(line, pre_same_line):
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_qs_not_lh_2mmd")
                                and qs_bc
                            ):
                                self._add_mmd_once(
                                    line,
                                    "2buy" if line.type == "down" else "2sell",
                                    latest_zs if latest_zs is not None else ZS(default_zs_type, line.start, line.end),
                                    zs_type,
                                    msg="趋势背驰后不创新低高",
                                )
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_qs_bc_2mmd")
                                and pre_same_line.bc_exists([line_type, "pz", "qs"], zs_type)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "2buy" if line.type == "down" else "2sell",
                                    latest_zs if latest_zs is not None else ZS(default_zs_type, line.start, line.end),
                                    zs_type,
                                    msg="前同向背驰后不创新低高",
                                )
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_3mmd_not_lh_bc_2mmd")
                                and pre_same_line.mmd_exists(["3buy", "3sell"], zs_type)
                                and compare_ld_beichi(pre_same_line.get_ld(self), line.get_ld(self), line.type)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "2buy" if line.type == "down" else "2sell",
                                    latest_zs if latest_zs is not None else ZS(default_zs_type, line.start, line.end),
                                    zs_type,
                                    msg="三买卖后不创新低高并背驰",
                                )
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_1mmd_not_lh_2mmd")
                                and pre_same_line.mmd_exists(["1buy", "1sell"], zs_type)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "2buy" if line.type == "down" else "2sell",
                                    latest_zs if latest_zs is not None else ZS(default_zs_type, line.start, line.end),
                                    zs_type,
                                    msg="一买卖后不创新低高",
                                )
                            if (
                                self._mmd_config_enabled("cl_mmd_cal_3mmd_xgxd_not_bc_2mmd")
                                and pre_same_line.mmd_exists(["3buy", "3sell"], zs_type)
                            ):
                                self._add_mmd_once(
                                    line,
                                    "2buy" if line.type == "down" else "2sell",
                                    latest_zs if latest_zs is not None else ZS(default_zs_type, line.start, line.end),
                                    zs_type,
                                    msg="三买卖相关线段后不创新低高",
                                )

                        user_custom_mmd(self, line, lines, zs_type, zss)
        return True

    def beichi_line(self, pre_line, now_line):
        if pre_line is None or now_line is None:
            return False
        if pre_line.type != now_line.type:
            return False
        if pre_line.type == "up":
            if now_line.high < pre_line.high or now_line.low < pre_line.low:
                return False
        if pre_line.type == "down":
            if now_line.low > pre_line.low or now_line.high > pre_line.high:
                return False
        return compare_ld_beichi(pre_line.get_ld(self), now_line.get_ld(self), now_line.type)

    def beichi_pz(self, zs: ZS, now_line: LINE) -> Tuple[bool, Union[LINE, None]]:
        if not zs.lines or zs.lines[-1].index != now_line.index:
            return False, None
        if zs.type not in ("up", "down"):
            return False, None
        if now_line.type == "up" and now_line.high < max(line.high for line in zs.lines):
            return False, None
        if now_line.type == "down" and now_line.low > min(line.low for line in zs.lines):
            return False, None
        return compare_ld_beichi(zs.lines[0].get_ld(self), now_line.get_ld(self), now_line.type), zs.lines[0]

    def beichi_qs(
        self, lines: List[LINE], zss: List[ZS], now_line: LINE
    ) -> Tuple[bool, List[LINE]]:
        if len(zss) < 2:
            return False, []

        one_zs = zss[-2]
        two_zs = zss[-1]
        qs_type = self.zss_is_qs(one_zs, two_zs)
        if qs_type is None or now_line.type != qs_type:
            return False, []
        if two_zs.lines and now_line.index <= two_zs.lines[-1].index:
            return False, []
        if now_line.type == "up" and now_line.high < max(line.high for line in lines[: now_line.index + 1]):
            return False, []
        if now_line.type == "down" and now_line.low > min(line.low for line in lines[: now_line.index + 1]):
            return False, []
        if one_zs.end.index > two_zs.start.index or two_zs.end.index > now_line.end.index:
            return False, []

        compare_lines = []
        if one_zs.lines and two_zs.lines:
            compare_lines = [
                line
                for line in lines
                if one_zs.lines[-1].index < line.index < two_zs.lines[0].index
            ]
        pre_ld = {"macd": query_macd_ld(self, one_zs.end, two_zs.start)}
        now_ld = {"macd": query_macd_ld(self, two_zs.end, now_line.end)}
        return compare_ld_beichi(pre_ld, now_ld, now_line.type), compare_lines

    def _lines_level_ld(self, lines: List[LINE]) -> dict:
        if len(lines) == 0:
            return {}
        if lines[0].type != lines[-1].type:
            return {}

        max_high = max(line.high for line in lines)
        min_low = min(line.low for line in lines)
        if lines[0].type == "up" and lines[0].low != min_low:
            return {}
        if lines[0].type == "down" and lines[0].high != max_high:
            return {}
        if lines[-1].type == "up" and lines[-1].high != max_high:
            return {}
        if lines[-1].type == "down" and lines[-1].low != min_low:
            return {}

        return {"macd": query_macd_ld(self, lines[0].start, lines[-1].end)}

    def zss_is_qs(self, one_zs: ZS, two_zs: ZS) -> Union[str, None]:
        if one_zs is None or two_zs is None:
            return None
        if not one_zs.lines or not two_zs.lines:
            return None
        if one_zs.lines[-1].type != two_zs.lines[-1].type:
            return None
        if self._config_is_enabled(self.config["judge_zs_qs_level"]) and one_zs.level != two_zs.level:
            return None

        if one_zs.zg < two_zs.zd:
            qs_type = "up"
        elif one_zs.zd > two_zs.zg:
            qs_type = "down"
        else:
            return None

        if self.config["zs_wzgx"] == Config.ZS_WZGX_ZGD.value:
            if qs_type == "up" and two_zs.zd <= one_zs.zg:
                return None
            if qs_type == "down" and two_zs.zg >= one_zs.zd:
                return None
        elif self.config["zs_wzgx"] == Config.ZS_WZGX_ZGGDD.value:
            if qs_type == "up" and two_zs.zd <= one_zs.gg:
                return None
            if qs_type == "down" and two_zs.zg >= one_zs.dd:
                return None
        elif self.config["zs_wzgx"] == Config.ZS_WZGX_GD.value:
            if qs_type == "up" and two_zs.dd <= one_zs.gg:
                return None
            if qs_type == "down" and two_zs.gg >= one_zs.dd:
                return None
        else:
            raise Exception("中枢类型配置错误")
        return qs_type

    def _df_to_klines(self, klines: pd.DataFrame) -> List[Kline]:
        rows = klines.copy()
        rows["date"] = pd.to_datetime(rows["date"])
        rows = rows.sort_values("date")
        result = []
        for _, row in rows.iterrows():
            result.append(
                Kline(
                    len(result),
                    row["date"].to_pydatetime()
                    if hasattr(row["date"], "to_pydatetime")
                    else row["date"],
                    float(row["high"]),
                    float(row["low"]),
                    float(row["open"]),
                    float(row["close"]),
                    float(row["volume"]),
                )
            )
        return result
