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
### 问题 31：NX-16
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：`/ticks` 原始请求没有代码数量、长度、去重、速率和 provider deadline 边界，问题存在。
- 修复：新增集中式输入契约、稳定去重、线程安全有界滑动窗口限流，以及带总 deadline/固定并发槽的 daemon provider 调用门；路由对非法、限流、异常、忙和超时返回明确 4xx/5xx。
- 专项及相邻测试：20 passed；覆盖解析边界、20 线程限流竞争、deadline、容量耗尽、槽位恢复和路由调用顺序。
- 真实同步 SDK 无法被 Python 强制取消；超时调用的残留线程数量由固定槽限制。
- 提交：`fix(NX-16): bound tick fanout and provider waits`。
### 问题 32：NX-14
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：chart/template 查询为空后直接解引用，且 chart ID 未统一校验，问题存在。
- 修复：新增轻量参数校验器；charts GET/DELETE/update 统一正整数 ID，study_templates GET/DELETE 统一名称契约；不存在资源返回稳定 404，非法参数返回 422。
- 专项与相邻测试：37 passed；成功响应结构和 CRLF 未回归。
- 提交：`fix(NX-14): return stable storage not-found responses`。
### 问题 33：NX-15
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：绘图保存异常、未确认结果和缺少必填字段都会返回 `status: ok`，问题存在。
- 修复：必填字段缺失返回 422；保存异常或非严格 True 返回带 request_id 的 500 并写关联日志；仅确认提交成功返回 ok。
- 专项与相邻测试：26 passed；覆盖成功、异常、False、None、缺参和 GET。
- 提交：`fix(NX-15): report drawing persistence failures`。
### 问题 34：RV-05
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：多进程路径允许 save_file=None，却在 worker 内无条件 `.split()`，问题存在。
- 修复：主进程先验证输出基路径并创建父目录；per-code 文件改用 pathlib 和安全代码名生成，禁止空路径/目录路径。
- 专项与相邻测试：18 passed；完整 ProcessPool 历史回测仍受容器缺失 empyrical/pyfolio 限制。
- 提交：`fix(RV-05): validate process backtest output paths`。
### 问题 35：RV-04
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：零收益与接近零的浮点噪声均被计入 loss_num，问题存在。
- 修复：新增 flat_num 和 1e-9 三分容差；结果表、汇总和总交易数展示持平，旧结果自动补字段。
- 专项与相邻测试：20 passed；真实 BackTestTrader 的 +/0/-、容差和旧数据兼容路径通过。
- 提交：`fix(RV-04): track breakeven trades separately`。
### 问题 36：RV-01
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：置顶重排遗漏 market，会同时移动跨市场同名组，问题存在。
- 修复：删除、目标 market/group 连续重排和插入使用单事务；已有标的重新置顶不再留下 position 空洞。
- 专项与相邻测试：7 passed；真实 SQLite 验证 A/HK 隔离、插入失败全回滚和重复置顶。
- 提交：`fix(RV-01): isolate watchlist top ordering by market`。
### 问题 37：RV-07
- **状态：** complete
- **完成时间：** 2026-08-03（会话恢复后重建）
- 验证结论：UDF/search/marks 路由直接 split/lower/int/枚举/字典索引，畸形参数可返回 500 并提前触发副作用。
- 修复：扩展共享 parser；8 个入口统一校验文本、market:code、周期、严格布尔、整数和时间区间；UDF 返回稳定 error，普通接口返回 422。
- 专项与相邻测试：77 passed；Web 主文件保持 CRLF，payload 时区契约未回归。
- 提交：`fix(RV-07): validate TradingView UDF request parameters`。

### 问题 38：ME-11
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：证券目录固定 2022-04-18、分钟 bar 按行序造时间、认证错误递归调用 `klines`，三项问题均存在。
- 修复：最近交易日历+有限数据发布回退+按市场日缓存；分钟请求直接读取并严格解析源 `time`；所有 BaoStock 查询采用最多 3 次、指数退避和总预算的有限重登录循环。
- 专项、相邻及报告测试：11 passed；fake SDK 动态执行真实 provider，验证时间缺口、毫秒、目录回退、缓存、认证耗尽与非认证错误。
- 当前容器没有 baostock 0.8.9 和在线服务；真实网络联调限制已记录，单次 SDK 内部阻塞也无法由调用方强制取消。
- 提交：`fix(ME-11): use BaoStock source timestamps and bounded retries`。

### 问题 39：HI-17
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：A 股/数字货币脚本 import 即连接并执行，A 股与数字货币含无界循环；美股 provider 顶层构造且请求 timeout=0；三者无持久化逐项状态、配置绑定和总体 deadline。
- 修复：新增共享可恢复批次引擎；三脚本改为无副作用 CLI；1,210/495 个代码和所有周期参数外置 JSON；原子 checkpoint、配置 digest、逐项审计、有限调用/批次 deadline、无进展/max_pages 和稳定退出码全部落地。
- 专项测试：`tests/test_hi17_sync_batch.py` 10 passed；与 ME-11/报告测试组合共 18 passed；compileall、CRLF 和 diff 检查通过。
- 提交：`fix(HI-17): make market sync batches recoverable`。

### 问题 40：ME-12
- **状态：** complete
- **完成时间：** 2026-08-03
- 验证结论：A 股目录在连接失败后递归自调用；六个 TDX Tick 路径存在当前价分母或无效前收价伪装；A/HK/US/FX 使用服务器本地时间、粗粒度时段或恒真返回，问题存在。
- 修复：A 股目录改为 3 次/12 秒有界节点恢复；新增统一涨跌幅函数，全部 TDX adapter 按前收价计算并用 `None` 表示不可用；Web/前端保留 unavailable；新增 SSE/HKEX/NYSE 2026 版本化日历与 DST/半日市，FX 改为 24x5 周界。
- 专项测试：`tests/test_me12_tdx_contracts.py` 11 passed；专项及相邻 TDX/Web/前端/报告组合 74 passed；排除既有配置/可选依赖/footprint 收集阻断后的广泛回归 235 passed、3 skipped；Node 语法、compileall、CRLF 与 diff 检查通过。
- 同进程扩展回归曾暴露专项测试对 singleton 包装函数的隔离不足；测试改为通过 `__wrapped__` 获取真实 provider 类型后恢复稳定，产品代码无需回退。
- 联调限制：无真实 pytdx/TDX 网络；现金日历当前覆盖 2026，FX venue 细节和期货品种时段留给 ME-30。未排除全量测试仍被基线缺少本地 config.py、环境缺 empyrical/pinyin 和既有 footprint 私有符号漂移阻断。
- 提交：`fix(ME-12): unify TDX quote and calendar contracts`。

## 2026-08-04 · 续作恢复：从第 41 条重新构建
- 检查发现 041–050 归档文件未挂载；GitHub 对 `80e346e` 和 `faa2227` 均返回 commit 不存在。
- 重新解压 `tradingview_remediation_issues_031-040.zip`，确认 `HEAD=9bad598`、工作树干净、问题 001–040 标签存在。

