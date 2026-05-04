# tradingview_zy 架构与二次开发手册

本文面向第一次系统阅读本项目、准备学习源码或做二次开发的使用者。它描述的是当前 `tradingview_zy` 主线：通用行情、TradingView 图表、选股监控、回测和交易执行工具。历史缠论源码与文档只作为归档资料保留在 `archive/`，不属于当前运行架构。

## 1. 项目定位

`tradingview_zy` 可以理解为一套围绕普通 K 线数据工作的量化工具底座：

- 向多个市场和数据源获取行情。
- 将行情转换为 TradingView UDF 风格接口，供 Web 图表展示。
- 管理自选组、选股任务和监控提醒任务。
- 通过通用策略协议接入自定义策略。
- 提供历史回测框架。
- 保留不同市场的交易执行适配。

当前主线不再提供缠论计算、分型、笔、线段、中枢、买卖点、背驰等运行能力。看到 `archive/`、历史数据库表字段名、少量历史变量名时，要把它们理解为迁移遗留或兼容存储，不要把它们当成当前功能方向。

## 2. 推荐阅读顺序

如果你想快速建立全局认知，推荐按下面顺序读代码：

1. `README.md`：当前项目能力、环境和入口。
2. `CLAUDE.md`：本仓库维护边界和开发注意事项。
3. `项目结构总览.md`：快速了解各目录职责。
4. `src/tradingview_zy/base.py`：市场枚举。
5. `src/tradingview_zy/exchange/exchange.py`：交易所抽象接口。
6. `src/tradingview_zy/exchange/__init__.py`：不同市场如何选择具体交易所实现。
7. `web/tradingview_zy_chart/app.py`：Web 服务启动入口。
8. `web/tradingview_zy_chart/cl_app/__init__.py`：Flask 路由、TradingView 接口、自选和任务页面。
9. `src/tradingview_zy/strategies/base.py` 与 `loader.py`：通用策略输入输出协议。
10. `src/tradingview_zy/selection.py`、`monitoring.py`：选股与监控如何运行策略。
11. `src/tradingview_zy/backtesting/backtest.py` 与 `backtesting/base.py`：回测如何组织数据、策略和交易。
12. `src/tradingview_zy/trader/`：实盘交易适配。
13. `tests/`：当前架构边界和关键回归约束。

## 3. 顶层目录职责

| 路径 | 职责 | 学习价值 |
| --- | --- | --- |
| `src/tradingview_zy/` | 核心 Python 包，包含行情、数据库、自选、策略、选股监控、回测和交易 | 二次开发主战场 |
| `web/tradingview_zy_chart/` | Web 服务、Flask 路由、TradingView 图表页面、静态资源和任务外壳 | 修改页面和接口必看 |
| `script/` | Windows 本地 uv 工具、行情同步脚本、选股脚本、交易脚本和进程配置 | 部署、批处理和自动任务参考 |
| `docs/` | 当前有效开发文档 | 新增文档优先放这里 |
| `tests/` | 回归测试和架构边界测试 | 修改后验证行为 |
| `notebook/` | Jupyter 研究和示例 | 学习与实验参考 |
| `joinquant/` | 聚宽相关示例 | 外部平台参考 |
| `archive/` | 历史源码和历史文档归档 | 只读参考，不代表当前运行能力 |
| `package/` | 本地 wheel 包，如 `ta-lib`、`pytdx` | 依赖安装支持 |
| `windows_install.bat` / `windows_run.bat` | Windows 安装和启动辅助 | 本地运行入口 |
| `pyproject.toml` | 项目依赖、Python 版本和 uv 源配置 | 环境安装依据 |

## 4. 环境、配置与启动

### 4.1 Python 与依赖

项目优先使用 Python 3.11，依赖由 `pyproject.toml` 管理。常用命令：

```bash
uv venv --python=3.11 .venv
uv sync
```

