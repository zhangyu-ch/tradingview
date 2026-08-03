# 进度日志

## 会话：2026-08-03

### 阶段 1：建立基线与问题台账
- **状态：** complete
- **开始时间：** 2026-08-03T11:13:08+00:00
- 执行的操作：
  - 解压 planning-with-files 技能并读取 `SKILL.md`。
  - 解压本地 TradingView 仓库。
  - 保存原始问题清单到 `audit/`。
  - 创建 `task_plan.md`、`findings.md`、`progress.md`。
  - 通过 GitHub App 校验远程默认分支与最新提交。
  - 尝试 `git clone`，因容器 DNS 无法解析 GitHub 失败；改用 GitHub App。
  - 解析 81 条问题并生成 `audit/remediation_state.json` 与 `remediation_report.md`。
  - 执行完整与可运行子集基线测试；确定离线分层验证策略。
- 创建/修改的文件：
  - `task_plan.md`
  - `findings.md`
  - `progress.md`
  - `audit/tradingview_current_open_issues_v1.md`
  - `audit/remediation_state.json`
  - `audit/source_sha256.txt`
  - `remediation_report.md`
  - `script/remediation/parse_issue_report.py`

## 测试结果
| 测试 | 输入 | 预期结果 | 实际结果 | 状态 |
|------|------|---------|---------|------|
| ZIP 完整性 | 两个用户上传 ZIP | 可成功列出并解压 | 成功 | 通过 |
| 完整 pytest 基线 | `pytest -q` | 收集并运行 | 缺 `empyrical`、`werkzeug`，收集阶段中止 | 环境阻断 |
| 可运行测试子集 | 5 个测试文件 | 通过可用模块 | 34 通过；9 个因缺 `tzlocal`/`pinyin` 失败 | 部分通过 |

## 错误日志
| 时间戳 | 错误 | 尝试次数 | 解决方案 |
|--------|------|---------|---------|
| 2026-08-03T11:13:08+00:00 | 仓库 ZIP 不含 `.git` | 1 | 初始化新的本地仓库并建立导入基线 |

| 2026-08-03T11:15:04+00:00 | `git clone` 无法解析 github.com | 1 | 改用 GitHub App 获取远程信息 |

| 2026-08-03T11:18:57+00:00 | 在线安装依赖 / Python 3.11 失败（DNS） | 3 | 改用现有 Python 3.13 与依赖隔离测试 |

## 五问重启检查
| 问题 | 答案 |
|------|------|
| 我在哪里？ | 阶段 2：处理问题 1–10 |
| 我要去哪里？ | 顺序完成 81 条问题、9 个归档及最终全量交付 |
| 目标是什么？ | 每条问题独立提交、可验证、可追溯 |
| 我学到了什么？ | 见 findings.md |
| 我做了什么？ | 见上方记录 |

### 问题 01：CR-02
- **状态：** complete
- **完成时间：** 2026-08-03T11:22:19+00:00
- 验证结论：问题存在；认证/会话主体已安全，但设置页仍泄露 Secret。
- 修复：停止回显/日志泄露，增加留空不改与 no-store。
- 专项测试：`tests/test_cr02_settings_secret.py`，3 passed。
- 提交：`fix(CR-02): stop echoing saved Feishu secrets`。

### 问题 02：NEW-02
- **状态：** complete
- **完成时间：** 2026-08-03T11:24:10+00:00
- 验证结论：本地 ZIP 已无危险临时工作流/分片；远程固定点仍是历史来源。
- 修复：新增只读仓库卫生门禁和恶意 fixture 防回归测试。
- 专项测试：`tests/test_new02_repository_hygiene.py`，3 passed。
- 提交：`fix(NEW-02): add repository hygiene gate`。