### 问题 41：ME-23（恢复重建）
- **状态：** complete
- 验证结论：20 个期货品种参数为无版本模块全局，交易器和利润计算直接读取，保存产物无日期/source/hash/snapshot，问题存在。
- 修复：迁移为带 schema、版本、生效区间、来源和 provenance 的 JSON package data；期货回测显式选择版本并在行情构造前校验日期/代码覆盖；交易器只使用注入快照，保存/加载校验 manifest 与 SHA-256。
- 验证：`tests/test_me23_futures_parameter_versions.py` 7 passed；与 NEW-05、RV-04、RV-05、NX-08 和报告统计组合共 30 passed；compileall、TOML 解析、CRLF 与 `git diff --check` 通过。
- 限制：参数为原仓库 2024-12-13 快照迁移，未连接期货公司/交易所二次核验；更早日期和未列品种按设计 fail-closed。
- 提交：`fix(ME-23): version futures backtest parameters`。


### 问题 42：HI-16（恢复重建）
- **状态：** complete
- 验证结论：K 线 CSV 直接覆盖、任意读错即删、隐式丢最后一行，以及通用/除权 pickle 缓存均可达，问题存在。
- 修复：统一同目录临时文件+fsync+原子 replace；损坏隔离、暂时 I/O 保留；K 线完成状态显式元数据；交易器状态改为 schema/hash JSON 白名单，legacy pickle 明确拒绝；xdxr 改原子 CSV。
- 专项及相邻测试：9 项 HI-16 专项、44 项组合通过；恶意 `__reduce__` payload 未执行，原子中断、权限抖动、损坏 JSON/CSV、路径穿越和真实 `BackTestTrader` 往返均通过。
- 首轮专项唯一失败来自测试在默认 `signal` 模式下错误期待初始现金；改为显式 `trade` 模式后通过，产品行为未修改。
- 限制：CSV 与 sidecar 非跨文件事务；进程间为 last-writer-wins；旧 pickle 不做自动迁移；完整 BackTest 产物 pickle 不属于本缓存路径。
- 提交：`fix(HI-16): make file caches atomic and non-executable`。


### 问题 43：ME-17（恢复重建）
- **状态：** complete
- 验证结论：QMT 读取隐式下载、end_date 全链路被忽略、响应无 schema/空值保护、类级目录缓存与订阅可变默认均存在。
- 修复：下载拆为显式 `download_klines`；默认读取使用 `get_market_data_ex` 并传递/二次执行 start/end；所有请求和 code->DataFrame/tick/detail 响应严格校验；目录缓存实例隔离，默认列表改 None。
- 专项及相邻测试：8 项 ME-17、55 项组合通过；QMT 调用计数、精确时间窗口、空/缺列/重复/NaN、零前收价和实例状态均动态验证。
- 当前容器无 xtquant/MiniQMT；测试只注入官方参数与返回结构一致的协议桩，并为缺失 `tzlocal` 注入 UTC 最小桩，实际 adapter 产品逻辑未替换。
- 限制：默认读取不再自动下载是有意契约变化；SDK 单次调用强制 deadline 留给统一 adapter 可靠性治理。
- 提交：`fix(ME-17): validate QMT ranges and payloads`。


### 问题 44：ME-26（恢复重建）
- **状态：** complete
- 验证结论：Flask factory 内构造、监听并立即启动 TornadoScheduler，reloader/多 worker 会各自执行同一持久任务，问题存在。
- 修复：移除 Web 的全部 APScheduler 生命周期；新增独立 BlockingScheduler CLI、跨进程 leader lock、启动及周期任务 reconcile、安全原子状态快照；Web 保存配置后由 runner 最终一致同步，`/jobs` 只读快照。
- 专项及相邻测试：9 项 ME-26、23 项组合通过；真实 POSIX 锁验证排他/释放/PID/0700/0600，协议 scheduler 验证 build 不启动、runner 只 start 一次、重复 CLI 返回 2。
- 当前容器缺 Flask、Flask-Login、APScheduler、pinyin、tzlocal；未启动真实长驻进程，限制已写入 a–e 报告。
- 独立 CLI 首次使用 package import 会先执行 Flask app 包；已改为直接惰性导入 `cl_app` 目录中的 runtime，避免无关 Web 依赖。
- 提交：`fix(ME-26): move scheduler out of Flask factory`。


### 问题 45：ME-19（恢复重建）
- **状态：** complete
- 验证结论：目标组选股结果通过 clear + 多次独立 add 提交，任一中途失败会留下空组/半组；opt_type 全链路传递但未消费；同名跨市场任务共享内存键，问题存在。
- 修复：新增完整快照预校验与单事务 `zx_replace_group_stocks`；任务在全部频率成功后只替换一次，重复代码稳定合并；失败不更新内存，键改为 `(market, task_name)`；删除无效果 opt_type 契约。
- 专项及相邻测试：7 项 ME-19、35 项组合通过；SQLite 第二条 INSERT 触发器失败验证旧快照完整回滚，成功路径 position=0..N-1，HK 同名组不变。
- 限制：未连接真实 MySQL；临时 running_tasks 仍为进程内状态；跨频率 memo 使用最后一个信号。
- 提交：`fix(ME-19): atomically replace selection results`。


### 问题 46：ME-18（验证阶段）
- **状态：** in_progress
- **开始时间：** 2026-08-04
- 静态验证确认问题存在：SelectionRunner/MonitoringRunner 没有逐标的结构化失败隔离；任务层无法区分 miss 与 failure；策略入口前没有统一 K 线 schema/时区/数据质量校验。
- 已确定修复边界：新增 StrategyRunTarget/Failure/BatchRunResult 和共享阶段执行器，并更新选股/监控任务层的失败可观测性与原子替换条件。

### 问题 46：ME-18
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：SelectionRunner/MonitoringRunner 的单标的异常会终止或只能由任务层宽泛捕获，且策略入口前没有统一 K 线协议，问题存在。
- 修复：新增 target/provider/input/strategy/output 五阶段失败模型和 BatchRunResult；统一深拷贝、市场时区、date/OHLCV、唯一升序时间、有限值、非负 volume、OHLC、code/frequency 校验；选股与监控任务分别实现“失败不替换旧结果”和“正常命中继续保存、整批返回失败”。
- 专项测试：`tests/test_me18_strategy_runner_contracts.py`，13 passed；相邻 ME-19/ME-12/Web payload/策略加载/安全选股监控组合共 52 passed。
- 首轮测试 fixture 自身构造了 low>close 的无效 K 线，被新协议正确拒绝；修正 fixture 后产品实现未改。
- 完整 cl_app 历史集成测试仍在 package import 前被容器缺失 pinyin 阻断；真实 AlertTasks 已通过最小依赖桩动态执行。
- 提交：`fix(ME-18): isolate strategy batch failures`。


### 问题 47：ME-14（验证阶段）
- **状态：** in_progress
- **开始时间：** 2026-08-04
- 已确认问题存在：TDX US 使用 `replace(tzinfo=pytz_zone)` 附着时区，且把 pytdx ExHQ 的 `amount` 当作 canonical `volume`。仓库随附 parser 证明 `trade` 与 `amount` 是两个独立字段。
- 正在抽取无网络副作用的 payload normalizer，并为冬/夏令时、跨午夜交易日、日线收盘锚点、字段映射和数据质量增加专项测试。

