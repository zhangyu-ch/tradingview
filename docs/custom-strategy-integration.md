# 自定义策略接入指南

`tradingview_zy` 的选股、监控、回测和交易信号统一通过普通 K 线数据接入，不依赖缠论结构。

## 策略类约定

策略类使用 `module:ClassName` 路径加载。类实例必须提供 `run(context)` 方法。

```python
from tradingview_zy.strategies.base import StrategyContext, StrategySignal


class CloseAboveOpenStrategy:
    name = "close_above_open"

    def run(self, context: StrategyContext):
        last = context.klines.iloc[-1]
        if float(last["close"]) <= float(last["open"]):
            return []
        return [
            StrategySignal(
                code=context.code,
                name=context.name,
                action="select",
                score=1.0,
                message="收盘价高于开盘价",
                frequency=context.frequency,
                event_time=context.now,
            )
        ]
```

`run(context)` 可以返回 `StrategySignal`、`list[StrategySignal]` 或 `None`。返回 `None` 表示没有信号。

## StrategyContext 字段

- `market`：市场，例如 `a`、`hk`、`us`。
- `code`：标的代码。
- `name`：标的名称。
- `frequency`：周期，例如 `5m`、`d`。
- `klines`：普通 pandas DataFrame，包含 `date`、`open`、`close`、`high`、`low`、`volume`。
- `now`：本次任务触发时间。
- `metadata`：调用方传入的附加信息。

## StrategySignal 字段

- `code`：标的代码。
- `name`：标的名称。
- `action`：`select`、`watch`、`buy`、`sell`、`open`、`close`、`ignore`。
- `score`：排序或强度分数。
- `message`：展示给用户的原因。
- `frequency`：触发周期。
- `event_time`：触发时间。
- `metadata`：策略自定义信息。

## 选股接入

在 `src/tradingview_zy/config.py` 中配置：

```python
XUANGU_STRATEGIES = {
    "收盘强势": {
        "strategy_path": "my_strategies.close_above_open:CloseAboveOpenStrategy",
        "strategy_kwargs": {},
        "task_memo": "收盘价高于开盘价",
        "frequency_memo": "选择一个 K 线周期",
        "frequency_num": 1,
    }
}
```

Web 选股任务会读取自选组股票，按配置周期拉取 K 线，然后执行策略。任务显式选择目标自选组时，策略返回的标的会写入该目标组；未指定目标组时只保存任务运行结果，不覆盖源自选组。

## 监控接入

监控任务保存 `strategy_path` 和 `strategy_kwargs`。任务触发时会拉取当前标的 K 线，并把策略返回的 `StrategySignal` 写入监控记录。

监控记录使用通用字段展示：

- `event_type`：事件类型。
- `action`：策略动作。
- `score`：策略分数。
- `msg`：策略返回原因。

## 回测和交易接入

选股和监控直接消费 `StrategySignal`。回测策略目前仍使用 `tradingview_zy.backtesting.base.Operation` 表达开平仓操作，需要在你的回测策略中把普通信号转换为 `Operation`。

最小示例：

```python
from tradingview_zy.backtesting.base import Operation


def signal_to_operation(signal):
    if signal.action not in {"buy", "open"}:
        return None
    return Operation(
        code=signal.code,
        opt="open",
        signal=signal.action,
        msg=signal.message,
    )
```

实盘交易层保留下单、撤单、账户和持仓查询等执行能力。交易代码应显式决定信号到订单的转换规则，例如标的、方向、数量、价格类型和风控限制；不要假设 `StrategySignal` 会被 trader 自动下单。