# 发现与决策

## 需求
- 用户要求按问题清单顺序逐条验证、修复、验证修复、记录，并为每条问题建立独立本地 Git 提交。
- 每完成 10 条问题，压缩完整仓库（含 `.git`）交付留存。
- 本地 ZIP 是主代码；远程 GitHub 仓库只用于校正和补充。

## 研究发现
- 上传的仓库 ZIP 根目录直接包含项目文件，但不包含 `.git`。
- 原始问题清单共 81 条，来源固定点为远程 `master` 提交 `3488462529c6ec052192eb41d1a6b74c5718c58f`（2026-08-01 12:03:48Z）；GitHub 当前默认分支仍停在该提交。
- 本地 ZIP 的项目文件时间为 2026-08-02，且 `pyproject.toml` 与远程固定点描述不一致（例如本地重新包含 `chardet`、Python 约束为 `>=3.11`），说明本地 ZIP 是独立工作副本，必须以本地实际代码逐条重验。

## 测试环境发现
- 容器只有 Python 3.13.5；仓库 `.python-version` 指定 3.11。
- 完整测试收集被缺失的 `empyrical`、`werkzeug` 阻断；可执行子集得到 34 通过、9 个因 `tzlocal`/`pinyin` 缺失而失败。
- 容器 DNS 无法解析 GitHub 与 PyPI，无法在线补依赖或下载 Python 3.11。
- 后续采用分层验证：现有可运行 pytest + 新增依赖隔离单元测试 + AST/源码契约测试 + `compileall`；涉及真实 SDK/账户的验证限制逐条记录。

## 技术决策
| 决策 | 理由 |
|------|------|
| 新建本地 Git 仓库并使用 `main` | 保留本轮逐问题提交历史，同时不向远程推送 |
| 为问题清单生成结构化 JSON 台账 | 支持严格顺序、自动检查遗漏和报告生成 |
| 测试优先使用离线单元/契约测试 | 避免真实交易、网络和第三方账户副作用 |
| 不在产品代码中加入仅为当前容器服务的依赖伪实现 | 防止测试环境问题污染生产语义 |

## 遇到的问题
| 问题 | 解决方案 |
|------|---------|
| 本地 ZIP 无 Git 元数据 | 建立导入基线提交并记录来源文件 SHA256 |
| 容器无法解析 github.com，`git clone` 失败 | 使用已连接的 GitHub App 读取远程元数据和指定文件；本地 ZIP 继续作为主基线 |

## 资源
- `audit/tradingview_current_open_issues_v1.md`：原始问题清单。
- `/mnt/data/work/planning-with-files/SKILL.md`：执行规范。

## 视觉/浏览器发现
- GitHub App 校验：仓库 `zhangyu-ch/tradingview` 的默认分支为 `master`，最新提交为 `3488462529c6ec052192eb41d1a6b74c5718c58f`。

---
*每执行2次查看/浏览器/搜索操作后更新此文件*

## NEW-03 依赖契约复核
- 本地 `pyproject.toml` 重新把 `chardet>=5.2.0` 声明为直接依赖，并未约束 `websockets`；本地 `uv.lock` 因而锁定 `chardet 7.1.0` 与 `websockets 16.0`。
- 本地 `requirements.txt` 又维护一套宽松依赖清单，构成第二个人工维护入口。
- 远程固定点的 `pyproject.toml` 已采用 `requires-python = ">=3.11,<3.12"`、移除直接 `chardet`、增加 `websockets>=13.1,<14`；远程锁文件对应 `websockets 13.1` 且无 `chardet` 根依赖。
- 本地 TA-Lib 供应方式仅包含 CPython 3.11 轮子；在声明支持 3.12+ 时，离线 `uv lock` 会明确报出不可满足，说明 Python 上界也是同一依赖契约的一部分。
- GitHub 代码搜索接口首次调用参数格式错误，修正后未返回锁文件片段；改用 `fetch_blob` 成功读取完整远程锁文件，不再重复搜索。

## NEW-05 本地复核
- 用户提供的本地 ZIP 没有报告固定点中的 `backtesting/accounting.py`，`POSITION` 也没有 `lots` 字段；全仓不存在 `consume_fifo_lots` / `close_settlement` 调用，因此“FIFO lot 先消费后校验”的确切回归不在本地代码中。
- 当前本地回测仍采用聚合仓位模型；本条不应凭空引入一套未被调用的 FIFO 会计实现。处理方式是保存“不存在”的验证证据，并增加 AST 门禁：若未来重新引入这两个步骤，结算校验必须排在 lot 消费之前。

## HI-14 TQ 生命周期复核
- `ExchangeTq` 原构造函数会立即创建默认非 daemon 线程；即使调用者只想读取静态能力，也会产生线程与潜在 SDK 连接副作用。
- 原命令队列是普通 list，结果字典由工作线程与请求线程无锁读写；关闭只设置 `stop_thread` 并 sleep，不具备 join 或资源释放完成语义。
- 参数化类上的 `@fun.singleton` 会忽略后续 `use_simulate_account` 参数，属于与线程问题耦合的实例隔离缺陷。
- 修复采用独立 `ManagedWorker`：构造无副作用、首个订阅命令惰性启动、daemon + Event + join timeout；Queue/RLock/快照避免跨线程容器竞态，API 关闭集中化。
- 真实导入烟雾测试先后被容器缺失 `tzlocal` 与 `tqsdk` 阻断；未继续伪造完整 SDK，因为专项测试已覆盖本地生命周期核心，真实 SDK 行为在报告中保留限制。

## CR-05 CTP 能力边界复核
- 本地标准工厂虽不选择 `ctp`，但运行包仍保留 `exchange_ctp.py` 与 `trader_ctp.py`；外部脚本可以直接导入，不能把“无标准入口”当作根因修复。
- 静态复核确认 MarketCTP 缺少完整 Exchange 契约、历史 K 线为 pass、Tick 字段不兼容且时间调用错误；CTPTrader 有 4 组重复方法定义，后定义会覆盖前定义。
- 项目仍把 `openctp-ctp` 作为直接依赖并暴露 CTP 配置项，这会继续向维护者传达“内置支持”的错误信号。
- 本轮选择彻底移除不支持能力：删除运行时代码、依赖和配置声明；工厂为已移除 provider 提供明确 fail-closed 错误。历史 archive 文档保留作为历史证据，不是当前支持矩阵。