本项目运行时需要让 Python 能导入 `src/tradingview_zy`：

```bash
export PYTHONPATH="$PWD/src"
```

Windows 下 `windows_run.bat` 会自动设置：

```bat
set "PYTHONPATH=%ROOT_DIR%src"
```

### 4.2 配置文件

运行前需要复制配置模板：

```bash
cp src/tradingview_zy/config.py.demo src/tradingview_zy/config.py
```

`src/tradingview_zy/config.py` 是本地真实配置，通常不提交。关键配置包括：

- `WEB_HOST`：Web 监听地址。
- `LOGIN_PWD`：Web 登录密码，为空则不需要登录。
- `DATA_PATH`：项目数据目录；以 `.` 开头时写入用户 home 目录。
- `DB_TYPE`、`DB_DATABASE` 等：SQLite 或 MySQL 配置。
- `REDIS_HOST`：Redis，可为空。
- `EXCHANGE_A`、`EXCHANGE_HK`、`EXCHANGE_US` 等：各市场默认数据源。
- 各交易接口账号：富途、天勤、CTP、币安、Polygon、Alpaca、IB 等。
- `XUANGU_STRATEGIES`：自定义选股策略配置。

注意：配置模板中仍可能出现历史命名，例如默认 `DATA_PATH = ".chanlun_pro"`、数据库名 `chanlun_klines`、少量注释。这是历史兼容，不代表当前运行项目仍依赖缠论模块。

### 4.3 环境检查

```bash
PYTHONPATH="$PWD/src" uv run python check_env.py
```

`check_env.py` 会检查：

- Python 版本。
- 是否能导入 `tradingview_zy`。
- 是否存在 `src/tradingview_zy/config.py`。
- 代理、Redis、MySQL 连接。

Web 启动流程当前已不检查缠论授权文件。`check_env.py` 中若仍看到授权检查，可视为历史检查残留；整理环境检查脚本时应优先清理这类提示。

### 4.4 启动 Web

Linux/macOS 或 Git Bash：

```bash
PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/app.py nobrowser
```

Windows：

```bat
windows_run.bat
```

Web 入口 `web/tradingview_zy_chart/app.py` 做三件事：

1. 把 `src` 和 Web 目录加入 `sys.path`。
2. 调用 `cl_app.create_app()` 创建 Flask 应用。
3. 用 Tornado `HTTPServer(WSGIContainer(app))` 在 `config.WEB_HOST:9900` 启动服务。

## 5. 核心包 `src/tradingview_zy`

### 5.1 市场枚举

`src/tradingview_zy/base.py` 定义 `Market`：

- `a`：A 股。
- `hk`：港股。
- `futures`：国内期货。
- `ny_futures`：纽约期货。
- `currency`：数字货币合约。
- `currency_spot`：数字货币现货。
- `us`：美股。
- `fx`：外汇。

Web 路由、交易所选择、自选组、数据库记录和任务配置都大量使用这些 market 值。

### 5.2 交易所抽象

`src/tradingview_zy/exchange/exchange.py` 定义 `Exchange` 抽象基类。一个交易所实现至少要考虑这些方法：

- `default_code()`：Web 默认展示标的。
- `support_frequencys()`：支持周期映射，例如 `{"d": "日线"}`。
- `all_stocks()`：所有可用标的。
- `now_trading()`：当前是否交易中。
- `klines(code, frequency, start_date=None, end_date=None, args=None)`：返回 K 线 DataFrame。
- `ticks(codes)`：批量 tick。
- `stock_info(code)`：标的基本信息。
- `stock_owner_plate(code)`、`plate_stocks(code)`：板块相关。
- `balance()`、`positions()`、`order()`：账户、持仓和下单。

K 线 DataFrame 是项目最核心的数据结构，通常包含：

- `date`
- `frequency`
- `code`
- `open`
- `close`
- `high`
- `low`
- `volume`

期货等市场可能额外包含 `position`。