### 问题 03：NEW-03
- **状态：** complete
- **完成时间：** 2026-08-03T11:30:00+00:00
- 验证结论：问题存在；本地依赖入口漂移并锁到 chardet 7.1.0 / websockets 16.0，Python 声明也超出本地轮子支持范围。
- 修复：pyproject 成为唯一依赖源，requirements 仅转发；锁定 Python 3.11 与 websockets 13.1，移除 chardet；增加依赖契约门禁。
- 专项测试：`tests/test_new03_dependency_contract.py`，2 passed；依赖契约脚本通过。
- 环境限制：离线容器没有 Python 3.11，`uv lock --check --offline` 无法启动目标解释器。
- 提交：`fix(NEW-03): unify dependency sources and compatibility bounds`。

### 问题 04：NEW-04
- **状态：** complete
- **完成时间：** 2026-08-03T11:34:00+00:00
- 验证结论：问题存在；naive K 线在市场本地化前被转换为 epoch。
- 修复：新增市场时区规范化并确保 history 的所有时间运算都在规范化后执行。
- 专项测试：`tests/test_web_payloads.py`，6 passed。
- 提交：`fix(NEW-04): normalize market time before history filtering`。

### 问题 05：NEW-05
- **状态：** complete（本地不存在，已加防回归）
- **完成时间：** 2026-08-03T11:38:00+00:00
- 验证结论：本地无 FIFO lot 会计模块或调用，确切半提交回归不存在。
- 修复：增加 AST 门禁，未来若引入 FIFO 关闭路径，必须先完成结算校验再消费 lot。
- 专项测试：`tests/test_new05_fifo_atomicity_guard.py`，3 passed。
- 提交：`test(NEW-05): guard FIFO settlement atomicity`。

### 问题 06：NX-20
- **状态：** complete
- **完成时间：** 2026-08-03T11:45:00+00:00
- 验证结论：问题存在于 4 个 TDX-ExHq 构造器。
- 修复：3 次尝试、12 秒总 deadline、受剩余预算约束的 SDK connect timeout、统一 ProviderUnavailableError。
- 专项测试：`tests/test_nx20_tdx_bounded_retry.py`，3 passed。
- 提交：`fix(NX-20): bound TDX ExHq constructor retries`。

### 问题 07：RV-08
- **状态：** complete（共享修复已复验）
- **完成时间：** 2026-08-03T11:49:00+00:00
- 验证结论：CR-02 后原 Secret 回显/控制台泄露已不存在。
- 修复：新增独立 Secret 暴露扫描器、脆弱 fixture 与 CI 门禁。
- 专项测试：`tests/test_rv08_secret_exposure_guard.py`，2 passed。
- 提交：`test(RV-08): enforce no-secret-echo settings contract`。

### 问题 08：HI-13
- **状态：** complete
- **完成时间：** 2026-08-03T11:56:00+00:00
- 验证结论：合约/现货均存在单行 -2 越界与包含端点分页停滞风险。
- 修复：共享严格游标分页器，0/1/N 缓存安全、±1ms 推进、去重、无进展与最大页数保护。
- 专项测试：`tests/test_hi13_binance_pagination.py`，5 passed。
- 提交：`fix(HI-13): make Binance pagination strictly progressive`。

### 问题 09：HI-14
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：构造即启动非 daemon 线程、普通 list/字典跨线程共享、无 join 关闭和参数化 singleton 均存在。
- 修复：显式/惰性 ManagedWorker 生命周期，daemon + Event + join；Queue、RLock、行情快照与确定性 API 释放。
- 专项测试：`tests/test_hi14_tq_lifecycle.py`，3 passed；compileall、危险模式 grep、diff 检查通过。
- 环境限制：容器缺 `tzlocal`/`tqsdk`，未运行真实 TQ SDK 联调。
- 提交：`fix(HI-14): make TQ worker lifecycle deterministic`。

### 问题 10：CR-05
- **状态：** complete（通过移除不支持能力）
- **完成时间：** 2026-08-03
- 验证结论：标准工厂未接入 CTP，但失效行情/交易实现、OpenCTP 依赖和配置声明仍在，外部可直接导入。
- 修复：删除 CTP 运行时实现与依赖/配置；工厂在导入和缓存前明确拒绝 ctp；补不支持能力文档。
- 专项测试：`tests/test_cr05_ctp_removed.py` + NEW-03 依赖契约，5 passed；依赖契约脚本通过。
- 提交：`fix(CR-05): remove unsupported CTP runtime`。

