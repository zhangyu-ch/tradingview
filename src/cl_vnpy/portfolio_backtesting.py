"""Legacy Chanlun runtime module removed."""

MESSAGE = "缠论模块已移除，请改用 tradingview_zy.strategies、selection 或 monitoring 的自定义策略接口。"


def unavailable(*args, **kwargs):
    raise RuntimeError(MESSAGE)


def run_backtesting(*args, **kwargs):
    raise RuntimeError(MESSAGE)


def show_portafolio(*args, **kwargs):
    raise RuntimeError(MESSAGE)


if __name__ == "__main__":
    print(MESSAGE)
