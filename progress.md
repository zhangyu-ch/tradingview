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