### 问题 47：ME-14
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：TDX US 通过 pytz replace 附着时区、凌晨交易日修正缺少契约测试，并把 pytdx `amount` 映射为 volume；仓库内置 parser 证明 `trade`/`amount` 独立，问题存在。
- 修复：新增纯 payload normalizer；zoneinfo 处理上海墙钟→纽约 DST，凌晨源时刻修正交易日，日线锚定纽约 16:00，转换后排序；volume 严格来自 `trade`，并校验时间、OHLC、有限值和非负成交量。
- 专项测试 17 passed（以 warnings=error）；ME-14/ME-12/MX-17/NX-20/MX-05 组合共 40 passed；compileall、diff 和 CRLF 门禁通过。
- 当前无真实 TDX ExHQ 网络；字段证据来自仓库随附 wheel，真实单位与黄金样本限制已写入台账。
- 提交：`fix(ME-14): normalize TDX US timezone and volume`。


### 问题 48：ME-30（验证阶段）
- **状态：** in_progress
- **开始时间：** 2026-08-04
- 已逐文件确认问题存在：QMT、Baostock、Alpaca、IB、Futu、Polygon、TQ、TDX 国内期货与 TDX 纽约期货仍分别使用服务器本地时间、硬编码现金时段、远端粗粒度状态、统一 02:30 夜盘或恒真返回。
- 原 `Exchange.now_trading()` 没有 code/instant 参数；Web history、ticks 和 AlertTasks 也不传具体 instrument，因此无法表达节假日、午休、半日市、DST 与不同期货品种 session。
- 修复边界：扩展版本化共享日历为 `market + code + aware instant`，未知品种/年份 fail-closed；迁移全部可达 provider 和调用方，并增加现金、FX、crypto、国内期货与纽约期货边界故障注入。


### 问题 48：ME-30
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：全部可达 provider 仍存在本机时钟、硬编码现金时段、统一期货夜盘、远端粗粒度状态或恒真返回；调用方不传 instrument，问题存在。
- 修复：统一 `market + code + aware at -> bool` 日历契约；现金/FX/crypto/国内期货/纽约期货按版本和品种解析，未知年份/品种 fail-closed；history、ticks 与监控任务传具体代码，Futu 按代码前缀分流 A/HK。
- 验证：22 项 warnings-as-errors 专项、152 项相邻组合通过；国内六类 profile、跨午夜/周末/春节前夜盘、CME 维护窗/圣诞/DST、畸形目标保留均已故障注入。
- 环境限制：完整 `test_selection_monitoring.py` 为 6 passed、9 项被缺失 pinyin/tzlocal 在业务断言前阻断；更广收集另受归档外 config.py 缺失阻断。
- compileall、JSON、diff 和 19 个 CRLF 文件 bare-LF=0 门禁通过。
- 提交：`fix(ME-30): unify instrument-aware market sessions`。


### 问题 49：ME-22
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：飞书发送没有 timeout/真实失败返回、时间函数依赖主机 localtime/mktime、singleton 并发首次构造无锁，问题存在。
- 修复：lark SDK per-attempt timeout + 同一 UUID 有限幂等重试 + 错误脱敏/严格布尔；zoneinfo/aware datetime/DST fail-closed；RLock 双重检查 singleton 与成功后发布。
- 专项及相邻验证：13 项 ME-22、51 项直接组合、326 项可运行仓库回归通过，3 skipped；compileall、JSON、diff 和 CRLF 门禁通过。
- 真实飞书未联调；当前容器无 lark-oapi，使用 v1.5.3 官方 builder/UUID 契约与 fake SDK 故障注入。
- 提交：`fix(ME-22): harden messaging time and singleton utilities`。


### 问题 50：ME-02
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：history follow-up 状态是无界普通字典，键不含身份/IP，且读改写无锁；firstDataRequest 全量历史是既有正确契约。
- 修复：新增线程安全 TTL/LRU 有界 tracker，使用 monotonic clock；按 user/IP/market/code/resolution 隔离，配置启动校验；首次请求完全旁路。
- 验证：8 项 warnings-as-errors 专项、48 项 ME-02/RV-07/Web payload 组合通过；24 worker/100 次并发得到旧语义对应的 16 次抑制，无丢更新或状态增长。
- 历史 firstDataRequest 动态测试在导入阶段被缺失 pinyin/Flask 依赖阻断；原测试不改，AST 门禁确认首次请求不进入 tracker。
- 实现过程中首个 CRLF 补丁脚本有 Python 拼接语法错误，第二次断言错误地构造了 `{{}}`；均在写回前中止。首轮并发测试误把旧复位周期按 7 计算，复算原控制流后修正为第 7、13、19…次抑制。
- 提交：`fix(ME-02): bound history request tracking`。


### 问题 041–050 完整仓库归档
- **状态：** complete
- 已生成包含完整源码与 `.git` 的 `tradingview_remediation_issues_041-050.zip` 及 SHA-256 sidecar。
- 使用系统 `unzip` 重新解压；工作树 clean，HEAD 与 `issue/050-ME-02` 一致，`issue/041-*` 至 `issue/050-*` 全部存在，`git fsck --full` 无损坏。
- Python 标准库 extractall 不恢复 Unix executable mode，曾造成 mode-only 假差；最终验证使用能恢复 external_attr 的系统 unzip。
## 2026-08-04 会话恢复与第 51–59 条重建
- 当前运行时仅保留问题 041–050 的完整仓库归档，以及截至第 59 条的规划、发现、进度与机器台账；第 51–59 条原 Git 对象和工作树未挂载，远程仓库也不包含这些本地提交。
- 从 SHA-256 已验证的 `tradingview_remediation_issues_041-050.zip` 恢复 `issue/050-ME-02` 固定点；依据已保存 a–e 台账逐条重新实现和验证，不伪造先前临时 SHA。
- 第 51 条专项 6 passed；直接相邻组合首次得到 53 passed / 2 failed，两个失败均在产品逻辑前被归档缺失 `config.py` 阻断；随后显式 deselect 后为 53 passed / 2 deselected。

### 问题 51：NX-10
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：strategy JSON 与 memo 仍写旧 String(200)，create_all 不迁移旧表，Web 无字段字节边界或写后核对，问题存在。
- 修复：新建两个 Text 列和幂等回填迁移；专用写路径事务内写新列并 refresh 精确往返；config/memo 采用 32 KiB/8 KiB UTF-8 硬上限，拒绝非对象、非标准数值和 NUL。
- 验证：6 项专项、53 项可运行相邻组合通过；2 项旧测试被归档缺失 config.py 阻断。
- 首轮专项有一个源码断言依赖单行格式，改为结构/片段顺序；另有测试未 dispose SQLite engine，在 `-W error` 下触发 ResourceWarning，修正测试资源清理后产品代码不变。
- 提交：`fix(NX-10): migrate alert strategy storage`。

### 问题 52：RV-06
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：全局 1 MiB 请求体边界已部分缓解原报告，但 chart/template/drawing 仍缺独立 UTF-8 上限、主体记录数/总字节配额、同名去重和并发事务，问题存在。
- 修复：新增共享 TVStoragePolicy；默认 blob 上限 512/256/512 KiB、记录配额 100/200/2000、总字节 16 MiB；MySQL MEDIUMTEXT、旧表去重/索引迁移、事务内 upsert；MySQL 主体锁+FOR UPDATE，SQLite 占用读取前 BEGIN IMMEDIATE；历史超限只减不增；Web 稳定返回 413/422。
- 验证：14 项 warnings-as-errors 专项、39 项 NX-14/NX-15 聚焦、106 项直接相邻、371 项可运行仓库回归通过，3 skipped；SQLite 双线程竞态只允许一条写入。
- 环境限制：15 个 selection_monitoring 测试在导入 cl_app 时缺 Flask/pinyin；另有 empyrical 与既有 footprint 私有导入阻断，均发生在产品断言前。
- 提交：`fix(RV-06): bound TradingView storage`。