### 5.3 交易所选择

`src/tradingview_zy/exchange/__init__.py` 的 `get_exchange(market: Market)` 负责按配置选择具体实现，并缓存实例。

例子：

- `Market.A` 根据 `config.EXCHANGE_A` 选择 `ExchangeTDX`、`ExchangeFutu`、`ExchangeBaostock`、`ExchangeDB`、`ExchangeQMT`。
- `Market.US` 根据 `config.EXCHANGE_US` 选择 `ExchangeAlpaca`、`ExchangePolygon`、`ExchangeIB`、`ExchangeTDXUS`、`ExchangeDB`。
- `Market.CURRENCY` 根据 `config.EXCHANGE_CURRENCY` 选择 `ExchangeBinance` 或 `ExchangeDB`。

这个函数是 Web、选股、监控、脚本和交易访问行情的统一入口。

### 5.4 数据库层

`src/tradingview_zy/db.py` 使用 SQLAlchemy。`DB` 是单例，初始化时根据 `config.DB_TYPE` 创建 SQLite 或 MySQL engine，并自动 `Base.metadata.create_all()`。

SQLite 默认路径：

```text
get_data_path() / "db" / f"{config.DB_DATABASE}.sqlite"
```

主要数据类型：

- K 线动态表：由 `DB.klines_tables(market, stock_code)` 按市场和标的生成。
- 自选分组：`TableByZxGroup`。
- 自选标的：`TableByZixuan`。
- 监控任务：`TableByAlertTask`。
- 监控记录：`TableByAlertRecord`。
- TradingView 标记：`TableByTVMarks`、`TableByTVMarksPrice`。
- TradingView 图表布局：`TableByTVCharts`。
- TradingView 画线：`TableByTVDrawings`。
- 订单：`TableByOrder`。
- AI 分析记录：`TableByAIAnalyse`。

因为数据库表名和字段名保留了部分历史命名，例如 `cl_*` 表名前缀、`check_idx_ma_info` 映射为 `strategy_config`，二次开发时应优先使用当前代码提供的属性和方法，不要按字段名推断业务含义。

### 5.5 自选组

`src/tradingview_zy/zixuan.py` 的 `ZiXuan` 封装自选组能力：

- 获取分组：`get_zx_groups()`。
- 添加/删除分组：`add_zx_group()`、`del_zx_group()`。
- 查询组内标的：`zx_stocks()`。
- 添加/删除标的：`add_stock()`、`del_stock()`。
- 修改颜色、名称、排序：`color_stock()`、`rename_stock()`、`sort_top_stock()`、`sort_bottom_stock()`。
- 清空分组：`clear_zx_stocks()`。
- 查询某标的属于哪些分组：`query_code_zx_names()`。

Web 自选接口和选股任务都依赖它。

### 5.6 Web payload

`src/tradingview_zy/web_payloads.py` 将普通 K 线转换为 TradingView history 响应：

- `filter_klines_by_timestamp_range(klines, start_ts, end_ts)`：按时间戳裁剪 K 线。
- `klines_to_tv_history(klines, update, status="ok")`：输出 `s/t/o/c/h/l/v/update`。

当前图表接口只返回普通 OHLCV，不返回旧 overlay 字段。

## 6. Web 应用架构

### 6.1 启动入口

`web/tradingview_zy_chart/app.py` 是进程入口。它不写业务逻辑，主要负责环境路径、异常输出、Tornado 包装和浏览器打开。

### 6.2 Flask 应用主体

`web/tradingview_zy_chart/cl_app/__init__.py` 的 `create_app()` 是 Web 核心。它负责：

- 初始化 TornadoScheduler。
- 创建 Flask app 和登录管理。
- 定义市场周期、默认标的、时区、类型映射。
- 注册页面路由。
- 注册 TradingView UDF 接口。
- 处理自选、监控、选股任务、设置、板块接口。