### 归档检查点 01（问题 001–010）
- **状态：** verified
- 文件：`/mnt/data/tradingview_remediation_issues_001-010.zip`
- SHA-256：`0c0b63c18b2ecd340553bad6555904c25bbf1c20dafef74c0236e948bd60359f`
- 验证：系统 unzip 后工作树干净；HEAD=`9b741486a84b9255cdf3ba1f53a4878ba5f8a68f`；10 个问题标签；`git fsck --full` 通过。

### 问题 11：CR-04
- **状态：** complete（通过移除不支持能力）
- **完成时间：** 2026-08-03
- 验证结论：无内置入口但危险 QMT 实盘类可直接导入；未定义 price、硬编码配置和真实失败模拟成功均存在。
- 修复：删除 QMT 实盘 trader，保留 QMT 行情；文档化恢复订单执行所需的状态机与沙箱门槛。
- 专项测试：`tests/test_cr04_qmt_trader_removed.py` 与相邻移除门禁，6 passed。
- 提交：`fix(CR-04): remove unsafe QMT live trader`。

### 问题 12：HI-06
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：全部写请求缺少 CSRF token/来源校验，提醒删除仍使用 GET。
- 修复：统一会话 CSRF token + 同源校验；登录/登出轮换；前端四种提交机制自动带 token；删除改 POST。
- 专项测试：`tests/test_hi06_csrf.py` + `tests/test_web_security.py`，14 passed、3 skipped（离线镜像缺完整 Web 依赖）；compileall 与 diff 检查通过。
- 提交：`fix(HI-06): enforce CSRF on state-changing requests`。

### 问题 13：CR-03
- **状态：** complete（通过移除未验收实盘订单执行能力）
- **完成时间：** 2026-08-03
- 验证结论：多个 provider 把提交/单次查询/本地状态当最终成交，缺少统一 Order/Fill、幂等与重启对账。
- 修复：删除 live trader；所有 order/cancel 统一 fail-closed；移除 IB 下单队列/worker；保留行情与回测。
- 专项测试：CR-03 与相邻下线/生命周期测试共 13 passed；运行树危险下单调用扫描、compileall、diff 检查通过。
- 提交：`fix(CR-03): disable unreconciled live trading`。

### 问题 14：ME-24
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：环境脚本与 pyproject 版本约束漂移，使用 telnetlib，失败后仍打印环境OK。
- 修复：读取 pyproject 单一版本约束；有限 socket/Redis/MySQL 超时；结构化 OK/DEGRADED/FAILED 和可靠退出码。
- 专项测试：`tests/test_me24_check_env.py`，5 passed；当前 Python 3.13 真实执行正确返回失败。
- 提交：`fix(ME-24): align environment checks with project metadata`。

### 问题 15：NEW-06
- **状态：** complete（本地不存在，已加防回归）
- **完成时间：** 2026-08-03
- 验证结论：本地没有 MarketRegistry/Capability，确切的 DB 能力过报不存在；底层主数据/板块方法仍未实现。
- 修复：新增能力边界文档和未来 registry 的 DB_CAPABILITIES AST 门禁。
- 专项测试：`tests/test_new06_db_capability_guard.py`，4 passed。
- 提交：`test(NEW-06): guard DB provider capability claims`。

### 问题 16：HI-01
- **状态：** complete（共享修复已复验）
- **完成时间：** 2026-08-03
- 验证结论：CR-03 后 TraderFutures 已不存在，旧 TypeError 与平多误记均不可达。
- 修复：增加独立移除/危险构造防回归门禁。
- 专项测试：HI-01 + CR-03 共 7 passed。
- 提交：`test(HI-01): guard removed futures trader`。

### 问题 17：ME-06
- **状态：** complete
- **完成时间：** 2026-08-03
- 修复：导出使用 BytesIO；导入流式限额解析，增加请求体/行数/行长度/UTF-8/.txt 校验。
- 专项测试：`tests/test_me06_watchlist_transfer.py`，4 passed。
- 提交：`fix(ME-06): isolate and bound watchlist transfers`。