### 问题 53：ME-15
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：Futu quote/trade 使用无锁模块级全局对象，随机清订阅，失败不失效重建，且无 close/fork 所有权，问题存在。
- 修复：新增独立 `FutuContextManager`；quote/trade 独立 RLock 与状态、有界重建、只发布完整对象、失败隔离、PID/at-fork 重置、无秘密 health、幂等 close/atexit；adapter 删除全局/随机/tenacity/wildcard 路径并统一 RET_OK 边界，缓存改为实例级防御性副本。
- 验证：9 项 warnings-as-errors 专项和 52 项直接相邻通过；20 线程同类操作最大并发严格为 1，quote/trade 可独立并发。广泛回归中 377 项执行通过、3 skipped；其余在产品断言前被缺失 pinyin、归档外 config.py、empyrical 或既有 footprint 私有导入阻断。
- 限制：未连接真实 Futu OpenD；单次 SDK 阻塞 deadline 与真实订阅、断线回调和服务器重启需沙箱联调。
- 提交：`fix(ME-15): manage Futu context lifecycle`。


### 问题 54：NX-01
- **状态：** complete（能力保持移除）
- **完成时间：** 2026-08-04
- 验证结论：旧 CTP 空前置地址错误所在运行时已由 CR-05 删除；当前无 adapter、SDK 依赖或 `CTP_*` 配置，工厂在 import/cache 前拒绝，原错误路径当前不存在。
- 修复：保持 fail-closed，不重新引入 CTP；补充恢复地址必须是校验的非空 `tcp://host:port`、空值在 SDK 构造前明确拒绝或通过唯一文档化默认值解析的规范，并增加专项门禁。
- 验证：4 项 NX-01 专项和包含 HI-01 移除门禁的 7 项组合通过；AST 确认 tombstone 位于全部 provider import/cache 写入前。
- 限制：能力移除不代表 CTP 可用；未连接 OpenCTP 仿真环境。
- 提交：`fix(NX-01): guard removed CTP front configuration`。


### 问题 55：NX-25
- **状态：** complete（不安全 provider 已删除）
- **完成时间：** 2026-08-04
- 验证结论：旧 `ExchangeZB`/TLS 绕过已随 MX-02 从运行树删除，当前工厂在 provider import/cache 前拒绝。
- 修复：保持删除；文档和门禁强制未来恢复启用证书链/主机名校验、系统信任库或显式 CA、验证失败不降级，并禁止 `verify=False/CERT_NONE/check_hostname=False/sslopt` 绕过。
- 验证：5 项专项和 10 项仓库卫生/Secret 安全组合通过；运行树扫描无等价 TLS 绕过。
- 限制：静态扫描不覆盖第三方依赖内部实现；恢复 ZB 仍是新功能。
- 提交：`fix(NX-25): guard removed ZB TLS security`。


### 问题 56：ME-29（恢复重建）
- **状态：** complete
- 验证结论：当前本地历史只有仓库卫生 workflow，缺完整 pytest、provider、真实 MySQL 与浏览器 DOM 四类稳定门禁；footprint 私有导入还会阻断完整收集，问题存在。
- 修复：新增四个只读 GitHub Actions job、质量门禁 checker、隔离配置生成器、真实 MySQL/Chromium 专用测试和分支保护文档；footprint 改用公开时间函数。
- 首次真实执行 provider job 发现 BaoStock 测试文件名错误，已修正并重跑。
- 验证：18 passed/2 skipped 专项；82 passed provider 严格矩阵；414 passed/5 skipped 可运行仓库回归；8 项缺 pinyin、完整收集缺 empyrical，均在产品断言前阻断。
- 提交：`fix(ME-29): add executable quality gates`。


### 问题 57：ME-10（恢复重建）
- **状态：** complete
- 验证结论：标准工厂缺能力声明、调用前拒绝、统一错误和响应边界，DB 能力存在过报风险，问题存在。
- 修复：新增根级领域契约、24 项 side-effect-free registry、ContractedExchange facade 和原子惰性 factory；DB 不声明 security master/plates，全部 provider 不声明 live orders。
- 验证：7 项专项、31 项聚焦、125 项 provider/工厂直接相邻测试以 warnings-as-errors 通过；真实 SQLite DB facade 与 Secret 故障注入通过。
- 提交：`fix(ME-10): add capability-bound exchange contracts`。


### 问题 58：ME-20（恢复重建）
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：StrategySignal 缺版本、用途动作、目标绑定、资源边界和明确时间语义，任务层仍能接受裸 list 绕过，问题存在。
- 修复：新增 v1 schema、StrategyAction/StrategyPurpose、canonical signal、有限 score/message/time/metadata、64 条输出上限、重复拒绝与 ignore→miss；Selection/Monitoring 采用不同动作集合，任务层仅接受 BatchRunResult。
- 验证：60 项 ME-20 专项、91 项核心聚焦、108 项 scheduler/calendar 任务相邻测试以 warnings-as-errors 通过；完整历史 selection_monitoring 中 6 项直接通过；隔离生成 config.py 后 DB 模型项另通过，剩余 8 项在缺 Flask/pinyin 导入阶段阻断。
- 测试过程：首个非 list 容器参数误用含 dict 的不可哈希 StrategySignal set，改为普通 set 后产品代码不变；ME-10 顺序隔离测试单独保留。
- compileall、py_compile、JSON、diff 与 7 个历史 CRLF 文件 bare-LF=0 门禁通过。
- 提交：`fix(ME-20): validate versioned strategy signals`。


### 问题 59：ME-25（恢复重建）
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：requirements.txt、未固定 uv、内置 uv 可执行文件、未登记 wheel 及缺少 SBOM/许可证/漏洞门禁仍在，旧 setup.py 删除只完成部分治理。
- 修复：pyproject+uv.lock 成为唯一安装源；固定 uv 0.10.0/locked sync；删除二次解析入口和不透明二进制；建立 7 个 wheel 的 SHA-256/来源/许可证清单、155 组件 CycloneDX、许可证库存、离线未扫描报告、到期豁免策略和 live fail-closed OSV CI。
- 验证：28 项专项/相邻测试通过；3 类 wheel 篡改/登记故障、stale SBOM、过期/重复豁免、OSV advisory 和响应数量失配全部按预期阻断；154 个 OSV package/version fixture clean=0、vulnerable=1。
- 过程修正：TA-Lib Project-URL 顺序改为确定性排序；测试复制 helper 补目标目录。
- 限制：当前容器无 Python 3.11 且本轮未联网访问 OSV；真实 locked sync 与 live scan 由新增 CI job 执行，离线报告不声称无漏洞。
- 提交：`fix(ME-25): add verifiable supply-chain manifests`。