主要路由按职责分组：

| 路由 | 作用 |
| --- | --- |
| `/login` | 登录 |
| `/` | 主图表页面 |
| `/tv/config` | TradingView datafeed 配置 |
| `/tv/search` | 标的搜索 |
| `/tv/symbols` | 标的信息解析 |
| `/tv/history` | K 线历史数据 |
| `/tv/marks`、`/tv/timescale_marks` | 图表标记 |
| `/tv/<version>/charts` | 图表布局保存/读取/删除 |
| `/tv/<version>/study_templates` | 指标模板保存/读取/删除 |
| `/tv/<version>/drawings` | 手工画线保存/读取 |
| `/ticks` | tick 查询 |
| `/get_zixuan_*`、`/zixuan_*` | 自选组相关 |
| `/alert_*` | 监控任务与记录 |
| `/jobs` | 调度任务列表 |
| `/xuangu/task_*` | 选股任务 |
| `/setting`、`/setting/save` | Web 设置 |
| `/a/bkgn_*` | A 股行业概念相关 |

### 6.3 TradingView K 线数据流

图表加载 K 线的核心链路：

```text
浏览器 TradingView Datafeed
  -> GET /tv/history?symbol=a:SH.000001&resolution=1D&from=...&to=...
  -> cl_app.__init__.py:tv_history()
  -> 解析 market/code/resolution
  -> get_exchange(Market(market))
  -> ex.klines(code, frequency)
  -> 可选按 from/to 过滤
  -> klines_to_tv_history()
  -> 返回 {s, t, o, h, l, c, v, update}
```

`firstDataRequest=true` 代表 TradingView 首次请求。当前实现会返回交易所已有的完整历史，便于图表缩小时看到更早 K 线；后续实时轮询请求仍按窗口过滤并受交易时间限制，避免非交易时段频繁返回重复数据。

### 6.4 前端资源

核心路径：

- `web/tradingview_zy_chart/cl_app/templates/index.html`：主图表页面。
- `web/tradingview_zy_chart/cl_app/templates/alert.html`：监控任务页面。
- `web/tradingview_zy_chart/cl_app/static/js/charts.js`：图表相关业务脚本。
- `web/tradingview_zy_chart/cl_app/static/js/alert.js`：监控页面交互。
- `web/tradingview_zy_chart/cl_app/static/datafeeds/udf/`：TradingView UDF datafeed 前端实现。
- `web/tradingview_zy_chart/cl_app/static/charting_library/`：TradingView Advanced Charts 静态资源。

扩展右侧面板时，优先参考 `docs/web-right-panel-extension.md`，原则是不改 TradingView 图表库源码，只在外层页面组合扩展区域。

## 7. 策略、选股和监控

### 7.1 策略协议

`src/tradingview_zy/strategies/base.py` 定义两个核心 dataclass：

`StrategyContext`：

- `market`
- `code`
- `name`
- `frequency`
- `klines`
- `now`
- `metadata`

`StrategySignal`：

- `code`
- `name`
- `action`：`select`、`watch`、`buy`、`sell`、`open`、`close`、`ignore`
- `score`
- `message`
- `frequency`
- `event_time`
- `metadata`

策略类必须实现：

```python
def run(self, context: StrategyContext):
    ...
```

返回值可以是：

- `StrategySignal`
- `list[StrategySignal]`
- `None`

`normalize_strategy_results()` 会把这些返回值规范化为 `list[StrategySignal]`。

### 7.2 策略加载

`src/tradingview_zy/strategies/loader.py` 的 `load_strategy(dotted_path, **kwargs)` 使用 `module:ClassName` 格式加载策略。

例如：

```python
load_strategy("my_strategies.close_above_open:CloseAboveOpenStrategy", threshold=1.02)
```

加载后会检查实例是否有可调用的 `run(context)`。

### 7.3 选股 Runner

