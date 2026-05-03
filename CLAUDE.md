# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

这是 `tradingview_zy` 通用行情、TradingView 图表、选股监控、回测和交易执行工具。项目主线围绕多市场行情接入、Web 图表展示、脚本化任务和交易适配展开。历史缠论源码与相关文档已归档，不应沿用旧项目定位。

主要代码分层：

- `src/tradingview_zy/`：核心 Python 包，包含基础枚举/数据结构、配置模板、行情存储、图表辅助、监控、自选等通用能力。
- `src/tradingview_zy/exchange/`：行情与交易所适配层。`exchange.py` 定义 `Exchange` 抽象接口，`exchange/__init__.py` 的 `get_exchange(Market)` 根据 `src/tradingview_zy/config.py` 中的 `EXCHANGE_*` 配置选择并缓存具体实现。
- `src/tradingview_zy/backtesting/`：回测框架。`backtest.py` 组合回测 K 线、回测交易器和策略类；`base.py` 定义 `Strategy`、`Trader`、`MarketDatas`、`POSITION`、`Operation` 等基类。
- `src/tradingview_zy/strategy/`：策略实现，策略继承 `tradingview_zy.backtesting.base.Strategy` 并实现 `open` / `close`。
- `src/tradingview_zy/trader/`：实盘/交易执行适配，按市场区分 A 股、港股、期货、数字货币等。
- `web/tradingview_zy_chart/`：Web 应用。`app.py` 将 `src` 和 Web 目录加入 `sys.path`，用 Tornado 包装 Flask 应用并监听 `config.WEB_HOST:9900`；`cl_app/__init__.py` 创建 Flask app，提供 TradingView 数据接口、登录、监控、选股等路由。
- `script/crontab/` 与 `script/trader/`：行情同步、选股和交易任务脚本。
- `notebook/`：Jupyter 回测、图表和研究示例。

支持市场枚举在 `src/tradingview_zy/base.py`：A 股、港股、国内期货、纽约期货、数字货币合约/现货、美股、外汇。

## 环境与配置

Python 版本以 `pyproject.toml` 为准：`>=3.11`。安装文档同时说明 3.8、3.9、3.10、3.11 可用；本仓库优先使用 3.11。

项目需要 `PYTHONPATH` 指向仓库的 `src` 目录，否则 `check_env.py` 会提示无法导入 `tradingview_zy`：

```bash
export PYTHONPATH="$PWD/src"
```

运行前需要从示例配置复制真实配置：

```bash
cp src/tradingview_zy/config.py.demo src/tradingview_zy/config.py
```

`src/tradingview_zy/config.py` 已被 `.gitignore` 排除；不要依赖它已经存在。授权文件路径由 `check_env.py` 检查：`src/pyarmor_runtime_005445/pyarmor.rkey`。

## 常用命令

优先使用仓库自带的 `uv` 配置：

```bash
uv venv --python=3.11 .venv
uv sync
```

Windows 下也可双击或运行：

```bash
./windows_install.bat
```

检查环境：

```bash
uv run check_env.py
```

运行 Web 服务：

```bash
uv run web/tradingview_zy_chart/app.py
```

不自动打开浏览器：

```bash
uv run web/tradingview_zy_chart/app.py nobrowser
```

Windows 启动脚本：

```bash
./windows_run.bat
```

pytest 已在 `pyproject.toml` 依赖中声明，但仓库没有集中测试目录；现有测试/示例更像脚本。运行单个测试文件示例：

```bash
uv run pytest src/cl_wtpy/test_hotpicker/testHots.py
```

运行单个 Python 脚本时保留 `PYTHONPATH`：

```bash
PYTHONPATH="$PWD/src" uv run python path/to/script.py
```

## 开发注意事项

- 配置驱动的市场选择集中在 `src/tradingview_zy/config.py.demo` 的 `EXCHANGE_*` 变量和 `src/tradingview_zy/exchange/__init__.py`；新增市场/数据源时同时检查 `Market` 枚举、Exchange 实现、Web 端市场映射和配置示例。
- Web 图表接口依赖 TradingView UDF 风格路由，如 `/tv/config`、`/tv/search`、`/tv/symbols`、`/tv/history`；改行情字段或频率映射时要同步检查 Web 路由与 exchange 的 `support_frequencys()`。
- 回测策略应以 `Strategy.open` / `Strategy.close` 返回 `Operation`，并通过 `MarketDatas` 获取指定标的/周期的数据。
- 数据默认保存路径由 `config.DATA_PATH` 决定；以 `.` 开头时会落到用户 home 目录下。