### 问题 60：ME-27
- **状态：** complete
- **完成时间：** 2026-08-04
- 验证结论：业务凭据仍以明文/示例字符串集中在 Python 配置与通用飞书缓存，消费者直接读取 config，缺少统一分类、引用解析、版本轮换和日志脱敏，问题存在。
- 修复：新增 database/market-data/broker-trading/messaging/AI Secret inventory；配置只允许 env/managed/file/keyring 引用，明文默认拒绝；ManagedSecretStore 采用版本化原子 0600 文件与 0700 目录；全部数据库/行情/券商/AI/消息消费者在使用边界解析；飞书旧缓存迁移为 reference-only，留空保持、非空轮换；新增中央 redactor、文档和仓库门禁。
- 回归修正：扩大测试发现 issue57 ContractedExchange.order 绕过 issue13 CR-03 源码门禁；已恢复无条件 fail-closed，并用误报 LIVE_ORDERS 能力的 fake provider 确认底层 order 从未调用。
- 验证：105 项聚焦、82 项 provider `-W error` 矩阵、495 项可运行仓库回归通过，5 skipped；四项静态门禁、compileall、JSON、diff 与 CRLF 检查通过。
- 环境限制：未连接真实 keyring/Vault/券商或消息服务；Windows ACL 和完整 Flask/Chromium 本地运行未验证，真实 browser gate 已保留在 CI。
- 提交：`fix(ME-27): require rotatable secret references`。


### 问题 051–060 完整仓库归档
- **状态：** complete
- 已生成包含完整源码与 `.git` 的 `tradingview_remediation_issues_051-060.zip` 及 SHA-256 sidecar。
- 使用系统 `unzip` 重新解压验证：工作树 clean，HEAD 与 `issue/060-ME-27` 一致，`issue/051-*` 至 `issue/060-*` 全部可解引用，`git fsck --full` 成功。
- 归档前清除 ignored 测试配置、运行缓存和 `__pycache__`；保留全部可达本地提交、标签及源码。


### 问题 61：ME-04（恢复重建）
- 状态：complete；严格 K 线 payload 边界与路由错误契约已复验。


## 2026-08-04 第 61–70 条恢复重建
- 运行环境重挂载后，未形成正式十条归档的第 61–70 条代码与 Git 对象不可恢复；第 51–60 条完整归档、原始问题清单及第 61–69 条 a–e 台账仍在。
- 从已校验 `tradingview_remediation_issues_051-060.zip` 恢复到 `issue/060-ME-27`，逐条重新实现并生成真实提交，不沿用不存在的 SHA。
- 第 61 条 ME-04 已完成严格 K 线 payload、市场时区前置规范化、身份/排序/OHLCV 校验与稳定错误契约；15 项专项及报告门禁通过。
- 第 61 条提交：`184efe5 fix(ME-04): validate canonical history payloads`，标签 `issue/061-ME-04`。
- 当前第 62 条 ME-01 已确认剩余根因：TradingView 协议中的 `client/user` 仍直接作为数据库所有权键；正在改为登录会话主体，并设计受控、幂等的旧 owner 迁移。
- ME-01 首轮 43 项严格组合为 38 passed / 5 failed；失败全部来自 NX-15 旧测试未关闭源码文件的 ResourceWarning，已改为 Path.read_text 后准备复验，产品与迁移专项没有失败。

### 问题 62：ME-01（恢复重建）
- **状态：** complete
- 验证结论：chart/template/drawing 虽要求登录，仍把请求 `user` 直接作为数据库 owner；已登录主体可横向伪造其他 owner，问题存在。
- 修复：新增 `WEB_AUTH_PRINCIPAL` 和显式 `TV_STORAGE_LEGACY_USER_IDS`；请求 user 仅校验，不参与授权；所有数据库调用使用 `current_user.get_id()`。旧 999 owner 在单事务中迁移，冲突按 timestamp/id 保留最新，unknown owner 不触碰，quota lock 同步迁移。
- 验证：4 项 ME-01 专项、60 项严格相邻测试通过，3 skipped；当前可运行仓库回归 515 passed、5 skipped、8 deselected。SQLite 冲突迁移、unknown 隔离、幂等重跑与三条真实路由动态执行均通过。
- 过程修正：NX-15 旧 AST 测试未关闭源码文件导致 warnings-as-errors 失败，改为 `Path.read_text()` 后同一组合 43 passed。
- 编译、JSON、diff 与三个历史 CRLF 文件 bare-LF=0 门禁通过。
- 待提交主题：`fix(ME-01): bind TradingView storage to sessions`。
- ME-03 相邻测试首次引用已不存在的旧测试文件，随后 ME-10 在缺归档外 config.py 时收集阻断；已改为当前实际测试文件并采用临时 demo 配置，不重复失败命令。

### 问题 63：ME-03（恢复重建）
- **状态：** complete
- 验证结论：`/tv/config` 手写七个市场并集，遗漏 `ny_futures`；当前周期碰巧重合但未来独有周期会漂移。
- 修复：新增 `all_market_frequencies()`，按元数据当前全部市场稳定去重；真实路由不再硬编码市场键。
- 验证：注入 ny_futures 独有 `10s`、AST 检查真实 tv_config、5 项元数据测试及 12 项注册表/能力相邻测试全部通过。
- 待提交主题：`fix(ME-03): derive UDF resolutions from all markets`。

### 问题 64：MX-11（恢复重建）
- **状态：** complete
- 原配置模板已由 ME-27 改成 env 引用，但复核发现 ExchangeIB docstring 仍残留具体 DU 账户；本条删除该身份样例。
- 新增配置/worker/adapter 扫描和 Secret 动态拒绝测试；MX-11 + ME-27 共 14 passed（-W error）。
- 待提交主题：`test(MX-11): prevent concrete IB account templates`。

### 问题 65：MX-07（恢复重建）
- **状态：** complete
- alert.js 七个 Layui 列对象把 `field` 拼成 `filed`，排序和字段元数据失效。
- 七处统一改为 `field`，不改变 API、标题或模板语义；字段集合、可排序列与 Node 语法均纳入测试。
- MX-07/MX-05/HI-06 组合 12 passed（-W error），CRLF 与 diff 门禁通过。
- 待提交主题：`fix(MX-07): correct alert table field bindings`。

### 问题 66：MX-10（恢复重建）
- **状态：** complete
- 验证结论：Charts.show_tv_chart 的实现只有 id 一个参数，但模板六个调用点仍传高度，JavaScript 静默忽略且留下无效尺寸变量，问题存在。
- 修复：六个调用统一为单参数，删除 win_width/chart_height；容器继续持有 flex、百分比和显式高度，widget 保持 autosize；JSDoc 固化公开签名。
- 验证：Node vm 断言运行时 arity=1，node --check、布局静态契约、CRLF 与 diff 门禁通过；MX-10/MX-05 组合 7 passed（-W error）。
- 过程修正：首次引用不存在的 test_mx05_watchlist_timer.py，按当前目录改为 test_mx05_rate_timer.py 后复验。
- 待提交主题：`fix(MX-10): align chart display call contract`。

### 问题 67：NX-09（恢复重建）
- **状态：** complete
- 验证结论：fee_us 是公开但只返回 None 的空桩，且 src/script/web 没有调用方，问题存在。
- 修复：删除 fee_us，不凭空实现无来源美股费率；保留 fee_a，并增加全运行代码 AST 无定义/无引用门禁。
- 验证：真实模块不再暴露 fee_us，fee_a 买/卖样例仍为 32/42；NX-09/NX-08 共 6 passed（-W error），编译、CRLF 与 diff 门禁通过。
- 过程修正：首次引用不存在的 NX-08 测试文件，按当前目录改为 test_nx08_position_close_profit.py 后复验。
- 待提交主题：`fix(NX-09): remove unimplemented US fee stub`。