### 问题 18：ME-16
- **状态：** complete
- **完成时间：** 2026-08-03
- 修复：统一有限 IB Redis RPC、明确 TimeoutError、响应键清理和 worker TTL。
- 专项测试：`tests/test_me16_ib_rpc_timeout.py`，4 passed。
- 提交：`fix(ME-16): bound IB Redis RPC waits`。

### 问题 19：ME-05
- **状态：** complete
- **完成时间：** 2026-08-03
- 修复：create_app 改用零副作用静态市场元数据，provider 只在实际请求时构造。
- 专项测试：`tests/test_me05_lazy_web_startup.py`，3 passed。
- 提交：`fix(ME-05): remove provider construction from app startup`。

### 问题 20：MX-01
- **状态：** complete（通过移除废弃能力）
- **完成时间：** 2026-08-03
- 修复：删除破裂钉钉配置/发送接口和死注释，保留飞书并补通道准入文档。
- 专项测试：`tests/test_mx01_dingding_removed.py`，3 passed。
- 提交：`fix(MX-01): remove broken DingTalk integration`。

### 归档检查点 02（问题 011–020）
- **状态：** verified
- 文件：`/mnt/data/tradingview_remediation_issues_011-020.zip`
- SHA-256：`0fabf6142b1a4878249e34c8f9795751662abd48f4edde3c356c560336e3a4f8`
- 验证：重新解压后工作树干净；HEAD=`3ba999384981bf0f2ebbd67a9622d344ca9df775`；问题 011–020 标签齐全；`git fsck --full` 通过。

### 问题 21：MX-06
- **状态：** complete
- **完成时间：** 2026-08-03
- 修复：删除 db.py 可执行 demo/main 测试写入，保留生产 DB 单例。
- 专项测试：`tests/test_mx06_db_module_safe.py`，3 passed。
- 提交：`fix(MX-06): remove executable database demo writes`。

### 问题 22：MX-02
- **状态：** complete（通过移除不支持能力）
- **完成时间：** 2026-08-03
- 验证结论：配置宣称支持 ZB，工厂从未注册，孤立实现还关闭 TLS 校验。
- 修复：删除 ZB 适配器/配置密钥/支持声明；旧配置在导入和缓存前 fail-closed；补不支持 provider 文档。
- 专项测试：`tests/test_mx02_zb_removed.py` 与相邻 provider 下线测试共 7 passed。
- 提交：`fix(MX-02): remove unsupported ZB provider`。

### 问题 23：MX-04
- **状态：** complete
- **完成时间：** 2026-08-03
- 修复：ExchangeDB.now_trading 改为严格 `bool` 并明确返回 False，消除 Python/JSON/前端三态分叉。
- 专项测试：`tests/test_mx04_exchange_db_trading_state.py`，3 passed；隔离动态调用、AST、compileall 通过。
- 提交：`fix(MX-04): make DB trading state explicit`。

### 问题 24：MX-05
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：两处 `setInterval(ZiXuan.stocks_update_rate(), 30000)` 确认把函数返回值当回调，轮询不会持续执行。
- 修复：抽取可重复启动/停止的涨跌幅定时器 helper；启动前清理旧 timer，立即刷新一次，再传入真实函数回调。
- 专项测试：`tests/test_mx05_rate_timer.py`，3 passed；Node fake timer 动态验证和全部内联脚本语法编译通过。
- 首轮测试错误：2 passed、1 failed；失败来自测试脚本跨 `<script>` 标签提取，不是产品代码语法错误，已改用逐内联脚本编译。
- 提交：`fix(MX-05): schedule watchlist rate refresh correctly`。

