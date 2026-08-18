# tradingview_zy

`tradingview_zy` 是一个多市场行情、TradingView 图表、选股监控和回测工具。

本仓库已从原缠论分析系统迁移为多市场行情、研究、监控与回测工具。运行路径中不再保留缠论计算、分型、笔、线段、中枢、买卖点、背驰等模块。历史缠论源码已压缩归档到 `archive/chanlun-runtime-source.zip`，相关文档已迁移到 `archive/docs/`。

## 当前保留能力

- 多市场 provider 适配、K 线和有界 Tick 查询。
- TradingView UDF 风格基础行情接口。
- 自选股、注册式选股任务和注册式监控任务。
- 版本化策略信号协议与通用回测框架。
- 部分 provider 的只读账户余额和持仓查询。

内置 provider **不声明实盘下单能力**。所有 `order()` 入口继续 fail-closed，直到
持久化 Order/Fill 状态机、券商对账和 sandbox 验收完成。详见
[`docs/live-trading-disabled.md`](docs/live-trading-disabled.md)。

## 支持范围

市场、默认 provider、TradingView session 和精确能力由 `MarketRegistry` 统一声明。
自动生成且由 CI 校验的完整矩阵见
[`docs/provider-support-matrix.md`](docs/provider-support-matrix.md)。不要根据适配器上
“存在某个方法”推断能力；只有矩阵中声明的 capability 才属于标准 `get_exchange()`
契约。

旧 JoinQuant 研究代码已经从活跃根目录移除，并以
`archive/joinquant-legacy.zip` 留存。它依赖专有 `jqdata` 环境和已移除的 `cl` 包，
不是当前安装或运行入口。

## 文档导航

- Provider 支持范围：[`docs/provider-support-matrix.md`](docs/provider-support-matrix.md)（由 Registry 生成）和 [`docs/provider-capabilities.md`](docs/provider-capabilities.md)。
- 策略协议：[`docs/strategy-protocol.md`](docs/strategy-protocol.md) 和 [`docs/strategy-protocol-boundary.md`](docs/strategy-protocol-boundary.md)。
- 安全边界：[`docs/live-trading-disabled.md`](docs/live-trading-disabled.md)、[`docs/secrets.md`](docs/secrets.md) 和 [`docs/unsupported-providers.md`](docs/unsupported-providers.md)。
- 运维与治理：[`docs/branch-governance.md`](docs/branch-governance.md)、[`docs/quality-gates.md`](docs/quality-gates.md)、[`docs/supply-chain.md`](docs/supply-chain.md) 和 [`docs/messaging-channels.md`](docs/messaging-channels.md)。
- 图表库维护：[`charting_library_patches/README.md`](charting_library_patches/README.md) 和 [`FOOTPRINT_RENDERING_PLAN.md`](FOOTPRINT_RENDERING_PLAN.md)。

`archive/` 和 `audit/` 保存迁移、研究和审计证据，不是当前安装、API 或能力说明。

## 安装与启动

项目只支持 Python 3.11。依赖解析、安装脚本和 CI 的审计基线固定为
`uv 0.10.0`，`uv.lock` 是唯一受支持的依赖解析结果。以下命令都应在仓库根目录执行。

### Windows

先安装受信任的 Python 3.11 和 PATH 中的 `uv 0.10.0`，然后运行：

```bat
windows_install.bat
windows_run.bat
```

`windows_install.bat` 创建或复用 `.venv`、执行 `uv sync --locked`、首次复制配置并运行
`check_env.py`。`windows_run.bat` 只负责调用 Web 启动命令并自动打开浏览器；它接受已有环境中的
uv 0.10 或 0.11，但内部使用默认的 `uv run`，因此可能按 uv 行为同步环境。要遵守锁文件审查
边界，应先运行 `windows_install.bat` 或显式执行 `uv sync --locked`，不要把 `windows_run.bat`
当成锁定安装入口。

监控调度器必须在另一个终端单独运行：