`src/tradingview_zy/selection.py` 的 `SelectionRunner` 流程：

```text
stocks 列表
  -> 对每个 stock 调 ex.klines(code, frequency)
  -> 构造 StrategyContext
  -> strategy.run(context)
  -> normalize_strategy_results()
  -> 汇总 StrategySignal
```

Web 选股任务封装在 `web/tradingview_zy_chart/cl_app/xuangu_tasks.py`。它会：

1. 从 `config.XUANGU_STRATEGIES` 读取任务配置。
2. 用 `load_strategy()` 加载策略。
3. 读取全部标的或某个自选组标的。
4. 对每个周期运行 `SelectionRunner`。
5. 如果指定目标自选组，则清空目标组并写入策略命中的标的。
6. 保存本次运行结果到 `running_tasks`。

### 7.4 监控 Runner

`src/tradingview_zy/monitoring.py` 的 `MonitoringRunner` 面向单个标的运行策略：

```text
code/name/frequency
  -> ex.klines(code, frequency)
  -> StrategyContext
  -> strategy.run(context)
  -> StrategySignal 列表
```

Web 监控任务在 `web/tradingview_zy_chart/cl_app/alert_tasks.py`：

1. 从数据库读取监控任务。
2. 交易所不在交易时间时跳过实时监控。
3. 从自选组读取标的。
4. 从 `strategy_config` JSON 解析 `strategy_path` 和 `strategy_kwargs`。
5. 加载策略并运行 `MonitoringRunner`。
6. 将信号写入监控记录，字段包括 `event_type`、`action`、`score`、`event_time` 和 `alert_msg`。

## 8. 回测架构

回测主入口是 `src/tradingview_zy/backtesting/backtest.py` 的 `BackTest`。

### 8.1 配置对象

创建 `BackTest(config)` 时，配置必须包含：

- `mode`
- `market`
- `base_code`
- `codes`
- `frequencys`
- `start_datetime`
- `end_datetime`
- `init_balance`
- `fee_rate`
- `max_pos`
- `strategy`

可选：

- `data_config`
- `save_file`

### 8.2 回测核心对象

- `BackTestKlines`：组织历史 K 线，按时间推进。
- `BackTestTrader`：模拟资金、持仓、手续费、成交记录。
- `Strategy`：回测策略基类，定义 `open()` 和 `close()`。
- `Operation`：策略返回的开平仓指令。
- `POSITION`：持仓对象。
- `MarketDatas`：回测或实盘行情访问抽象。

回测策略和通用 `StrategySignal` 协议不是同一个接口。选股/监控直接消费 `StrategySignal`；回测当前仍使用 `Operation` 表示开平仓动作。如果要复用通用信号，需要自己写转换层。

### 8.3 回测执行流

```text
BackTest(config)
  -> 创建 BackTestTrader
  -> 创建 BackTestKlines
  -> trader.set_strategy(strategy)
  -> trader.set_data(datas)
  -> BackTest.run()
  -> datas.next(next_frequency) 推进行情
  -> trader 更新持仓盈亏
  -> 调用 strategy.open / strategy.close
  -> 生成 Operation
  -> trader 执行模拟开平仓
  -> 汇总绩效和记录
```

## 9. 交易执行架构

交易执行相关代码在 `src/tradingview_zy/trader/`。

常见文件：

- `online_market_datas.py`：实盘行情数据访问对象，实现 `MarketDatas`。
- `trader_a_stock.py`：A 股交易适配。
- `trader_hk_stock.py`：港股交易适配。
- `trader_futures.py`：期货交易适配。
- `trader_currency.py`：数字货币交易适配。
- `trader_ctp.py`：CTP 交易适配。
- `trader_qmt_stock.py`：QMT A 股交易适配。

实盘链路通常应显式拆成三步：

1. 策略产生信号。
2. 风控/仓位模块决定是否交易、交易方向、数量和价格。
3. 交易适配层执行下单、撤单、账户和持仓查询。

