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

项目只支持 Python 3.11，并固定使用 `uv 0.10.0`。`uv.lock` 是唯一受支持的依赖解析结果：

```bash
uv --version  # 必须是 uv 0.10.0
uv venv --python=3.11 .venv
uv sync --locked
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

启动独立监控调度进程（只运行一个实例）：

```bash
PYTHONPATH="$PWD/src" uv run python web/tradingview_zy_chart/scheduler.py
```

Web worker 不再启动 APScheduler。多个 Web worker 可以共享同一数据库；监控任务只由
上述独立进程执行。调度进程使用 `DATA_PATH/scheduler/leader.lock` 防止本机重复启动，
第二个实例会以退出码 2 结束。配置保存后最多等待
`SCHEDULER_RECONCILE_SECONDS`（默认 30 秒）同步到实际任务。`/jobs` 页面读取调度进程
写入的原子状态快照；快照缺失或损坏时显示为空，不会在 Web 进程补启动调度器。

## 供应链证据

依赖、仓库内 wheel、SBOM、许可证和漏洞扫描的治理方式见
[`docs/supply-chain.md`](docs/supply-chain.md)。仓库不提供可绕过锁文件的
`requirements.txt`；正常安装、Windows 脚本和 CI 都只执行 `uv sync --locked`。

本地复核：

```bash
python script/remediation/check_dependency_contract.py
python script/remediation/check_supply_chain.py
python script/remediation/generate_supply_chain_artifacts.py --check
```

## 业务凭据与轮换

数据库、交易所、券商、AI 和消息平台的业务凭据不得直接写入 Python 配置。
配置项只保存 `env://`、`managed://`、`file://` 或 `keyring://` 引用；
引用格式、私有文件权限、飞书轮换和旧配置迁移见
[`docs/secrets.md`](docs/secrets.md)。

本地复核：

```bash
python script/remediation/check_secret_references.py
python script/remediation/check_secret_exposure.py
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
PYTHONPATH="$PWD/src" uv run python -c \
  "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('Web 登录密码: ')))"
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
python -c "import secrets; print(secrets.token_urlsafe(48))"
export TRADINGVIEW_ZY_WEB_SECRET_KEY="上一步输出"
```

也可使用 `TRADINGVIEW_ZY_LOGIN_PASSWORD_HASH` 或
`TRADINGVIEW_ZY_LOGIN_PASSWORD` 注入登录凭据。默认记住登录 30 天，失败登录会被
短时限速。

## 自定义策略

选股、监控、回测和交易信号统一面向普通 K 线数据。策略基类和信号对象见
`src/tradingview_zy/strategies/base.py`。

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