### 问题 68：NX-18（恢复重建）
- **状态：** complete
- 验证结论：render_zixuan_opts 两个分支裸写 templet，非严格模式泄漏到全局对象，问题存在。
- 修复：改为 each 回调块内 const 条件表达式，保留 checked/unchecked 模板输出和下拉数据结构。
- 验证：Node vm 执行真实脚本后 context 无 templet 属性，两种 HTML 均正确；NX-18/MX-05 组合 6 passed（-W error），语法、CRLF 与 diff 门禁通过。
- 待提交主题：`fix(NX-18): scope watchlist dropdown templates`。

### 问题 69：NX-17（恢复重建）
- **状态：** complete
- 验证结论：Web 把全部市场写为 24x7、FX 写为 stock，并对 HK/NY futures 使用错误时区，问题存在。
- 修复：集中 TradingView type/session/timezone；现金、FX、crypto、国内六类期货与纽约 Globex 使用权威常规时段，未知国内期货只退化到日盘；搜索 type 只作过滤。
- 验证：现金/FX/crypto、RB/CU/AG/IF/T/AP/GC 和未知品种全部参数化；真实 tv_symbols/tv_search AST 使用描述符；NX-17/ME-30/ME-03/ME-05/RV-07 共 63 passed（-W error）。
- 编译、Web CRLF、JSON 与 diff 门禁通过。
- 待提交主题：`fix(NX-17): publish market-aware UDF sessions`。

## 2026-08-04 · 问题 70：LO-02（恢复重建）
- **状态：** complete
- 验证结论：五个 TDX ExHq 适配器重复生命周期；Alpaca/Polygon 重复美国历史边界并含 `len(datetime)` 确定性错误；港股、币现货和期货同步脚本仍有 import 副作用与过期 universe，问题存在。
- 修复：新增 `TdxExHqLifecycleMixin`、`us_history.py`，扩展 `sync_batch.py` 的过滤/安全空 universe；五个 ExHq 和两个美国 provider 迁入共享边界，三份剩余脚本改为薄 CLI + JSON 配置。
- 故障注入：无效缓存、首次连接失败、空 market map、冬夏令时、逆序/重复/非法 OHLCV、provider-free 空批次、过滤后空集和六个入口 import 均纳入自动测试。
- 验证：35 项聚焦、71 项 TDX/日历相邻、99 项 provider 严格组合全部通过（`-W error`）；可运行仓库回归 565 passed/5 skipped。8 项 Web 测试缺 pinyin、1 项回测收集缺 empyrical，均在产品断言前阻断。
- 静态门禁：compileall、JSON、git diff、历史 CRLF 全部通过。
- 提交主题：`refactor(LO-02): consolidate market adapter workflows`。
- 第 70 条提交后生成并用系统 `unzip` 复验问题 061–070 的完整 `.git` 归档。

### 问题 71：LO-06
- **状态：** complete
- 验证结论：三个 provider 仍有 wildcard import，Alpaca/Polygon 使用短变量、宽泛异常、print 并返回 None；无可执行 lint 门禁，问题存在。
- 修复：运行树 wildcard import 清零；三个 provider 显式导入和领域命名；新增共享 secret-free provider logging/exception boundary；未支持能力改为领域异常。
- 门禁：pyproject 启用 F403/F405/BLE001；repository hygiene 执行 AST checker，拒绝 wildcard、目标短名和无理由 broad catch。
- 验证：故障注入确认 network/unknown SDK 异常映射和日志不泄密；LO-06/LO-02/ME-11/ME-14/ME-17/ME-29 组合 63 passed（-W error）；compileall、质量门禁、CRLF 和 diff 通过。
- 提交主题：`refactor(LO-06): enforce auditable provider code`。

### 问题 72：MX-16
- **状态：** complete
- 删除未加载的 `ai.js`、完全 no-op 的 `OtherTasks` 及 app factory 懒代理；不把不可用能力伪装成实现。
- 运行时引用图、app factory AST、MX-16/ME-26/ME-05 共 15 项严格测试通过；compileall、CRLF 与 diff 门禁通过。
- 提交主题：`refactor(MX-16): remove dead AI and task stubs`。

### 问题 73：MX-18
- **状态：** complete
- 新增版本化 Signal→TradeDecision→Operation 桥接；执行参数必须由 metadata.trade 明确提供，禁止从 score/message 猜测。
- Operation 嵌入完整 snapshot，反向转换逐字段防篡改；selection/watch/ignore 与 arbitrary legacy Operation 明确拒绝。
- MX-18/ME-20/ME-18 组合 82 passed（-W error）；完整 BackTest 泛型测试仍被环境缺少 empyrical 阻断。
- 提交主题：`feat(MX-18): add versioned strategy trade bridge`。


### 2026-08-04T14:33:14Z · 会话恢复：问题 74 NX-11
- 从 `issue/073-MX-18` 固定点恢复后发现工作树已有未提交的 NX-11 草稿，涉及 typed event/action/score schema、旧表迁移、监控写入和前端空值展示。
- 已核对原问题文本与 `git diff`；不丢弃现有修改，下一步先审查新模块与迁移实现，再执行专项、相邻和双后端契约验证。

- 2026-08-04T14:34:10Z：审查 NX-11 新模块与专项测试；首个 DB 摘录脚本因函数边界假设不匹配而中止，已切换为按实际行号定位，仓库产品文件未受影响。

### 2026-08-04T14:35:44Z · NX-11 恢复草稿审查检查点
- 已确认未提交草稿形成一致的修复方向：独立 `event_type/action` 与数值 `score` 边界、旧列只读兼容、写入路径不再截断分数。
- `db.py`、`alert_tasks.py`、`alert.js` 三个历史文件仍保持纯 CRLF（bare LF = 0），未出现全文件换行噪声。
- 尚未接受为完成：下一步逐段审查迁移与事务语义，并运行 NX-11 专项、MySQL DDL、监控任务和相邻回归。

- 第 74 条首轮聚焦组合结果：19 passed、1 skipped、8 failed；8 个失败均在导入 `cl_app` 时因当前环境缺少 `pinyin`，发生在产品断言前。核心领域、SQLite 迁移、MySQL DDL 与前端源码契约均已通过。后续改用既有隔离加载方式执行真实 `alert_tasks.py`。

- 2026-08-04T14:36:17Z：NX-11/selection 组合得到 19 passed、8 failed；8 项均在 `cl_app` 导入阶段因环境缺少 `pinyin` 阻断，未执行到 NX-11 产品断言。将专项与可运行相邻测试分开复验。

- 2026-08-04T14:37:44Z：NX-11 专项 12 passed（`-W error`）；随后一个不存在的 selection 测试节点使验证命令 code 4，已记录并改为先列举真实节点。
- 2026-08-04：NX-11 完整 pytest 首次在收集阶段被当前环境缺少 `empyrical` 阻断，发生在 `test_backtesting_base_generic.py`，未执行产品测试；后续不重复该命令，改为排除这一已知环境阻断后执行可收集仓库回归。

- 2026-08-04T14:40:08Z：复核确认 NX-11 迁移已按方言选择 MySQL `DOUBLE`、其他后端 `FLOAT`；12 项专项与 7 项不依赖 Web 包初始化的 selection/monitoring 相邻测试均通过。
- 2026-08-04：排除既有 `empyrical` 收集阻断后，可收集仓库回归执行到 603 项：595 passed、5 skipped，另 8 项仅因当前容器缺少 `pinyin` 在 `cl_app` 导入阶段失败；这些失败与 NX-11 产品代码无关，真实 AlertTasks 已由隔离加载测试覆盖。