不要默认把 `StrategySignal` 直接自动下单。信号到订单之间必须有清晰的风控转换规则。

## 10. 脚本与批处理

`script/` 主要服务部署、同步和批量任务。

### 10.1 `script/bin`

包含 Windows 下的 uv 可执行文件：

- `uv.exe`
- `uvw.exe`
- `uvx.exe`

`windows_run.bat` 默认使用这里的 `uv.exe` 启动 Web。

### 10.2 `script/crontab`

主要是行情同步和批处理脚本，例如：

- `reboot_sync_a_klines.py`
- `reboot_sync_hk_klines.py`
- `reboot_sync_us_klines.py`
- `reboot_sync_futures_klines.py`
- `reboot_sync_currency_klines.py`
- `run_history_xuangu.py`
- `xuangu_by_process.py`
- `xuangu_by_same.py`
- `script_ib_tasks.py`

如果要做离线行情同步、历史选股、批量任务，可从这里找入口。

### 10.3 `script/trader`

保存不同市场交易任务的重启脚本。当前部分脚本可能是占位或历史迁移后的薄入口，使用前应读具体文件确认是否仍有实际逻辑。

### 10.4 `script/*.config.js`

进程管理或部署配置，例如 Web 服务、Jupyter、富途 OpenD 相关配置。

## 11. 二次开发常见任务

### 11.1 新增一个数据源或交易所

通常需要改这些地方：

1. `src/tradingview_zy/exchange/exchange.py`
   - 确认你的实现满足 `Exchange` 抽象接口。
2. 新增 `src/tradingview_zy/exchange/exchange_xxx.py`
   - 实现 `default_code()`、`support_frequencys()`、`klines()` 等。
3. `src/tradingview_zy/exchange/__init__.py`
   - 在对应 `Market` 分支中加入配置分派。
4. `src/tradingview_zy/config.py.demo`
   - 在对应 `EXCHANGE_*` 注释和默认配置中加入新数据源名称。
5. 如新增市场而非新增数据源，还要改：
   - `src/tradingview_zy/base.py` 的 `Market`。
   - Web 中的市场周期、默认代码、时区、类型映射。
   - 数据库 K 线表名规则。
   - 前端市场选择和脚本入口。
6. 添加测试。

开发建议：先新增一个最小 `klines()`，确保 Web `/tv/history` 能展示 OHLCV，再补 tick、板块、账户和下单能力。

### 11.2 新增一个自定义策略

推荐步骤：

1. 写策略类，提供 `run(context)`。
2. 返回 `StrategySignal` 或列表。
3. 确保策略模块能被 Python import。
4. 在 `config.XUANGU_STRATEGIES` 配置：

```python
XUANGU_STRATEGIES = {
    "demo": {
        "name": "示例策略",
        "strategy_path": "my_package.my_module:MyStrategy",
        "strategy_kwargs": {},
        "task_memo": "策略说明",
        "frequency_num": 1,
        "frequency_memo": "单周期",
    }
}
```

5. Web 选股任务选择对应策略和周期。
6. 如用于监控，在监控任务中保存 `strategy_config` JSON。

参考文档：`docs/custom-strategy-integration.md`。

### 11.3 新增 Web 接口

推荐位置：`web/tradingview_zy_chart/cl_app/__init__.py`。

原则：

- 输入来自 `request.args` 或 `request.form` 时做必要校验。
- 返回普通 JSON，不把 HTML 拼接放后端。
- 复用 `src/tradingview_zy` 的核心能力，不在路由中写复杂业务。
- 如果接口给前端渲染用户文本，前端用 `textContent`，不要直接拼接 `innerHTML`。
- 加测试时可用 Flask `test_request_context()` 调用路由函数。

### 11.4 扩展 TradingView 图表页面

常见修改点：