```bat
uv run --locked python web\tradingview_zy_chart\scheduler.py
```

### macOS/Linux（Bash）

```bash
uv --version  # 必须是 uv 0.10.0
uv venv --python=3.11 .venv
uv sync --locked
cp src/tradingview_zy/config.py.demo src/tradingview_zy/config.py
uv run --locked python check_env.py
```

启动 Web；`nobrowser` 表示不自动打开浏览器：

```bash
uv run --locked python web/tradingview_zy_chart/app.py nobrowser
```

监控调度器必须在另一个终端单独运行：

```bash
uv run --locked python web/tradingview_zy_chart/scheduler.py
```

### 兼容配置说明

`config.py.demo` 的默认 `DATA_PATH = ".chanlun_pro"` 和
`DB_DATABASE = "chanlun_klines"` 为兼容已有数据目录和数据库而保留；这些名称不代表
当前运行路径仍包含 Chanlun。模板中的 AI 配置字段同样只作为旧私有配置和 Secret
inventory 的兼容残留，当前 Web 和工具链不提供 AI 分析入口。

Web worker 不再启动 APScheduler。多个 Web worker 可以共享同一数据库；监控任务只由
上述独立进程执行。调度进程使用 `DATA_PATH/scheduler/leader.lock` 防止本机重复启动，
第二个实例会以退出码 2 结束。配置保存后最多等待
`SCHEDULER_RECONCILE_SECONDS`（默认 30 秒）同步到实际任务。`/jobs` 页面读取调度进程
写入的原子状态快照；快照缺失或损坏时显示为空，不会在 Web 进程补启动调度器。

## 供应链证据

依赖、仓库内 wheel、SBOM、许可证和漏洞扫描的治理方式见
[`docs/supply-chain.md`](docs/supply-chain.md)。仓库不提供可绕过锁文件的
`requirements.txt`；手工安装、`windows_install.bat` 和 Tests workflow 的六个安装 job 都执行
`uv sync --locked`。`windows_run.bat` 是已有环境的启动入口，但它调用默认 `uv run`，可能同步
环境；需要可审计的锁文件状态时，应先用 `uv sync --locked` 完成安装。

本地复核：

```bash
uv run --locked python script/remediation/check_dependency_contract.py
uv run --locked python script/remediation/check_supply_chain.py
uv run --locked python script/remediation/generate_supply_chain_artifacts.py --check
```

## 业务凭据与轮换

数据库、行情、券商和消息平台的业务凭据不得直接写入 Python 配置。
配置项只保存 `env://`、`managed://`、`file://` 或 `keyring://` 引用；
引用格式、平台权限边界、飞书轮换和旧配置迁移见
[`docs/secrets.md`](docs/secrets.md)。Secret inventory 暂时保留旧 AI 字段以约束私有配置迁移，
这不表示当前提供 AI 分析功能。

本地复核：

```bash
uv run --locked python script/remediation/check_secret_references.py
uv run --locked python script/remediation/check_secret_exposure.py
```

## Web 安全配置

### 本机单机使用

默认 `WEB_HOST = "127.0.0.1"`。仅本机访问时，`LOGIN_PWD` 和
`LOGIN_PWD_HASH` 可以都留空，浏览器仍会自动登录，页面操作与原来一致。

`WEB_SECRET_KEY` 不是登录密码，而是 Flask 用来签名会话 Cookie 的随机密钥。
通常无需手工选择：留空时，第一次启动会自动生成高强度随机值并保存到：

```text
DATA_PATH/web_secret_key
```

后续启动会复用该文件。不要提交或共享它；删除或更换后只会使已有登录 Cookie
失效，不会删除行情、图表、任务或数据库数据。

### 局域网、公网或反向代理使用

当服务直接监听 `0.0.0.0`、局域网 IP 或公网 IP 时，必须配置登录密码，否则服务
会拒绝启动。即使服务只监听 `127.0.0.1`，只要通过 Nginx 等代理暴露给其他机器，
也应配置密码。