- 2026-08-04T14:41:44Z：NX-11 + ME-18 + ME-20 + ME-29 严格组合完成，97 passed、1 skipped；skip 为未配置真实 MySQL 服务。确认第 74 条报告/机器台账仍待写入。

- 2026-08-04T14:43:14Z：NX-11 扩大相邻组合得到 122 passed、1 skipped、1 failed；唯一失败为历史 NX-22 子进程在导入 DB 前缺少归档外 `config.py`，与本条 typed schema 无关。后续不重复该阻断，按已记录环境限制排除后复验。

### 问题 74：NX-11 完成
- 已建立独立 `event_type/action/score` 物理列和领域校验，旧短列转为只读兼容；MySQL 旧表 score 迁移使用 `DOUBLE`。
- NX-11 专项 14 passed；严格相邻组合 105 passed/1 skipped；可收集仓库回归 595 passed/5 skipped，环境阻断单独记录。
- 全部静态、供应链、Secret、JavaScript、JSON、CRLF 和 diff 门禁通过。
- 提交主题：`fix(NX-11): type monitoring event persistence`。
- 下一条：75. LO-05。
### 2026-08-04 · 问题 75 LO-05 验证开始
- 确认问题仍存在：provider registry 与 Web metadata 双源，`/tv/config`、首页模板和八个 `EXCHANGE_*` 配置仍需手工同步。
- 修复方向：扩展 `MarketSpec` 为全栈市场描述符；Web、UDF、模板和 provider override 全部由注册表派生，并补“只新增一个 registry 条目即可通过”的穷尽故障注入。


- 2026-08-04T14:50:50Z：LO-05 已确认 index/alert/xuangu 三个模板均手写八市场选项；首次 render_template 正则过窄无命中并被 `set -e` 中止，改用文件名/函数边界定位。

- 2026-08-04T14:51:33Z：LO-05 测试盘点命令首次因 shell 重定向位置错误中止，未写产品文件；已改为逐文件存在性判断。
- LO-05 首轮整体补丁在 `config.py.demo` 的换行假设处中止；exchange factory 的前置修改已成功落盘，其余文件未写入。改为逐文件 CRLF/LF 感知替换。

- LO-05 首次相邻测试在收集阶段被缺失的本地 `src/tradingview_zy/config.py` 阻断；该文件按仓库设计不入库。后续改用 `script/remediation/prepare_test_config.py` 生成临时配置，并在测试结束后删除，不重复裸环境测试。
- 2026-08-04T15:03:01Z：LO-05 已扩展 `MarketSpec` 为 provider、默认配置、UI、UDF、payload 时区、DB 分区和频率的单一静态描述符；`market_metadata.py` 已改为纯派生视图，尚待迁移消费者并测试。

- LO-05 实现补齐：`MarketSpec` 新增唯一默认市场和板块面板标志；`market_metadata.py` 增加 registry 派生的 catalog/default/UI API；模板、UDF、provider 选择和同步配置均消费这些投影。
- 新增 `test_lo05_market_registry_single_source.py`，覆盖穷尽注册、单描述符驱动全栈、默认/覆盖 provider、旧重复映射删除、动态模板、同步配置校验和通用 CLI import 无副作用。
- 更新 MX-05 JavaScript 语法门禁，适配新的整表 JSON 与动态默认市场 Jinja 表达式。

- LO-05 首轮 75 项聚焦/相邻测试结果：70 通过、5 失败。失败均定位为契约迁移缺口：HK Futu 的附加 10m 同步周期、旧测试仍写 EXCHANGE_A、两个 tombstone 顺序断言反向、MX-05 Jinja 正则空白未匹配；未发现 provider 运行时回归。
- LO-05 扩展组合首次引用不存在的历史测试名 `test_v6_market_registry.py`，收集前即停止；改用仓库实际存在的新穷尽测试与 ME-10 契约测试。
- LO-05 首次仓库级回归：603 passed/5 skipped，10 failures；其中 2 项是 CR-05/MX-02 测试仍写已删除的 EXCHANGE_*，8 项仍为环境缺少 pinyin 的历史 Web 阻断。
- LO-05 removed-provider 复验发现 `configured_provider` 会在 tombstone 前把 ctp/zb 当普通未知 provider 拒绝。改为工厂先 `selected_provider`、再 tombstone、最后 `provider_spec`，保留专用删除证明且仍不导入实现。


### 问题 75：LO-05 完成
- MarketRegistry 现在同时声明 provider/能力、默认 provider、UI/UDF 元数据、默认代码、展示与同步周期、时区/session、默认市场和 DB 分区；其余模块只消费派生投影。
- 首页、`/tv/config`、symbols/search 和同步配置均删除八市场手写映射；新配置使用 `MARKET_PROVIDERS`，旧 `EXCHANGE_*` 仅保留读取兼容。
- 严格聚焦/相邻组合 82 passed；可运行仓库回归 605 passed、5 skipped、8 deselected；质量、供应链、Secret、Node、JSON、diff 与 CRLF 门禁通过。
- 提交主题：`fix(LO-05): centralize full-stack market metadata`。
- 下一条：76. LO-07。


### 第 76 条 LO-07 恢复与错误记录
- AST/引用盘点确认剩余问题集中在 Exchange 可选能力空桩、三个运行树墓碑模块、FileCacheDB 旧 RuntimeError 方法和 BackTest 无调用方 `show_charts`。
- 首次按整段字节文本替换 `backtesting/base.py` 的可选 hook 失败：方法包含 docstring，预期块未命中；操作在写回前中止。
- 处理方式改为 AST 行号定位，仅把 `on_bt_loop_start()` 与 `clear()` 的裸 `pass` 替换为显式 `return None`，并保留 CRLF。

- LO-07 首次聚焦 pytest 命令引用不存在的 `tests/test_nx09_us_fee_stub_removed.py`，pytest 在收集前退出、未运行任何测试；实际文件名为 `tests/test_nx09_removed_us_fee_stub.py`，下一次命令改用实际路径。
- LO-07 聚焦回归首次实际运行得到 42 passed、1 failed：NEW-06 历史门禁要求 DB provider 自己保留空板块方法，与本条“统一由 Exchange 抛 UnsupportedCapabilityError”新契约冲突。已更新旧门禁为断言 DB 不声明板块方法且注册表不声明 PLATES；领域限制不变。
- LO-07 完整 `pytest -q` 在收集阶段被当前 Python 3.13 环境缺少 `empyrical` 阻断；唯一收集错误为 `tests/test_backtesting_base_generic.py`，未执行产品断言。托管 CI 的 Python 3.11 锁定环境仍要求完整套件。
- 排除唯一 empyrical 收集阻断后，广泛回归实际执行结果为 619 passed、5 skipped、8 failed；8 个失败全部在 `cl_app` 导入阶段因当前容器缺少 `pinyin`，没有进入产品断言。将以精确节点 deselect 复验其余可运行套件，并保留 CI 完整运行要求。