- 页面结构：`templates/index.html`。
- 图表初始化和交互：`static/js/charts.js`。
- UDF datafeed：`static/datafeeds/udf/`。
- 后端数据接口：`cl_app/__init__.py` 的 `/tv/*` 路由。

建议不要修改 `static/charting_library/` 内的 TradingView 库源码。外层组合更容易维护。

### 11.5 新增定时任务

Web 内部调度使用 APScheduler，初始化在 `create_app()` 中：

```text
TornadoScheduler(timezone="Asia/Shanghai")
```

已有任务封装：

- `cl_app/xuangu_tasks.py`
- `cl_app/alert_tasks.py`
- `cl_app/other_tasks.py`

新增任务建议：

1. 把业务逻辑放在 `src/tradingview_zy` 或 `cl_app/*_tasks.py` 的方法里。
2. 路由只负责接收参数和触发任务。
3. 任务状态通过 scheduler listener 写入 `scheduler.my_task_list`，供 `/jobs` 查看。

### 11.6 新增交易适配

如果是新市场交易：

1. 先实现或完善 `Exchange` 的账户、持仓、下单能力。
2. 在 `src/tradingview_zy/trader/` 新增对应 trader。
3. 使用 `OnlineMarketDatas` 获取实时行情。
4. 显式实现信号到订单的风控转换。
5. 用模拟或小范围环境验证，避免直接实盘大范围下单。

## 12. 测试体系

当前测试集中在 `tests/`。

主要测试文件：

- `tests/test_no_runtime_chanlun_imports.py`
  - 防止运行路径再次导入已移除的旧模块。
- `tests/test_web_payloads.py`
  - 验证 Web payload 只返回普通 OHLCV 和时间过滤行为。
- `tests/test_selection_monitoring.py`
  - 验证选股、监控、Web 告警、历史 K 线接口等行为。
- `tests/test_strategy_loader.py`
  - 验证策略加载器。
- `tests/test_backtesting_base_generic.py`
  - 验证回测基础对象的通用行为。

常用命令：

```bash
uv run pytest
uv run pytest tests/test_selection_monitoring.py
uv run pytest tests/test_web_payloads.py
```

修改行为时建议遵循：

1. 先写失败测试复现问题或定义新行为。
2. 做最小实现。
3. 跑相关测试。
4. 跑全量 `uv run pytest`。

## 13. 当前架构边界和旧代码边界

当前运行路径不应导入这些旧模块或前缀：

- `chanlun`
- `tradingview_zy.cl`
- `tradingview_zy.cl_analyse`
- `tradingview_zy.cl_interface`
- `tradingview_zy.cl_utils`
- `tradingview_zy.kcharts`
- `tradingview_zy.monitor`
- `tradingview_zy.strategy`
- `tradingview_zy.xuangu`
- `cl_myquant`
- `cl_vnpy`

边界测试在 `tests/test_no_runtime_chanlun_imports.py`。

历史资料可以读：

- `archive/`
- 外部旧版只读参考目录 `E:\AI-code-local\chanlun-pro`

但不要修改旧版目录，也不要把旧缠论运行逻辑重新接回当前项目。

## 14. 学习路线建议

### 14.1 只想跑起来看图

1. 安装依赖。
2. 复制 `config.py.demo` 为 `config.py`。
3. 设置 `EXCHANGE_A` 等数据源。
4. 运行 `windows_run.bat` 或 `uv run web/tradingview_zy_chart/app.py nobrowser`。
5. 从 `/tv/history` 链路理解图表如何取 K 线。

### 14.2 想写选股策略

1. 阅读 `docs/custom-strategy-integration.md`。
2. 阅读 `strategies/base.py`。
3. 写一个 `run(context)`。
4. 配置 `XUANGU_STRATEGIES`。
5. 从 Web 选股任务或 `SelectionRunner` 跑策略。
6. 用测试构造 fake exchange 验证策略输出。

### 14.3 想改 Web 页面