### 问题 25：MX-17
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：TDX 冷启动/重置选优串行遍历全部候选，且无总体 deadline；节点缓存也永久有效。
- 修复：新增并发有界 TDX 节点选择器，最多 16 个 daemon worker、3 秒总 deadline、最小成功数与明确失败；全部 TDX 节点缓存增加 6 小时 TTL。
- 专项测试：`tests/test_mx17_tdx_node_selection.py` 6 passed，NX-20 相邻测试 3 passed；并发度、最快节点、挂起节点、失败解释和 TTL 契约均通过。
- 提交：`fix(MX-17): bound and parallelize TDX node selection`。

### 问题 26：NX-08
- **状态：** complete
- **完成时间：** 2026-08-03
- 最小复现：输入 `uids=["uid-a"]`，调用后变为 `["uid-a", "clear"]`，问题确认存在。
- 修复：在局部 set 副本中补 `clear`，不再原地修改调用方列表。
- 专项测试：`tests/test_nx08_position_close_profit.py` 3 passed；覆盖指定 uid、clear fallback、无记录异常及重复调用。
- 相邻套件限制：`test_backtesting_base_generic.py` 因缺失 `empyrical` 无法收集；compileall 与 diff 检查通过。
- 提交：`fix(NX-08): keep close-profit queries side-effect free`。

### 问题 27：NX-03
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：飞书配置读取直接引用全局市场/default 字典并原地写入 user_id，问题存在。
- 修复：先选择来源映射，再返回 `dict(source)` 副本并只修改副本；补充明确类型契约。
- 专项测试：`tests/test_nx03_feishu_config_copy.py`，3 passed；覆盖市场/default、返回值再修改、跨市场调用和 DB override。
- 提交：`fix(NX-03): avoid mutating global Feishu config`。

### 问题 28：NX-22
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：db.py import 时执行进程级 `warnings.filterwarnings("ignore")`，问题存在。
- 修复：删除无差别 warnings import/过滤；保留其他模块已有的局部、精确 warning 上下文。
- 专项、相邻与报告测试：6 passed；隔离子进程真实执行 DB/SQLAlchemy/SQLite 导入后，调用方 UserWarning=error 策略仍生效（仅为容器缺失的 tzlocal 提供 UTC stub）。
- 首轮动态导入被容器缺失 `tzlocal` 阻断；测试改为只桩住纯时区查询，实际 DB 模块、SQLAlchemy 与 SQLite 初始化仍真实执行。
- 提交：`fix(NX-22): preserve process warning policy on DB import`。

### 问题 29：NX-21
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：MySQL DSN 直接插值用户名/密码/数据库，特殊字符会破坏解析，问题存在。
- 修复：新增 `build_mysql_url()`，使用 SQLAlchemy `URL.create` 结构化构造并由默认渲染隐藏密码。
- 专项测试：`tests/test_nx21_mysql_url.py`，3 passed；特殊字符完整 round-trip、默认脱敏和构造器无 f-string DSN 均通过。
- 提交：`fix(NX-21): build MySQL URLs without credential interpolation`。

### 问题 30：NX-23
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：ExchangeDB 可读取持久化 K 线，但 all_stocks 固定为空，导致 DB provider 的搜索、导入和全市场选股静默失效。
- 修复：按市场枚举 K 线分区并读取 DISTINCT code；映射到既有 `{code, name}` 目录契约，同时明确该目录不是权威 security master。
- 专项、相邻、能力边界与报告测试：17 passed；内存已有表发现、真实项目 SQLite 插入→ExchangeDB 端到端路径和 NEW-06 防过报门禁均通过。
- 首轮组合回归暴露 NEW-06 旧门禁把“持久化代码目录”误等同于“权威证券主数据”；已调整为允许 code/name=code 的兼容目录，同时继续禁止板块能力与 `SECURITY_MASTER`/`PLATES` 过报。
- 提交：`fix(NX-23): discover DB-backed instrument universe`。


### 归档检查点 03（问题 021–030）
- **状态：** verified
- 文件：`/mnt/data/tradingview_remediation_issues_021-030.zip`
- 校验和：见同名 `.sha256` sidecar。
- 验证：使用系统 `unzip` 重新解压后工作树干净；问题 021–030 标签逐一存在；`git fsck --full` 通过。