### 问题 76：LO-07 完成
- 统一 Exchange 可选能力 fallback，未实现能力只返回稳定 `UnsupportedCapabilityError`；facade 会把继承 fallback 识别为未实现，阻断注册表过报。
- 删除 17 个 provider 中的重复空桩、三个墓碑模块、五个 FileCacheDB 旧兼容壳和 BackTest.show_charts；IB 删除虚假目录能力。
- 43 项聚焦、105 项严格 provider 矩阵、619 项可运行仓库回归通过；5 skipped、8 个 pinyin 环境节点 deselect，empyrical 收集限制单独记录。
- 全部编译、质量、供应链、Secret、FIFO、JSON、diff 与 CRLF 门禁通过。
- 提交主题：`refactor(LO-07): replace speculative stubs with capability errors`。
- 下一条：77. LO-08。


### 2026-08-04 · 问题 77 LO-08 验证开始
- `check_env.py` 已由 ME-24 修复：从 `pyproject.toml` 读取 `>=3.11,<3.12`，输出稳定状态并返回可靠退出码；该原报告子问题已不存在。
- 剩余漂移真实存在：README 仍声称支持 trader 下单/撤单，与 CR-03 全部实盘入口 fail-closed 冲突；`joinquant/` 仍位于活跃根目录并直接依赖 `jqdata`/旧 `cl`；provider 能力文档只有手写说明，没有由 MarketRegistry 自动生成并由 CI 校验的全量支持矩阵。
- 修复方向：把 JoinQuant 研究遗留确定性归档并移出运行根目录；校准 README；从 MarketRegistry 生成 provider support matrix，并在 repository-hygiene CI 中执行 stale 检查。
- LO-08 首次聚焦 pytest 未先运行 `prepare_test_config.py`，CR-03/LO-07 两个模块在收集时因归档外 `config.py` 缺失停止；未执行测试、产品文件未受影响。下一次使用受控临时配置并在退出时清理。
- LO-08 首次用 `write_text(..., newline="\n")` 更新历史 CRLF README，造成全文件换行差异；已恢复 README 到 HEAD，改用字节级 CRLF 替换，并将首页关于页的同一过期“交易执行工具”描述一起校准。


### 问题 77：LO-08 完成
- 保留 ME-24 已修复的 pyproject 派生 check_env，不重复改写；删除 README/首页实盘能力误述。
- 将顶层 JoinQuant 研究遗留确定性归档为 `archive/joinquant-legacy.zip`，活跃根目录不再包含专有 jqdata/旧 cl 代码。
- 新增 MarketRegistry 派生的 provider support matrix，并由 repository-hygiene/quality contract 执行 stale 检查。
- 7 项专项、50 项严格相邻、626 项可运行仓库回归通过；所有文档生成、质量、供应链、Secret、FIFO、diff 与 CRLF 门禁通过。
- 提交主题：`docs(LO-08): generate support truth and archive legacy research`。
- 下一条：78. LO-03。


### 问题 78：LO-03（进行中）
- 恢复 config 稳定绑定的首次脚本因检测顺序漏加顶层 import，仓库回归出现 3 个 NameError；已补齐顶层绑定并将三个工厂测试纳入立即复验。
- 仓库回归发现惰性 config 导入会在模块替换测试中读取不同配置对象；已恢复稳定的 package 级 config 绑定，LO-03 保持只改值语义，依赖注入留到 LO-01。
- 严格矩阵发现旧 ME-18 测试仍期待未知市场在 input 阶段失败；新领域 parser 已在 target 阶段 fail-closed，更新测试以固定更早的拒绝边界。
- 相邻复验显示剩余污染来自 SQLite helper 未恢复临时 config；helper 已改为 pytest monkeypatch 事务化模块替换，测试结束自动恢复真实配置模块。
- 顶层 config 测试桩会污染相邻 ME-10 测试；已改为产品 package 仅在 `get_exchange()` 调用时惰性导入配置，并删除测试桩，纯 facade 导入因此无配置副作用。
- 新专项首次收集被 exchange 包的归档外 `config.py` 依赖阻断；改为在测试导入纯 facade 前注入最小无 Secret 配置，不修改产品运行边界。
- 回测完整基础测试仍在收集阶段被缺少 `empyrical` 阻断；LO-03 将用文件隔离方式执行真实 `backtesting/base.py`，其他相邻测试不再重复该阻断命令。
- 首次相邻测试命令引用不存在的历史 ME-10 测试文件，pytest 在收集前退出；已记录错误，改按实际文件名重组，不重复原命令。
- 已确认问题存在：Market/Frequency/订单方向与状态仍广泛使用裸字符串，且实际仓库缺失报告曾提及的订单领域枚举。
- 拟定修复范围：新增稳定领域枚举和 parser；在 MarketRegistry、ContractedExchange、策略协议、回测 Operation/POSITION 与 DB K 线边界统一 canonicalize；补 SQLite 往返、provider 前置拒绝和序列化故障注入。


### 问题 78：LO-03 完成
- Market 改为 StrEnum，并新增 Frequency、订单方向、仓位方向、开平、状态、回测操作和模式领域枚举与严格 parser。
- Registry、provider facade、策略协议、Web resolution、回测和 DB K 线边界统一 canonicalize；非法代码在 SDK/SQL 前 fail-closed。
- 11 项专项、193 项严格相邻、637 项可运行仓库回归通过；5 skipped、8 个 pinyin 环境节点 deselect，empyrical 收集限制单独记录。
- 全部编译、支持矩阵、质量、供应链、Secret、FIFO、JSON、diff 与 CRLF 门禁通过。
- 提交主题：`refactor(LO-03): enforce typed market and order codes`。
- 下一条：79. LO-04。


### 2026-08-04 · 问题 79 LO-04 验证开始
- 原报告的 OrderRequest/Fill/OrderState/KlineFrame 在当前重建运行树中并不存在；`domain.py` 只有第 78 条新增的代码枚举。
- 已定位两个高风险 Data Clumps：Alpaca/Polygon 把同一 OHLCV 七字段 dict 列表传入共享 frame builder；告警策略配置在 Web、AlertTasks 和 DB 间反复传递/解析任意 dict。
- 修复方向：新增不可变 KlineBar、OrderRequest、Fill、OrderState 与 StrategyParameters 领域对象；在 provider payload、策略配置和执行桥接边界使用，内部 DataFrame 继续保留。
- LO-04 首轮专项 8 passed/1 failed；唯一失败为未知市场从共享 parser 透出 `InvalidRequestError`，未收敛到 DataContractError。产品仍 fail-closed；现将异常统一到数据契约边界后复验。
- LO-04 首次相邻回归命令引用不存在的 `test_lo02_shared_adapters.py`，pytest 在收集前退出；已改用实际测试目录清单，不重复原命令。


### 问题 79：LO-04 完成
- 新增不可变、版本化的 provider bar、canonical Kline、策略参数、订单请求、成交和订单状态领域对象；公共边界不再依赖重复 dict。
- Alpaca/Polygon、US history、策略存储/Web/AlertTasks 和策略桥接已接入；内部 DataFrame 保留，实盘能力仍 fail-closed。
- 9 项专项、142 项严格相邻、646 项可运行仓库回归通过；5 skipped、8 个 pinyin 环境节点 deselect，empyrical 收集限制单独记录。
- 全部编译、质量、供应链、Secret、FIFO、Node、JSON、diff 与 CRLF 门禁通过。
- 提交主题：`refactor(LO-04): introduce immutable data contracts`。
- 下一条：80. LO-01。