1. 阅读 `web/tradingview_zy_chart/app.py`。
2. 阅读 `cl_app/__init__.py` 的路由。
3. 阅读 `templates/index.html` 和 `static/js/charts.js`。
4. 如果是右侧窗口扩展，按 `docs/web-right-panel-extension.md` 做。
5. 新增接口时添加 Flask route 测试。

### 14.4 想新增行情源

1. 阅读 `exchange/exchange.py`。
2. 找一个相近实现参考，例如 `exchange_tdx.py` 或 `exchange_db.py`。
3. 新增 exchange 实现。
4. 接入 `exchange/__init__.py` 和 `config.py.demo`。
5. 用 `ex.klines()` 先验证 DataFrame 字段。
6. 再打开 Web 图表验证 `/tv/history`。

### 14.5 想研究回测

1. 阅读 `backtesting/base.py` 的 `Strategy`、`Operation`、`MarketDatas`。
2. 阅读 `backtesting/backtest.py` 的 `BackTest.__init__()` 和 `run()`。
3. 看 `notebook/` 中的示例。
4. 写一个最小策略，实现 `open()`、`close()`。
5. 用小范围标的和短时间段验证。

## 15. 开发注意事项

- 当前项目以普通 K 线和通用策略为主线，不要新增依赖旧缠论结构的功能。
- `src/tradingview_zy/config.py` 是本地配置，通常不提交。
- 修改交易所或 Web 图表接口时，同时检查周期映射、默认标的、时区和数据字段。
- 修改策略协议时，要同步检查选股、监控、Web 任务和测试。
- 修改数据库模型时，要考虑 SQLite 和 MySQL 两种模式。
- 对外部接口、Web 参数、JSON 配置做边界校验。
- 策略信号不等于交易订单，实盘前必须经过风控转换。
- 不要直接修改 TradingView charting library 源码，优先在外层页面和 datafeed 适配。
- 每次功能变更后至少跑相关测试；架构性变更跑全量测试。

## 16. 快速定位表

| 你想做什么 | 先看哪里 |
| --- | --- |
| 改 Web 启动 | `web/tradingview_zy_chart/app.py`、`windows_run.bat` |
| 改 TradingView K 线返回 | `web/tradingview_zy_chart/cl_app/__init__.py` 的 `/tv/history`、`src/tradingview_zy/web_payloads.py` |
| 改市场数据源 | `src/tradingview_zy/exchange/`、`src/tradingview_zy/config.py.demo` |
| 改自选组 | `src/tradingview_zy/zixuan.py`、`cl_app/__init__.py` 自选路由 |
| 写选股策略 | `src/tradingview_zy/strategies/`、`selection.py`、`docs/custom-strategy-integration.md` |
| 写监控策略 | `monitoring.py`、`cl_app/alert_tasks.py` |
| 改监控页面 | `templates/alert.html`、`static/js/alert.js`、`cl_app/alert_tasks.py` |
| 改回测 | `src/tradingview_zy/backtesting/` |
| 改实盘交易 | `src/tradingview_zy/trader/`、对应 `exchange.order()` |
| 改数据库 | `src/tradingview_zy/db.py` |
| 改定时任务 | `web/tradingview_zy_chart/cl_app/*_tasks.py`、`script/crontab/` |
| 查旧资料 | `archive/` 或只读旧版目录 |

## 17. 最小二次开发闭环

一次比较稳妥的二次开发闭环如下：

1. 明确你要改的是行情源、策略、Web、回测还是交易。
2. 找到上表对应入口。
3. 写一个最小测试或最小脚本复现目标行为。
4. 做最小代码修改。
5. 跑相关测试。
6. 如涉及 Web，实际启动服务并在浏览器验证。
7. 更新文档或示例。
8. 提交代码。

这样做可以避免把 Web、策略、交易所、数据库混在一起改，也能避免历史归档逻辑重新污染当前主线。
