"""Legacy Chanlun runtime module removed."""

MESSAGE = "缠论模块已移除，请改用 tradingview_zy.strategies、selection 或 monitoring 的自定义策略接口。"


def unavailable(*args, **kwargs):
    raise RuntimeError(MESSAGE)


def monitoring_code(*args, **kwargs):
    raise RuntimeError(MESSAGE)


def kchart_to_png(*args, **kwargs):
    raise RuntimeError(MESSAGE)


if __name__ == "__main__":
    print(MESSAGE)
