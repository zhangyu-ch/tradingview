# tradingview_zy

`tradingview_zy` 是一个通用行情、TradingView 图表、选股监控、回测和交易执行工具。

本仓库已从原缠论分析系统迁移为普通行情/交易工具。运行路径中不再保留缠论计算、分型、笔、线段、中枢、买卖点、背驰等模块。历史缠论源码已压缩归档到 `archive/chanlun-runtime-source.zip`，相关文档已迁移到 `archive/docs/`。

## 当前保留能力

- 多市场交易所适配和 K 线查询。
- TradingView UDF 风格基础 K 线接口。
- 自选股、通用选股任务和通用监控任务外壳。
- 自定义策略接入接口。
- 通用回测框架。
- trader 下单、撤单、账户和持仓等交易执行适配。

## 环境

项目优先使用 Python 3.11：

```bash
uv venv --python=3.11 .venv
uv sync
export PYTHONPATH="$PWD/src"
```

运行前复制配置：

```bash
cp src/tradingview_zy/config.py.demo src/tradingview_zy/config.py
```

检查环境：

```bash
PYTHONPATH="$PWD/src" uv run python check_env.py
```

启动 Web 服务：

```bash
PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/app.py nobrowser
```

## 自定义策略

选股、监控、回测和交易信号统一面向普通 K 线数据。接入方式见：

- `docs/custom-strategy-integration.md`
- `docs/web-right-panel-extension.md`