推荐保存密码哈希而不是明文。先生成哈希：

```bash
uv run --locked python -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Web 登录密码: ')))"
```

将输出复制到私有的 `src/tradingview_zy/config.py`：

```python
WEB_HOST = "0.0.0.0"
LOGIN_PWD = ""
LOGIN_PWD_HASH = "这里粘贴上一步输出"
```

旧的明文 `LOGIN_PWD` 继续兼容，但不推荐。经 HTTPS 反向代理访问时设置：

```python
WEB_COOKIE_SECURE = True
```

容器、多实例或只读数据目录部署时，各实例必须使用同一个稳定会话密钥。可生成并
通过环境变量注入：

```bash
uv run --locked python -c "import secrets; print(secrets.token_urlsafe(48))"
export TRADINGVIEW_ZY_WEB_SECRET_KEY="上一步输出"
```

PowerShell 中使用：

```powershell
$env:TRADINGVIEW_ZY_WEB_SECRET_KEY = "上一步输出"
```

也可使用 `TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH` 或
`TRADINGVIEW_ZY_LOGIN_PASSWORD` 注入登录凭据。默认记住登录 30 天，失败登录会被
短时限速。

## 自定义策略

选股、监控、回测和交易信号统一面向普通 K 线数据。策略基类和信号对象见
`src/tradingview_zy/strategies/base.py`；信号格式和可选的 paper/backtest 桥接边界分别见
[`docs/strategy-protocol.md`](docs/strategy-protocol.md) 和
[`docs/strategy-protocol-boundary.md`](docs/strategy-protocol-boundary.md)。

### 监控策略注册

监控页面不再接受任意 `module:ClassName`。先在服务器端私有配置
`src/tradingview_zy/config.py` 中注册允许使用的策略：

```python
ALERT_STRATEGIES = {
    "price_breakout": {
        "name": "价格突破监控",
        "strategy_path": "my_strategies.breakout:BreakoutStrategy",
        "strategy_kwargs": {"window": 20, "threshold": 0.5},
        "allowed_kwargs": ["window", "threshold"],
        "strategy_kwargs_schema": {
            "window": "int",
            "threshold": "number",
        },
        "description": "收盘价突破窗口高点时产生监控信号",
    }
}
```

重启 Web 后，“新增监控”页面会显示策略下拉框。页面仍可编辑 JSON 参数，但只能
覆盖 `allowed_kwargs` 中的字段，并按 `strategy_kwargs_schema` 校验类型；页面不会
再接收或保存 Python 导入路径。

已有监控任务如果保存的是旧 `strategy_path`，只要该路径与 `ALERT_STRATEGIES`
中的某项完全一致，且旧任务使用的参数已列入 `allowed_kwargs`，系统会自动映射到
对应的策略 ID 并继续运行。未登记或参数未获准的旧任务会被安全禁用，日志和编辑
页面会提示先完成注册。这一变化不影响行情图表、自选组、图表布局或普通页面交互。

`allowed_kwargs` 只应开放窗口、阈值等普通业务参数；不要开放模块名、文件路径、
系统命令或可执行回调等高风险参数。注册表中的模块路径和策略类仍属于服务端可信
配置，修改后需要重启 Web。

### 选股策略注册

选股页面继续使用 `XUANGU_STRATEGIES`，交互方式不变。配置结构兼容上述注册表；
加载器会在实例化前确认目标是类且定义了 `run(context)`，并应用相同的参数白名单
和类型校验：

```python
XUANGU_STRATEGIES = {
    "demo": {
        "name": "示例选股",
        "strategy_path": "my_strategies.demo:DemoStrategy",
        "strategy_kwargs": {"window": 20},
        "allowed_kwargs": ["window"],
        "strategy_kwargs_schema": {"window": "int"},
        "task_memo": "示例",
        "frequency_num": 1,
        "frequency_memo": "单周期",
    }
}
```
