# TradingView 当前开放问题逐条修复记录

- **原始问题清单：** `audit/tradingview_current_open_issues_v1.md`（只读保留）
- **问题总数：** 81
- **已完成：** 36
- **待处理：** 45
- **提交规则：** 每个问题一个本地 Git 提交，直接落在 `main`，不推送远程。
- **判定规则：** 仅在根因修复且自动化验证通过后标记“已完成”；真实外部系统未联调的限制会单独列出。

## 总览

|序号|编号|严重度|领域|原状态|本轮状态|验证结果|提交|
|---:|---|---|---|---|---|---|---|
|1|`CR-02`|严重|Web Security|🟡 部分修复|已完成|通过（3 项专项测试通过）|`fix(CR-02)`|
|2|`NEW-02`|高|CI / Supply Chain|🆕 新问题（未修复）|已完成（本地已不存在，已加防回归）|通过（本地风险不存在，3 项防回归测试通过）|`fix(NEW-02)`|
|3|`NEW-03`|高|Dependencies / Packaging|🆕 新问题（未修复）|已完成|通过（2 项专项测试与静态依赖契约检查通过）|`fix(NEW-03)`|
|4|`NEW-04`|高|Web / Market Data|🆕 新问题（未修复）|已完成|通过（6 项 web payload 测试通过）|`fix(NEW-04)`|
|5|`NEW-05`|高|Backtesting / Accounting|🆕 新问题（未修复）|已完成（本地不存在，已加防回归）|通过（确切回归不在本地；3 项防回归测试通过）|`test(NEW-05)`|
|6|`NX-20`|高|TDX Reliability|❌ 未修复|已完成|通过（3 项专项测试通过，4 个构造器均已移除无上限重连）|`fix(NX-20)`|
|7|`RV-08`|高|Web Security / Secrets|❌ 未修复|已完成（共享修复已复验）|通过（共享根因已修复，2 项独立防回归测试通过）|`test(RV-08)`|
|8|`HI-13`|高|Binance|❌ 未修复|已完成|通过（5 项专项测试通过，合约/现货均使用严格分页器）|`fix(HI-13)`|
|9|`HI-14`|高|TQ SDK|❌ 未修复|已完成|通过（3 项离线生命周期/源码契约测试通过；真实 TQ SDK 导入与联调受缺失依赖和账户环境阻断）|`fix(HI-14)`|
|10|`CR-05`|高|CTP|🛡️ 未完全修复（已阻断或缓解）|已完成（通过移除不支持能力）|通过（5 项专项/依赖回归测试通过；不安全的 CTP 能力已从运行包彻底移除并 fail closed）|`fix(CR-05)`|
|11|`CR-04`|高|QMT Trader|🛡️ 未完全修复（已阻断或缓解）|已完成（通过移除不支持能力）|通过（3 项 CR-04 专项测试及相邻下线门禁均通过；危险 QMT 实盘适配器已从运行包移除）|`fix(CR-04)`|
|12|`HI-06`|高|Web Security|🛡️ 未完全修复（已阻断或缓解）|已完成|通过（14 项可执行测试通过；所有写请求的统一 CSRF 边界和 GET 删除根因已消除）|`fix(HI-06)`|
|13|`CR-03`|高|Live Trading|🟡 部分修复|已完成（通过移除未验收实盘订单执行能力）|通过（13 项专项/相邻测试通过；所有内置实盘订单和撤单入口均明确 fail-closed）|`fix(CR-03)`|
|14|`ME-24`|中|Environment|🔴 回归（重新出现）|已完成|通过（5 项专项测试通过；版本契约同源、失败退出码和状态汇总均正确）|`fix(ME-24)`|
|15|`NEW-06`|中|Architecture / Exchange Contract|🆕 新问题（未修复）|已完成（本地不存在，已加防回归）|通过（确切回归在本地不存在；4 项门禁测试防止未来重新过报）|`test(NEW-06)`|
|16|`HI-01`|中|Futures Trader|❌ 未修复|已完成（共享修复已复验）|通过（旧构造参数和错误落库类型所在模块已移除；7 项专项/共享门禁通过）|`test(HI-01)`|
|17|`ME-06`|中|File Upload|❌ 未修复|已完成|通过（4 项专项测试通过；共享文件、无界读取和上传边界根因已消除）|`fix(ME-06)`|
|18|`ME-16`|中|Interactive Brokers|❌ 未修复|已完成|通过（4 项专项测试通过；所有 IB 客户端 RPC 均使用有限 deadline）|`fix(ME-16)`|
|19|`ME-05`|中|Web Startup|❌ 未修复|已完成|通过（3 项专项测试通过；应用启动元数据不再实例化任何外部适配器）|`fix(ME-05)`|
|20|`MX-01`|中|Configuration / Messaging|❌ 未修复|已完成（通过移除废弃能力）|通过（3 项专项测试通过；破裂钉钉配置与不可达 HK 分支已从运行树移除）|`fix(MX-01)`|
|21|`MX-06`|中|Database / Operations|❌ 未修复|已完成|通过（3 项专项测试通过；直接执行文件不再触发测试业务写入）|`fix(MX-06)`|
|22|`MX-02`|中|Exchange Factory|❌ 未修复|已完成（通过移除不支持能力）|通过（4 项 MX-02 专项测试及 3 项相邻 provider 下线测试通过；支持声明与可选工厂已一致）|`fix(MX-02)`|
|23|`MX-04`|中|ExchangeDB / Scheduling|❌ 未修复|已完成|通过（3 项专项测试通过；DB provider 不再暴露 None/null 三态）|`fix(MX-04)`|
|24|`MX-05`|中|Frontend|❌ 未修复|已完成|通过（3 项专项测试通过；定时回调、重启清理和停止语义均通过 Node 动态验证）|`fix(MX-05)`|
|25|`MX-17`|中|TDX / Performance|❌ 未修复|已完成|通过（6 项专项测试及相邻 NX-20 测试通过；冷启动/重置扫描具有并发上限、全局 deadline 与有限缓存 TTL）|`fix(MX-17)`|
|26|`NX-08`|中|Backtesting Model|❌ 未修复|已完成|通过（3 项专项测试通过；成功、fallback、重复调用和异常路径均不再修改调用方列表）|`fix(NX-08)`|
|27|`NX-03`|中|Configuration / Messaging|❌ 未修复|已完成|通过（3 项专项测试通过；所有配置来源均返回独立映射，不再污染全局默认字典）|`fix(NX-03)`|
|28|`NX-22`|中|Database / Diagnostics|❌ 未修复|已完成|通过（6 项专项、相邻及报告测试通过；数据库模块不再覆盖进程 warning 策略）|`fix(NX-22)`|
|29|`NX-21`|中|Database Configuration|❌ 未修复|已完成|通过（3 项专项测试及相邻 DB 测试通过；特殊字符凭据可正确解析且默认字符串脱敏）|`fix(NX-21)`|
|30|`NX-23`|中|ExchangeDB|❌ 未修复|已完成|通过（17 项专项、相邻、能力边界及报告测试通过；DB provider 可恢复持久化标的目录且未过报证券主数据能力）|`fix(NX-23)`|
|31|`NX-16`|中|Web Security / Availability|❌ 未修复|已完成|通过（20 项专项及相邻测试通过；输入扇出、请求速率、provider 并发和等待时间均有明确上限）|`fix(NX-16)`|
|32|`NX-14`|中|Web Storage|❌ 未修复|已完成|通过（37 项专项与相邻测试通过；不存在资源稳定返回 404，畸形标识在数据库访问前返回 422）|`fix(NX-14)`|
|33|`NX-15`|中|Web Storage|❌ 未修复|已完成|通过（26 项专项与相邻测试通过；异常、未确认结果和缺参不再返回伪成功）|`fix(NX-15)`|
|34|`RV-05`|中|Backtesting / Process|❌ 未修复|已完成|通过（18 项专项与相邻测试通过；缺少保存路径在主进程明确失败，合法路径安全生成）|`fix(RV-05)`|
|35|`RV-04`|中|Backtesting Metrics|❌ 未修复|已完成|通过（20 项专项与相邻测试通过；零值与容差内噪声计入持平，不再污染失败统计）|`fix(RV-04)`|
|36|`RV-01`|中|Database / Watchlist|❌ 未修复|已完成|通过（7 项专项与相邻测试通过；跨市场隔离、失败回滚和连续重排均正确）|`fix(RV-01)`|
|37|`RV-07`|中|Web API Robustness|❌ 未修复|待处理|—|—|
|38|`ME-11`|中|Baostock|❌ 未修复|待处理|—|—|
|39|`HI-17`|中|Scripts|❌ 未修复|待处理|—|—|
|40|`ME-12`|中|TDX Adapters|❌ 未修复|待处理|—|—|
|41|`ME-23`|中|Backtesting Config|❌ 未修复|待处理|—|—|
|42|`HI-16`|中|File Cache|❌ 未修复|待处理|—|—|
|43|`ME-17`|中|QMT Market Data|❌ 未修复|待处理|—|—|
|44|`ME-26`|中|Scheduler Lifecycle|❌ 未修复|待处理|—|—|
|45|`ME-19`|中|Selection Tasks|❌ 未修复|待处理|—|—|
|46|`ME-18`|中|Strategy Runners|❌ 未修复|待处理|—|—|
|47|`ME-14`|中|TDX US|❌ 未修复|待处理|—|—|
|48|`ME-30`|中|Trading Calendar|❌ 未修复|待处理|—|—|
|49|`ME-22`|中|Utilities|❌ 未修复|待处理|—|—|
|50|`ME-02`|中|Web UDF|❌ 未修复|待处理|—|—|
|51|`NX-10`|中|Database Schema|❌ 未修复|待处理|—|—|
|52|`RV-06`|中|Web Storage / Availability|❌ 未修复|待处理|—|—|
|53|`ME-15`|中|Futu|❌ 未修复|待处理|—|—|
|54|`NX-01`|中|CTP|🛡️ 未完全修复（已阻断或缓解）|待处理|—|—|
|55|`NX-25`|中|Legacy Exchange Security|🛡️ 未完全修复（已阻断或缓解）|待处理|—|—|
|56|`ME-29`|中|Quality Gates|🟡 部分修复|待处理|—|—|
|57|`ME-10`|中|Adapter Architecture|🟡 部分修复|待处理|—|—|
|58|`ME-20`|中|Strategy Protocol|🟡 部分修复|待处理|—|—|
|59|`ME-25`|中|Supply Chain|🟡 部分修复|待处理|—|—|
|60|`ME-27`|中|Secrets|🟡 部分修复|待处理|—|—|
|61|`ME-04`|中|Web Payload|🟡 部分修复|待处理|—|—|
|62|`ME-01`|中|Web Storage|🟡 部分修复|待处理|—|—|
|63|`ME-03`|低|Web UDF|❌ 未修复|待处理|—|—|
|64|`MX-11`|低|Configuration|❌ 未修复|待处理|—|—|
|65|`MX-07`|低|Frontend|❌ 未修复|待处理|—|—|
|66|`MX-10`|低|Frontend|❌ 未修复|待处理|—|—|
|67|`NX-09`|低|Backtesting Fees|❌ 未修复|待处理|—|—|
|68|`NX-18`|低|Frontend|❌ 未修复|待处理|—|—|
|69|`NX-17`|低|Web UDF|❌ 未修复|待处理|—|—|
|70|`LO-02`|低|Maintainability|❌ 未修复|待处理|—|—|
|71|`LO-06`|低|Readability|❌ 未修复|待处理|—|—|
|72|`MX-16`|低|Dead Code|❌ 未修复|待处理|—|—|
|73|`MX-18`|低|Strategy Architecture|❌ 未修复|待处理|—|—|
|74|`NX-11`|低|Database Schema|❌ 未修复|待处理|—|—|
|75|`LO-05`|低|Architecture|🟡 部分修复|待处理|—|—|
|76|`LO-07`|低|Dead Code|🟡 部分修复|待处理|—|—|
|77|`LO-08`|低|Documentation|🟡 部分修复|待处理|—|—|
|78|`LO-03`|低|Domain Model|🟡 部分修复|待处理|—|—|
|79|`LO-04`|低|Domain Model|🟡 部分修复|待处理|—|—|
|80|`LO-01`|低|Maintainability|🟡 部分修复|待处理|—|—|
|81|`MX-12`|低|Architecture / Spec|🟡 部分修复|待处理|—|—|

## 逐条记录

### 01. CR-02 · 默认部署无有效认证，且会话签名密钥固定

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 严重 / Web Security
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 本地代码的远程免密拒绝、随机持久化会话密钥、密码哈希、限速和安全 Cookie 已存在；但 `/setting` 仍把数据库中的飞书 App Secret 作为普通文本框 value 返回给浏览器，并在提交前把整个表单打印到控制台。
- **b. 我是怎么修复的？** 设置页 GET 不再读取或传递旧 Secret，只传递“是否已配置”的布尔值；输入框改为无预填值的 password/new-password；删除控制台表单日志；保存时采用“Secret 留空则保持旧值，非空才轮换”的纯函数；设置页与保存响应增加 no-store 缓存头。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_cr02_settings_secret.py`，覆盖远程免密启动拒绝、随机 Secret 持久化/权限、Secret 留空保持和轮换语义。
  - 源码契约测试确认设置页不含 `{{ fs_app_secret }}`、不再执行 `console.log(data.field)`，且输入类型为 password。
  - 运行 `python3 -m compileall` 和 `git diff --check` 验证修改文件可编译且无补丁格式错误。
- **e. 验证是否通过？** 通过（3 项专项测试通过）
- **提交：** fix(CR-02): stop echoing saved Feishu secrets
- **修改文件：** `src/tradingview_zy/settings_security.py`, `web/tradingview_zy_chart/cl_app/__init__.py`, `web/tradingview_zy_chart/cl_app/templates/setting.html`, `tests/test_cr02_settings_secret.py`, `script/remediation/parse_issue_report.py`, `script/remediation/update_issue.py`, `audit/remediation_state.json`, `remediation_report.md`
- **验证限制：**
  - 当前容器缺少 Flask/Werkzeug 且无法联网安装，未运行真实 Flask test client；路由数据流由源码契约测试验证，纯 Secret 合并逻辑和认证/会话关键函数已动态测试。
- **原报告最新结论：** 默认回环监听、远程免密启动拒绝、随机持久化会话密钥、密码哈希、登录限速、安全 Cookie 和登出仍在；但设置页继续把已保存的飞书 App Secret 放入普通文本框 value，并打印整个提交字段。
- **原报告建议：** 设置页不得返回旧 Secret；删除 console.log(data.field)；敏感设置更新应使用“留空不改”语义，并考虑重认证/更严格权限。

### 02. NEW-02 · 临时修复传输分片与可写 force-push 工作流被合并进 master

- **原始状态 / 严重度 / 领域：** 🆕 新问题（未修复） / 高 / CI / Supply Chain
- **本轮状态：** 已完成（本地已不存在，已加防回归）
- **问题是否存在：** 否
- **a. 这个问题是什么？** 原报告固定点的远程 master 含临时补丁分片、临时 PR 元数据和具备 contents:write/force-push 的修复传输工作流；当前用户提供的本地 ZIP 已不包含这些文件，因此本地当前代码不再存在直接风险。
- **b. 我是怎么修复的？** 未对已缺失的文件做伪删除；新增仓库卫生扫描器，拒绝 `.github/remediation`、current-remediation 分片/元数据、contents:write、git reset --soft 和强制推送；新增只读 GitHub Actions 门禁，权限仅为 contents:read。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 执行 `find` 与 `rg` 扫描当前工作树，确认本地没有原报告列出的临时文件和危险工作流。
  - 运行 `python3 script/remediation/check_repository_hygiene.py`，当前仓库通过。
  - 运行 `pytest -q tests/test_new02_repository_hygiene.py`，覆盖当前仓库、恶意 fixture 与只读工作流 fixture。
- **e. 验证是否通过？** 通过（本地风险不存在，3 项防回归测试通过）
- **提交：** fix(NEW-02): add repository hygiene gate
- **修改文件：** `.github/workflows/repository-hygiene.yml`, `script/remediation/check_repository_hygiene.py`, `tests/test_new02_repository_hygiene.py`, `audit/remediation_state.json`, `remediation_report.md`, `progress.md`
- **验证限制：**
  - 远程 GitHub master 仍可能保留历史临时文件；用户明确要求不推送远程，本提交只修复并保护本地交付仓库。
- **原报告最新结论：** master 仍包含 .github/remediation/current-remediation.part.*、临时 PR body 文件和 3 个 contents:write 工作流；这些工作流能重组补丁、git reset --soft，并向 agent/current-comprehensive-remediation 执行 force-with-lease。临时元数据文件自身写明“must not be merged”。
- **原报告建议：** 删除 3 个临时工作流、全部 remediation 分片/marker/test 文件和临时 PR 元数据；增加仓库卫生检查，禁止此类 transport artifacts 合并。

### 03. NEW-03 · requirements.txt 与 pyproject/uv.lock 漂移，可重新解析出已知不兼容依赖

- **原始状态 / 严重度 / 领域：** 🆕 新问题（未修复） / 高 / Dependencies / Packaging
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 本地代码同时维护 `requirements.txt` 与 `pyproject.toml` 两套直接依赖清单；本地 `pyproject.toml` 重新加入了 `chardet`、没有限制 `websockets`，`uv.lock` 实际锁到 chardet 7.1.0 与 websockets 16.0；Python 约束还错误覆盖 3.12+，但仓库仅提供 CPython 3.11 的 TA-Lib 轮子。
- **b. 我是怎么修复的？** 把 `pyproject.toml` 设为唯一人工维护依赖源；`requirements.txt` 改为 `-e .` 兼容转发；Python 约束收紧为 3.11；删除直接 chardet，增加 `websockets>=13.1,<14`；同步锁文件到 websockets 13.1 并移除 chardet；新增依赖契约检查器、恶意漂移 fixture 和 CI 门禁。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `python3 script/remediation/check_dependency_contract.py`，校验 pyproject、requirements 与 uv.lock 的 Python、直接依赖、根包 metadata 和关键锁定版本一致。
  - 运行 `python3 -m pytest -q tests/test_new03_dependency_contract.py`，当前仓库和故意漂移的临时项目共 2 项测试通过。
  - 使用 `tomllib` 直接解析锁文件，确认不存在 chardet 包/根依赖，websockets 锁定为 13.1，根 metadata 保留 `>=13.1,<14`。
  - 运行 `python3 -m compileall` 与 `git diff --check`。
- **e. 验证是否通过？** 通过（2 项专项测试与静态依赖契约检查通过）
- **提交：** fix(NEW-03): unify dependency sources and compatibility bounds
- **修改文件：** `pyproject.toml`, `requirements.txt`, `uv.lock`, `script/remediation/check_dependency_contract.py`, `tests/test_new03_dependency_contract.py`, `.github/workflows/repository-hygiene.yml`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 容器只有 Python 3.13 且离线，`uv lock --check --offline` 在选择项目要求的 Python 3.11 解释器前即停止；锁文件结构、项目 metadata 和关键版本已由独立 TOML 契约测试验证，CI 在 Python 3.11 上继续执行同一检查。
- **原报告最新结论：** pyproject 已删除 chardet 并固定 websockets>=13.1,<14；requirements.txt 仍直接列出无上界 chardet 和 lark-oapi，且没有 websockets 兼容约束。使用 requirements 安装可再次解析到 chardet 7.x / websockets 16.x，重现本次 CI 中已出现过的 Requests/Lark 导入告警或失败。
- **原报告建议：** 将 pyproject+uv.lock 设为唯一依赖源；若必须发布 requirements，则从 lock 自动生成并在 CI 校验无漂移。

### 04. NEW-04 · /tv/history 在市场时区本地化前过滤时间窗口，naive K 线会按服务器时区错筛

- **原始状态 / 严重度 / 领域：** 🆕 新问题（未修复） / 高 / Web / Market Data
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** `/tv/history` 在把行情时间解释为市场本地时间之前，就调用 `Timestamp.timestamp()` 做首行与请求窗口比较。naive A 股 09:30 因而会按 Web 主机时区解释，在 UTC 主机上与 Asia/Shanghai 的正确 epoch 相差 8 小时。
- **b. 我是怎么修复的？** 新增统一的市场时区映射和 `normalize_klines_for_market()`；该函数复制输入并把 naive 时间按交易市场本地化、aware 时间转换到市场时区；路由在任何首行比较、范围过滤和 TradingView payload 转换前先规范化；epoch 转换现在拒绝 naive 时间，未知市场 fail closed。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_web_payloads.py`，6 项测试通过。
  - 专项测试用 A 股 naive `2026-05-03 09:30` 与 Asia/Shanghai epoch 构造精确单点窗口，确认可正确选中且调用方 DataFrame 不被修改。
  - 专项测试确认未知市场不能回退到服务器时区；源码检查确认 `/tv/history` 在首行和范围判断前调用规范化函数。
  - 运行 `python3 -m compileall` 与 `git diff --check`。
- **e. 验证是否通过？** 通过（6 项 web payload 测试通过）
- **提交：** fix(NEW-04): normalize market time before history filtering
- **修改文件：** `src/tradingview_zy/web_payloads.py`, `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_web_payloads.py`, `audit/remediation_state.json`, `remediation_report.md`, `progress.md`
- **验证限制：**
  - 当前容器缺 Flask/Werkzeug，未运行真实浏览器请求；市场本地化、过滤、payload 和路由调用顺序均已通过纯函数动态测试与源码契约核对。
- **原报告最新结论：** 路由先调用 filter_klines_by_timestamp_range，再由 klines_to_tv_history/_prepare_strict_history_frame 把 naive date 本地化到市场时区。Timestamp.timestamp() 对 naive 值使用主机本地时区；在 UTC 服务器上，A 股 09:30 会比 Asia/Shanghai 正确瞬间偏移 8 小时，可能返回 no_data 或错选窗口。
- **原报告建议：** 公开 prepare/normalize 函数并在任何 range/first-row 时间判断前调用；增加 UTC 主机 + A 股 naive 时间的路由级回归测试。

### 05. NEW-05 · FIFO lot 在结算校验完成前原地消费，异常会留下“lot 已减、聚合仓位未减”的半提交状态

- **原始状态 / 严重度 / 领域：** 🆕 新问题（未修复） / 高 / Backtesting / Accounting
- **本轮状态：** 已完成（本地不存在，已加防回归）
- **问题是否存在：** 否
- **a. 这个问题是什么？** 报告固定点中的问题依赖 `backtesting/accounting.py`、`POSITION.lots`、`consume_fifo_lots()` 与 `close_settlement()`；用户提供的本地 ZIP 不包含该模块/字段/调用，当前回测仍使用聚合仓位模型，所以本地不存在“lot 已减、聚合仓位未减”的确切半提交路径。
- **b. 我是怎么修复的？** 没有为不存在的运行路径凭空引入 FIFO 会计代码；新增 AST 原子性门禁，扫描全部产品源码：若同一函数同时出现结算校验和 FIFO lot 消费，校验必须先于消费。门禁包含原始不安全顺序与安全顺序 fixture，防止远程代码或后续重构把该回归重新带入。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 全仓搜索 `accounting.py`、`lots`、`consume_fifo_lots` 与 `close_settlement`，确认本地运行树没有报告所述实现。
  - 运行 `python3 script/remediation/check_fifo_atomicity.py`，当前源码通过。
  - 运行 `python3 -m pytest -q tests/test_new05_fifo_atomicity_guard.py`，覆盖当前仓库、原始半提交顺序与安全顺序。
  - 运行 `python3 -m compileall` 与 `git diff --check`。
- **e. 验证是否通过？** 通过（确切回归不在本地；3 项防回归测试通过）
- **提交：** test(NEW-05): guard FIFO settlement atomicity
- **修改文件：** `script/remediation/check_fifo_atomicity.py`, `tests/test_new05_fifo_atomicity_guard.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本地代码没有 FIFO lot 功能，因此不能执行报告固定点中的动态故障注入；本提交验证的是本地不存在该路径，并对未来重新引入的调用顺序建立自动门禁。
- **原报告最新结论：** 平仓路径先 consume_fifo_lots(pos.lots, ...) 原地减少/删除 lot，再调用 close_settlement 校验 close price、direction、期货 symbol_size 等。若后者抛错，后续聚合 amount/now_pos_rate/cash 尚未提交，但 pos.lots 已被修改，状态模型分叉。
- **原报告建议：** 让 lot 消费成为纯函数/对深拷贝工作；所有结算参数验证通过后一次性替换 lots、amount、rate、cash、records。增加无效 symbol_size/fee/price 的故障注入回归测试。

### 06. NX-20 · 多个 TDX-ExHq 构造器用无上限 while True 重连

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 高 / TDX Reliability
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 港股、国内期货、纽约期货和外汇四个 TDX-ExHq 构造器都用 `while True` 初始化 market map；连接持续失败时只重选节点并无限重试，构造器可能永久阻塞 Web 启动、测试和停机。
- **b. 我是怎么修复的？** 新增共享 `call_with_bounded_retry()`：同时限制最大 3 次尝试和 12 秒总 deadline，向每次 SDK connect 传递剩余预算并使用指数退避；失败统一抛 `ProviderUnavailableError`。四个 ExHq 构造器均改为该机制，并把 pytdx `time_out` 限制在剩余预算内，不再吞异常后留下半初始化对象。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_nx20_tdx_bounded_retry.py`，3 项测试通过。
  - Fake clock 故障注入确认持续连接失败最多调用 3 次且不超过总 deadline；第二次成功路径确认只恢复一次。
  - AST 契约逐一检查四个 ExHq 构造器，确认 `__init__` 内不存在恒真 while，并且都调用共享有界重试函数。
  - 读取仓库内 pytdx wheel，确认 `connect(..., time_out=...)` 是受支持参数；运行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项专项测试通过，4 个构造器均已移除无上限重连）
- **提交：** fix(NX-20): bound TDX ExHq constructor retries
- **修改文件：** `src/tradingview_zy/exchange/tdx_reliability.py`, `src/tradingview_zy/exchange/exchange_tdx_hk.py`, `src/tradingview_zy/exchange/exchange_tdx_futures.py`, `src/tradingview_zy/exchange/exchange_tdx_ny_futures.py`, `src/tradingview_zy/exchange/exchange_tdx_fx.py`, `tests/test_nx20_tdx_bounded_retry.py`, `audit/remediation_state.json`, `remediation_report.md`, `progress.md`
- **验证限制：**
  - 未连接真实 TDX 节点；重试、deadline 和异常语义由 fake clock/operation 验证，SDK 连接超时参数由随仓库提供的 pytdx wheel 源码确认。
- **原报告最新结论：** 多个 TDX-ExHq 构造器仍使用无上限 while True 重连；V6 顶层“已修复”没有源码依据。
- **原报告建议：** 有限次数+指数退避+总 deadline；失败抛 ProviderUnavailableError；构造器不得永久阻塞。

### 07. RV-08 · 系统设置页把已保存的飞书 App Secret 明文回显，并在控制台打印提交字段

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 高 / Web Security / Secrets
- **本轮状态：** 已完成（共享修复已复验）
- **问题是否存在：** 否
- **a. 这个问题是什么？** RV-08 与 CR-02 的剩余根因相同。复验当前本地 main：设置页已经不再获取/返回旧 `fs_app_secret`，Secret 输入为无预填的 password，控制台不再打印表单，保存使用留空不改语义并设置 no-store，因此原泄露在问题 01 后已不存在。
- **b. 我是怎么修复的？** 不重复修改已安全的业务逻辑；新增独立 Secret 暴露静态门禁，检查模板预填、输入类型、浏览器日志、GET 路由返回字段、配置状态替代字段和 Cache-Control；加入 CI，并用原始脆弱模板/路由 fixture 证明门禁能捕获整条泄露链。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `python3 script/remediation/check_secret_exposure.py`，当前设置页和路由通过。
  - 运行 `python3 -m pytest -q tests/test_rv08_secret_exposure_guard.py`，当前安全实现与原始泄露 fixture 共 2 项通过。
  - 再次运行 CR-02 的源代码检查结论：模板无 `{{ fs_app_secret }}`、无 `console.log(data.field)`，GET 只返回 configured 布尔值。
  - 运行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（共享根因已修复，2 项独立防回归测试通过）
- **提交：** test(RV-08): enforce no-secret-echo settings contract
- **修改文件：** `script/remediation/check_secret_exposure.py`, `tests/test_rv08_secret_exposure_guard.py`, `.github/workflows/repository-hygiene.yml`, `audit/remediation_state.json`, `remediation_report.md`, `progress.md`
- **验证限制：**
  - 当前容器未运行真实 Layui 浏览器；泄露数据流由模板/路由静态门禁和纯 Secret 合并测试覆盖。
- **原报告最新结论：** setting.html 当前仍以 type=text 和 value="{{ fs_app_secret }}" 回显旧 Secret，并在提交回调中 console.log(data.field)。
- **原报告建议：** 不返回旧 Secret；使用 password 输入与留空不改语义；删除日志；增加响应/DOM/控制台无 Secret 测试。

### 08. HI-13 · Binance 合约/现货增量分页可能重复边界或停滞，单行缓存会越界

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 高 / Binance
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** Binance 合约与现货适配器都用 `db_klines.iloc[-2]` 作为增量起点，缓存仅一行时直接越界；前向分页又把上一页最后时间戳原样作为下一页 startTime，包含端点的 API 会重复边界，若服务端忽略游标还可能永久停滞；反向分页也未排除上一页第一条。
- **b. 我是怎么修复的？** 新增共享 Binance OHLCV 分页器：缓存起点对 0/1/N 行均安全；前向游标严格推进到 `last+1ms`，反向游标退到 `first-1ms`；每页校验 schema/时间戳，按时间去重排序，限制最大页数并在无进展时抛 `PaginationStalledError`。合约和现货适配器统一调用该实现，对无新增数据安全返回缓存且不写入 None。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_hi13_binance_pagination.py`，5 项测试通过。
  - 参数化验证空、单行和多行缓存起点；单行不再访问 -2 索引。
  - 伪造包含上一页端点的前向响应，确认请求游标依次为 1000、2001、3001 且结果无重复。
  - 伪造重复整页确认抛停滞错误；反向分页确认第二页 endTime 为 first-1；源码契约确认两个适配器均无 `iloc[-2]`。
  - 运行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（5 项专项测试通过，合约/现货均使用严格分页器）
- **提交：** fix(HI-13): make Binance pagination strictly progressive
- **修改文件：** `src/tradingview_zy/exchange/binance_pagination.py`, `src/tradingview_zy/exchange/exchange_binance.py`, `src/tradingview_zy/exchange/exchange_binance_spot.py`, `tests/test_hi13_binance_pagination.py`, `audit/remediation_state.json`, `remediation_report.md`, `progress.md`
- **验证限制：**
  - 未调用真实 Binance/CCXT 网络接口；分页端点和停滞行为通过可控 fake API 响应验证。
- **原报告最新结论：** Binance 合约/现货增量逻辑仍读取 db_klines.iloc[-2]，单行缓存会越界；分页起点仍可能停在上页最后时间戳，造成重复边界或停滞。
- **原报告建议：** 单行/空缓存显式分支；下一页起点推进一个最小周期；去重并检测无进展。

### 09. HI-14 · ExchangeTq 构造即启动非 daemon 线程，队列/缓存无同步与确定性关闭

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 高 / TQ SDK
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** ExchangeTq 的构造函数立即启动默认非 daemon Thread；命令使用普通 list、行情缓存和 API 状态由调用线程与工作线程无锁共享；close_task_thread 只设置布尔值并 sleep，既不 join 也不保证释放 TqApi。参数化类还被全局 singleton 包装，使第一次构造参数永久影响后续调用。
- **b. 我是怎么修复的？** 移除参数化 singleton 与构造时线程启动，新增 ManagedWorker 管理显式/惰性 start、daemon 策略、停止 Event、幂等启动和带 timeout 的 join。命令改为 queue.Queue，订阅集合与结果缓存受 RLock 保护，K 线和 Tick 以快照形式跨线程交付；SDK API 创建/替换/关闭受独立 RLock 管理，close 在停止工作线程后确定性释放 API，并支持上下文管理器。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_hi14_tq_lifecycle.py`，3 项专项测试通过。
  - 动态测试 ManagedWorker：线程为 daemon、重复 start 不会创建第二线程、stop 设置 Event 并在 1 秒内 join；从未启动时 close 安全返回。
  - AST/源码契约确认 ExchangeTq 构造器不调用 start、已移除 singleton、使用 Queue/RLock/ManagedWorker、close 调用带 timeout 的 stop，且不存在 list.append 命令队列或 stop_thread 轮询。
  - 运行 compileall、git diff --check 和旧危险模式 grep。
  - 尝试真实导入实例化；容器缺少项目依赖 tzlocal 与 tqsdk，故未连接天勤 SDK，已记录为环境限制。
- **e. 验证是否通过？** 通过（3 项离线生命周期/源码契约测试通过；真实 TQ SDK 导入与联调受缺失依赖和账户环境阻断）
- **提交：** fix(HI-14): make TQ worker lifecycle deterministic
- **修改文件：** `src/tradingview_zy/exchange/worker_lifecycle.py`, `src/tradingview_zy/exchange/exchange_tq.py`, `tests/test_hi14_tq_lifecycle.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 容器未安装 tqsdk，且完整项目导入还缺 tzlocal；未执行真实天勤行情订阅、账户登录和网络断线联调。
  - SDK 内部协程停止语义通过 1 秒 wait_update deadline 与 API close 边界推演，真实 SDK 版本仍应在 Python 3.11 环境做集成测试。
- **原报告最新结论：** ExchangeTq 构造仍启动非 daemon 线程；共享队列/字典缺少同步，close() 只置标记并 sleep，没有 join/确定性释放。
- **原报告建议：** 显式 start/close 生命周期、daemon 策略、锁/线程安全队列、join timeout 和资源释放测试。

### 10. CR-05 · CTP 行情与交易代码存在多处确定性失效，但当前未接入标准工厂或内置启动脚本

- **原始状态 / 严重度 / 领域：** 🛡️ 未完全修复（已阻断或缓解） / 高 / CTP
- **本轮状态：** 已完成（通过移除不支持能力）
- **问题是否存在：** 是
- **a. 这个问题是什么？** 本地工厂没有正常选择 CTP，但运行包仍包含可直接导入的 MarketCTP 与 CTPTrader。前者未实现完整 Exchange 抽象契约、构造的 Tick 字段与基础类型不匹配、历史 K 线为 pass、now_trading 调用错误；后者存在重复覆盖的方法和未经验证的订单路径。与此同时 pyproject/uv.lock 仍安装 OpenCTP，配置模板仍暴露 CTP 凭据和前置地址，形成‘看似支持、实际不可用’的危险能力。
- **b. 我是怎么修复的？** 明确选择下线而非伪装修复：从运行包删除 exchange_ctp.py 与 trader_ctp.py；从 pyproject 和 uv.lock 移除 openctp-ctp；从配置模板移除 CTP 凭据/前置项；在交易所工厂建立 removed-provider 注册表，使 EXCHANGE_FUTURES='ctp' 在惰性导入与缓存写入前抛出 UnsupportedProviderError。新增不支持能力文档，明确恢复 CTP 必须作为经沙箱验收的新功能重新实现。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_cr05_ctp_removed.py tests/test_new03_dependency_contract.py`，5 项测试通过。
  - 动态把 EXCHANGE_FUTURES 设置为 ctp，确认工厂抛出明确 UnsupportedProviderError，未导入 exchange_ctp 且未污染 g_exchange_obj。
  - 静态确认两个 CTP 运行时文件已删除，src/script/web 不再包含 openctp_ctp、exchange_ctp 或 trader_ctp 引用。
  - 解析 pyproject.toml 与 uv.lock，确认 OpenCTP 包、根依赖和 requires-dist 均已移除；依赖契约脚本通过。
  - 运行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（5 项专项/依赖回归测试通过；不安全的 CTP 能力已从运行包彻底移除并 fail closed）
- **提交：** fix(CR-05): remove unsupported CTP runtime
- **修改文件：** `src/tradingview_zy/exchange/exchange_ctp.py（删除）`, `src/tradingview_zy/trader/trader_ctp.py（删除）`, `src/tradingview_zy/exchange/__init__.py`, `src/tradingview_zy/config.py.demo`, `pyproject.toml`, `uv.lock`, `docs/unsupported-providers.md`, `tests/test_cr05_ctp_removed.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本次关闭方式是移除不支持能力，CTP 行情与实盘交易不再是内置功能；没有声称完成 OpenCTP 仿真或实盘验证。
  - archive/ 下的历史架构文档保留原记录，不作为当前支持声明；当前状态以运行包、配置模板和 docs/unsupported-providers.md 为准。
- **原报告最新结论：** CTP 行情/交易实现仍未达到可用状态，标准工厂继续 fail-closed，不会把未完成实现作为正常 provider 加载。底层文件仍保留。
- **原报告建议：** 继续保持 fail-closed。恢复 CTP 前必须补齐抽象方法、Tick 契约、交易状态机、回报/重连/资源释放，并在仿真前置环境验证。

### 11. CR-04 · QMT 交易适配器真实买入确定性引用未定义 price；当前无内置活跃启动入口

- **原始状态 / 严重度 / 领域：** 🛡️ 未完全修复（已阻断或缓解） / 高 / QMT Trader
- **本轮状态：** 已完成（通过移除不支持能力）
- **问题是否存在：** 是
- **a. 这个问题是什么？** QMTTraderStock 虽无内置启动器，但仍可从运行包直接导入。真实买入在取得报价前用未定义的 price 计算数量；QMT 路径和资金账号硬编码；订单查询未命中时 price/amount 可能未绑定；持仓上限、资金不足或真实下单失败又可能降级为模拟成交，并继续发送成功通知、修改自选和写共享订单账本。
- **b. 我是怎么修复的？** 删除未验收的 QMT 实盘交易适配器及其自执行示例，保留独立的 QMT 行情 provider。更新不支持能力文档，明确 QMT 行情与交易能力分离；未来恢复订单执行必须通过显式能力/工厂、外部强制配置、幂等 client_order_id、券商确认成交、重启对账和 QMT 沙箱测试，真实失败不得转换为模拟成功。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src python3 -m pytest -q tests/test_cr04_qmt_trader_removed.py tests/test_cr05_ctp_removed.py`，6 项测试通过。
  - 确认 `src/tradingview_zy/trader/trader_qmt_stock.py` 已删除，src/script/web 无 QMTTraderStock、trader_qmt_stock 或 xtquant.xttrader 导入。
  - 确认 `exchange_qmt.py` 与 ExchangeQMT 行情类仍在，未误删 QMT 市场数据能力。
  - 检查不支持能力文档明确禁止真实失败回退为模拟成交；运行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项 CR-04 专项测试及相邻下线门禁均通过；危险 QMT 实盘适配器已从运行包移除）
- **提交：** fix(CR-04): remove unsafe QMT live trader
- **修改文件：** `src/tradingview_zy/trader/trader_qmt_stock.py（删除）`, `docs/unsupported-providers.md`, `tests/test_cr04_qmt_trader_removed.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 本次关闭方式是移除 QMT 订单执行能力；没有声称完成 QMT 实盘或沙箱订单验证。
  - QMT 行情适配器保留，后续将按 ME-17 单独修复其数据契约问题。
- **原报告最新结论：** QMT 交易类的底层错误实现仍在仓库并可被直接导入；标准应用当前没有内置活跃启动入口，且统一能力模型没有把它作为可用交易执行能力暴露。
- **原报告建议：** 不得绕过标准工厂启用该类。若恢复支持，需修正报价/数量、订单状态、真实失败不得模拟成功，并完成 QMT 沙箱集成测试；否则应真正移出运行包。

### 12. HI-06 · 状态变更接口无 CSRF 防护，删除任务还使用 GET

- **原始状态 / 严重度 / 领域：** 🛡️ 未完全修复（已阻断或缓解） / 高 / Web Security
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** Web 应用原先仅依赖登录 Cookie 和 SameSite=Lax，没有会话绑定的 CSRF token，也没有 Origin/Referer 校验；所有 POST 写接口都可在用户已登录时被跨站页面尝试调用。提醒任务删除更使用 GET，普通链接、浏览器预取或第三方页面即可触发状态变更。
- **b. 我是怎么修复的？** 新增会话绑定、使用恒定时间比较的 CSRF token；所有非 GET/HEAD/OPTIONS/TRACE 请求统一由 Flask before_request 校验 token，并拒绝不合法或跨站 Origin/Referer。登录与登出轮换 token；登录表单显式携带隐藏 token；已认证页面输出 meta token，统一 JavaScript 适配 jQuery AJAX、fetch、XMLHttpRequest 和原生表单。将 /alert_del/<id> 及其前端调用从 GET 改为 POST，并提供可配置的严格可信 Origin 列表。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_hi06_csrf.py tests/test_web_security.py`：14 项通过，3 项因当前离线镜像缺 Flask/APScheduler/pinyin/tzlocal 而明确跳过。
  - 专项测试覆盖安全方法、缺失/错误/旧 token、表单与请求头 token、同源与跨站 Origin/Referer、显式可信 Origin 和登录/登出 token 轮换。
  - 静态契约检查确认 /alert_del/<id> 仅允许 POST，前端改用 POST，所有认证模板加载 CSRF meta/脚本，登录表单含隐藏字段，jQuery/fetch/XHR/原生表单均自动附加 token。
  - 执行 `python -m compileall`、`git diff --check`，均通过。
- **e. 验证是否通过？** 通过（14 项可执行测试通过；所有写请求的统一 CSRF 边界和 GET 删除根因已消除）
- **提交：** fix(HI-06): enforce CSRF on state-changing requests
- **修改文件：** `src/tradingview_zy/web_security.py`, `src/tradingview_zy/config.py.demo`, `web/tradingview_zy_chart/cl_app/__init__.py`, `web/tradingview_zy_chart/cl_app/static/js/csrf.js`, `web/tradingview_zy_chart/cl_app/static/js/alert.js`, `web/tradingview_zy_chart/cl_app/templates/dark.html`, `web/tradingview_zy_chart/cl_app/templates/login.html`, `tests/test_hi06_csrf.py`, `tests/test_web_security.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 当前容器缺少 Flask 及部分 Web 依赖，未运行真实浏览器端到端测试；浏览器覆盖由四种请求机制的静态契约测试和纯 CSRF 核心测试提供。
  - 非浏览器客户端在持有有效会话 token 时允许省略 Origin/Referer；浏览器一旦提供任一来源头，非同源请求即拒绝。
- **原报告最新结论：** 登录与 Cookie 已加强，但状态变更接口仍没有 CSRF token/Origin 校验，删除提醒任务继续使用 GET。
- **原报告建议：** 引入 CSRF 中间件；所有写操作改 POST/DELETE；SameSite 只作纵深防御，不替代 token。

### 13. CR-03 · 实盘订单缺少成交状态机，内部账本可与券商/交易所永久分叉

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 高 / Live Trading
- **本轮状态：** 已完成（通过移除未验收实盘订单执行能力）
- **问题是否存在：** 是
- **a. 这个问题是什么？** 仓库中的 A 股、港股、数字货币、期货和 IB 交易路径没有统一持久化 Order/Fill 状态机。部分代码把本地行情价格、订单提交返回、固定等待后的单次查询、当前无持仓或一笔最终查询当成成交，并在缺少拒单、部分成交、撤单、重复回调、断线和重启对账语义时修改自选、通知成功或写共享订单账本。
- **b. 我是怎么修复的？** 暂不保留不安全的实盘订单执行能力。删除 A/HK/Binance/TQ 四个未验收 live trader；Exchange 基类新增统一 LiveTradingDisabledError，所有 provider 的 order 与撤单入口都委托到同一 fail-closed 边界；移除 IB Redis 订单命令、worker 下单实现和队列消费。保留行情、账户只读查询、研究与回测，并新增恢复实盘所必须满足的持久化状态机、幂等、成交明细和重启对账准入文档。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_cr03_live_trading_disabled.py tests/test_cr04_qmt_trader_removed.py tests/test_cr05_ctp_removed.py tests/test_hi14_tq_lifecycle.py`，13 项测试全部通过。
  - AST 扫描所有 Exchange.order/cancel 方法，确认全部委托统一 fail-closed 边界；基础 Exchange.order 直接抛 LiveTradingDisabledError。
  - 扫描 src/script/web 的 Python 运行树，确认不再含 create_order、place_order、placeOrder、insert_order、unlock_trade 或 CmdEnum.ORDERS 下单入口。
  - 确认 A/HK/Binance/TQ live trader 文件已删除，行情 provider、在线行情辅助和回测订单记录仍保留；执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（13 项专项/相邻测试通过；所有内置实盘订单和撤单入口均明确 fail-closed）
- **提交：** fix(CR-03): disable unreconciled live trading
- **修改文件：** `src/tradingview_zy/exchange/exchange.py`, `src/tradingview_zy/exchange/exchange_*.py`, `src/tradingview_zy/trader/trader_a_stock.py（删除）`, `src/tradingview_zy/trader/trader_currency.py（删除）`, `src/tradingview_zy/trader/trader_futures.py（删除）`, `src/tradingview_zy/trader/trader_hk_stock.py（删除）`, `script/crontab/script_ib_tasks.py`, `docs/live-trading-disabled.md`, `docs/unsupported-providers.md`, `tests/test_cr03_live_trading_disabled.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 本次关闭方式是禁用/移除实盘订单执行，不代表已经实现任何券商或交易所的实盘状态机。
  - 账户余额和持仓等只读接口仍可能访问外部 SDK；其各自可靠性问题在后续对应条目中单独处理。
  - 回测产生的订单记录继续存在，但文档明确其不是券商成交回报。
- **原报告最新结论：** 旧 trader 启动提示脚本已删除，但 QMT/TQ/Binance 等交易类的订单提交、成交确认和重启对账没有改变；状态机缺口仍在。
- **原报告建议：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账；未确认成交必须 fail closed。现有启动器保持禁用，直到每个适配器通过沙箱验收。

### 14. ME-24 · 环境检查与 pyproject 的 Python 约束冲突，并在失败后仍打印“环境OK”

- **原始状态 / 严重度 / 领域：** 🔴 回归（重新出现） / 中 / Environment
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** check_env.py 维护独立的 Python 3.8–3.11 白名单，与 pyproject.toml 的 >=3.11,<3.12 不同源；还导入已弃用并在新 Python 移除的 telnetlib。代理、Redis、MySQL 等检查失败后只打印提示，函数最终仍无条件输出“环境OK”并返回成功，自动化无法区分必需失败和可选降级。
- **b. 我是怎么修复的？** 重写环境检查器：从 pyproject.toml 读取唯一 requires-python 约束并同时执行上下界；用 socket.create_connection 的有限超时替代 telnetlib；依赖按配置惰性导入，网络连接设置明确超时并关闭资源；每项返回结构化 OK/DEGRADED/FAILED，配置的 MySQL或项目导入失败返回非零退出码，可选代理/Redis故障标记 DEGRADED；删除无条件“环境OK”。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_me24_check_env.py`，5 项测试全部通过。
  - 参数化验证 Python 3.10、3.11、3.12、3.13 与 pyproject 的 >=3.11,<3.12 完全一致。
  - 以当前 Python 3.13 真实执行 check_env.py，确认退出码为 1、输出明确 requires-python 不满足且不出现“环境OK”。
  - 验证 DEGRADED 与 FAILED 的退出码和汇总文本不同；确认不再导入 telnetlib，并执行 compileall、git diff --check。
- **e. 验证是否通过？** 通过（5 项专项测试通过；版本契约同源、失败退出码和状态汇总均正确）
- **提交：** fix(ME-24): align environment checks with project metadata
- **修改文件：** `check_env.py`, `tests/test_me24_check_env.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 当前离线容器运行 Python 3.13，因此只能验证检查器正确拒绝；没有在 Python 3.11 里连接真实 Redis/MySQL/代理。
  - 环境检查只支持项目当前使用的逗号分隔比较运算符约束；若未来使用通配符、~= 或环境 marker，需要扩展解析器或引入 packaging 作为直接依赖。
- **原报告最新结论：** PR #15 将包元数据收紧为 Python >=3.11,<3.12，以匹配 cp311-only TA-Lib wheel；但 check_env.py 仍以“>=3.11”为判定，_python_version_supported((3,12,0)) 实测返回 True，并输出“3.11 或更高版本”。
- **原报告建议：** 把环境检查改为同一 SpecifierSet/单一元数据来源，明确拒绝 3.12+；增加 pyproject 与 check_env 契约一致性测试。

### 15. NEW-06 · MarketRegistry 过报 DB provider 的 security_master/plates 能力

- **原始状态 / 严重度 / 领域：** 🆕 新问题（未修复） / 中 / Architecture / Exchange Contract
- **本轮状态：** 已完成（本地不存在，已加防回归）
- **问题是否存在：** 否
- **a. 这个问题是什么？** 远程固定点中的 NEW-06 源于新增 MarketRegistry 把 DB provider 声明为 SECURITY_MASTER/PLATES，但用户上传的本地主代码中没有 market_registry.py，也没有任何 Capability/DB_CAPABILITIES 声明，因此“能力过报”这一确切回归在本地不存在。底层 ExchangeDB 的证券目录和板块方法仍为空/未实现，属于后续 NX-23 与接口能力问题。
- **b. 我是怎么修复的？** 不凭空引入远程注册表。新增 DB provider 能力边界文档，明确当前仅可视为持久化 K 线/派生 tick 数据源，不提供证券主数据或板块能力；新增 AST 防回归门禁：确认本地没有过报注册表，确认三个底层方法仍是未实现状态，并规定未来出现 MarketRegistry 时 DB_CAPABILITIES 不得包含 SECURITY_MASTER/PLATES，除非先补行为级契约。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 全仓查找 market_registry.py、Capability、DB_CAPABILITIES、security_master/plates 声明，确认本地运行树不存在远程过报实现。
  - 运行 `PYTHONPATH=src pytest -q tests/test_new06_db_capability_guard.py`，4 项测试全部通过。
  - AST 检查 ExchangeDB.all_stocks() 返回空集合、stock_owner_plate()/plate_stocks() 未实现；未来注册表出现时自动拒绝 DB 的 SECURITY_MASTER/PLATES 声明。
  - 检查能力边界文档并执行 git diff --check。
- **e. 验证是否通过？** 通过（确切回归在本地不存在；4 项门禁测试防止未来重新过报）
- **提交：** test(NEW-06): guard DB provider capability claims
- **修改文件：** `docs/provider-capabilities.md`, `tests/test_new06_db_capability_guard.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本条没有实现 DB 证券主数据或板块查询；该根因按清单中的 NX-23 和 ME-10 后续处理。
  - 若未来引入新的注册表文件名或动态声明机制，需要同步扩展当前 AST 门禁。
- **原报告最新结论：** DB_CAPABILITIES 被定义为 MARKET_DATA + TICKS + SECURITY_MASTER + PLATES，并用于所有市场的 db provider；但 ExchangeDB.all_stocks() 固定返回空列表，stock_owner_plate() 和 plate_stocks() 为 pass。调用方通过 require_capability 后仍会得到空/None，而不是“能力不支持”。
- **原报告建议：** DB provider 只声明真实实现的 MARKET_DATA/TICKS；或实现安全主数据/板块查询。为每个 Capability 增加行为级契约测试，不能只检查集合存在。

### 16. HI-01 · TraderFutures 使用不存在的构造参数，实例化立即失败

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Futures Trader
- **本轮状态：** 已完成（共享修复已复验）
- **问题是否存在：** 否
- **a. 这个问题是什么？** HI-01 原本位于 TraderFutures：构造时传入 ExchangeTq 不存在的 use_account 参数，直接 TypeError；即使修正构造，平多落库又误用 open_long。CR-03 已将整套未验收 live trader 从运行包移除，因此本地当前不再存在或可达该错误类。
- **b. 我是怎么修复的？** 沿用 CR-03 的安全下线，不重新引入一个仍无订单状态机的 TraderFutures。新增独立防回归测试，确认模块不存在、运行树没有 TraderFutures/trader_futures 引用，也没有 ExchangeTq(use_account=...) 旧构造模式；恢复期货实盘必须按 live-trading-disabled.md 作为新功能重新实现并验证。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_hi01_trader_futures_removed.py tests/test_cr03_live_trading_disabled.py`，7 项测试全部通过。
  - 扫描 src/script/web，确认无 TraderFutures、trader_futures、ExchangeTq(use_account=...)。
  - 确认 CR-03 的所有 Exchange.order 入口继续 fail-closed，恢复要求包含 client_order_id、部分成交与重启对账。
  - 执行 git diff --check。
- **e. 验证是否通过？** 通过（旧构造参数和错误落库类型所在模块已移除；7 项专项/共享门禁通过）
- **提交：** test(HI-01): guard removed futures trader
- **修改文件：** `tests/test_hi01_trader_futures_removed.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本条通过移除未验收 TraderFutures 关闭，不代表 TQ 期货实盘交易已恢复。
  - ExchangeTq 仍可用于行情和只读账户接口；其生命周期修复由 HI-14 覆盖。
- **原报告最新结论：** TraderFutures 虽已传入 market，但仍调用 ExchangeTq(use_account=True)，而构造器参数是 use_simulate_account；直接实例化仍会 TypeError。
- **原报告建议：** 统一构造参数与 order_type；若不支持该 trader，应从运行包删除并加不可达测试。

### 17. ME-06 · 自选导入和导出共用固定 zx.txt，缺少并发隔离与上传限制

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / File Upload
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 自选导出与导入都使用 DATA_PATH/zx.txt；并发请求会相互覆盖或删除同一文件。上传直接 file.save()，再 readlines() 全量读入，没有请求体、字节、行数、单行长度、扩展名或编码限制。
- **b. 我是怎么修复的？** 导出改为请求私有 BytesIO，不再写磁盘临时文件；导入直接从上传二进制流逐行解析，限制总字节、行数、单行字节、UTF-8 编码和 .txt 扩展名，去重并校验代码。Flask 设置 MAX_CONTENT_LENGTH，所有限额可通过 WEB_* 配置调整，错误返回稳定 400/413/422。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_me06_watchlist_transfer.py`，4 项测试全部通过。
  - 并发执行 20 次导出，结果一致且不创建共享 zx.txt；覆盖 BOM、A 股别名、重复与未知代码。
  - 故障测试覆盖总大小、最大行数、最大单行和非法 UTF-8；静态检查路由不再含 file.save/readlines/zx.txt。
  - 执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（4 项专项测试通过；共享文件、无界读取和上传边界根因已消除）
- **提交：** fix(ME-06): isolate and bound watchlist transfers
- **修改文件：** `src/tradingview_zy/watchlist_transfer.py`, `src/tradingview_zy/config.py.demo`, `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_me06_watchlist_transfer.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 当前未运行真实 Flask multipart/浏览器上传；解析器与路由源码契约已离线验证。
  - 逐条 zx.add_stock 仍不是批量事务；本条只处理并发文件隔离和上传资源边界。
- **原报告最新结论：** 自选导出和导入仍共用 data/zx.txt；上传直接 file.save()，没有请求体/文件大小、并发隔离和流式限制。
- **原报告建议：** 每请求临时文件或内存流；MAX_CONTENT_LENGTH；扩展名/编码/行数验证；finally 清理。

### 18. ME-16 · IB Redis 请求使用 BRPOP timeout=0，可无限阻塞调用线程

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Interactive Brokers
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** ExchangeIB.ticks() 使用 Redis BRPOP timeout=0；IB worker 消失、消息丢失或响应未写回时，Web/同步调用线程永久阻塞。历史订单路径也曾使用无限等待，虽已随 CR-03 下线，但行情 RPC 仍需统一有限 deadline 和响应键清理。
- **b. 我是怎么修复的？** 新增 correlation-keyed `redis_rpc`：只接受正数 timeout，向命令队列写入后以向上取整的有限秒数 BRPOP；超时抛 `IBRequestTimeout`，成功/失败都清理响应键，并在请求前清除潜在陈旧响应。ExchangeIB 的 search/klines/ticks/stock_info/balance/positions 全部统一走该 RPC；worker 为迟到响应设置 120 秒 TTL。默认 deadline 通过 IB_RPC_TIMEOUT_SECONDS 配置。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_me16_ib_rpc_timeout.py`，4 项测试全部通过。
  - Fake Redis 故障注入验证无响应在有限 timeout 后抛明确 TimeoutError，队列前后均清理 correlation key。
  - 成功响应验证 JSON 解码与清理；0/负 timeout 在入队前拒绝。
  - 静态检查 ExchangeIB 不再含 timeout=0/BRPOP 0，worker 对响应键设置 TTL；执行 compileall、git diff --check。
- **e. 验证是否通过？** 通过（4 项专项测试通过；所有 IB 客户端 RPC 均使用有限 deadline）
- **提交：** fix(ME-16): bound IB Redis RPC waits
- **修改文件：** `src/tradingview_zy/exchange/ib_rpc.py`, `src/tradingview_zy/exchange/exchange_ib.py`, `script/crontab/script_ib_tasks.py`, `src/tradingview_zy/config.py.demo`, `tests/test_me16_ib_rpc_timeout.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 未连接真实 Redis/IB worker；使用行为等价 Fake Redis 验证 deadline、清理和解码。
  - worker 在客户端超时后仍可能完成外部 IB 请求，但迟到响应键有 TTL，不会永久泄漏；主动取消 IB API 调用需要独立 worker 协议扩展。
- **原报告最新结论：** ExchangeIB.ticks() 仍 BRPOP timeout=0，order 路径也存在 0 超时；调用线程可永久阻塞。
- **原报告建议：** 统一有限 deadline、取消/清理响应键、明确 TimeoutError，并覆盖 Redis 无响应测试。

### 19. ME-05 · create_app 启动时 eager 实例化全部配置市场，单个可选适配器可拖垮整个服务

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web Startup
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** create_app 在注册路由前为 8 个市场逐一调用 get_exchange().support_frequencys()/default_code()。任一可选 SDK 缺失、账号未配置、网络连接失败或构造器阻塞都会拖垮整个 Web 服务，即使用户只需要其他市场。
- **b. 我是怎么修复的？** 新增零副作用 market_metadata 模块，集中提供 Web 展示所需的市场默认代码和保守周期集合；create_app 只读取该静态数据，不导入或构造任何 provider。具体 provider 继续在实际市场请求时惰性 get_exchange，使单个市场故障不会阻断应用创建。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_me05_lazy_web_startup.py`，3 项测试全部通过。
  - 验证 8 个市场静态元数据完整且返回副本，模块不导入 exchange、SDK 或 get_exchange。
  - 静态检查 create_app 的启动元数据区块不再调用 get_exchange。
  - 执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项专项测试通过；应用启动元数据不再实例化任何外部适配器）
- **提交：** fix(ME-05): remove provider construction from app startup
- **修改文件：** `src/tradingview_zy/market_metadata.py`, `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_me05_lazy_web_startup.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 静态周期集合是市场级保守元数据，不代表每个配置 provider 的全部独有周期；provider 级能力将在 ME-10/ME-03 中继续收敛。
  - 当前离线镜像缺 Flask/APScheduler，未动态创建完整 app；启动调用图由源码契约测试验证。
- **原报告最新结论：** create_app() 启动阶段仍对全部市场调用 get_exchange().support_frequencys()/default_code()，单个可选 provider 失败仍可阻断整个 Web 服务。
- **原报告建议：** 注册表提供静态元数据；provider 按请求惰性实例化；可选市场失败降级为该市场不可用。

### 20. MX-01 · 钉钉配置契约破裂且 HK 分支永不可达

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Configuration / Messaging
- **本轮状态：** 已完成（通过移除废弃能力）
- **问题是否存在：** 是
- **a. 这个问题是什么？** utils.py 的钉钉配置函数引用配置模板中不存在的 DINGDING_KEY_*，HK 分支又重复判断 market == 'a'，因此即使补配置也不可达。代码注释已说明旧 API 下架，全仓只有函数定义和两条注释掉的调用，当前实际消息通道是飞书。
- **b. 我是怎么修复的？** 删除废弃的 config_get_dingding_keys/send_dd_msg、其专用加密/HTTP imports 和注释调用，避免继续暴露破裂配置契约。保留飞书接口；新增消息通道文档，规定任何新通道必须有类型化配置、显式启停、有限 HTTP timeout、状态校验、秘密脱敏与逐市场路由测试。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_mx01_dingding_removed.py`，3 项测试全部通过。
  - 扫描 src/script/web，确认无 send_dd_msg、config_get_dingding_keys 或 DINGDING_KEY_*。
  - 确认 send_fs_msg/config_get_feishu_keys 仍保留。
  - 执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项专项测试通过；破裂钉钉配置与不可达 HK 分支已从运行树移除）
- **提交：** fix(MX-01): remove broken DingTalk integration
- **修改文件：** `src/tradingview_zy/utils.py`, `script/crontab/reboot_sync_gm_a_klines.py`, `script/crontab/reboot_sync_gm_futures_klines.py`, `docs/messaging-channels.md`, `tests/test_mx01_dingding_removed.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 本条选择移除钉钉，不提供钉钉消息兼容层；外部私有脚本若曾调用该未声明接口，需要迁移飞书或自行实现受支持通道。
  - 飞书 HTTP/SDK 可靠性与配置副作用在 NX-03、ME-22 中继续处理。
- **原报告最新结论：** 最新配置模板仍没有 DINGDING_KEY_*，utils.py 也未修改；配置契约和 HK 分支问题仍在。
- **原报告建议：** 若已废弃钉钉，应删除接口和死配置分支；若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。

### 21. MX-06 · 直接执行 db.py 会向配置数据库写测试标记

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Database / Operations
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** db.py 文件末尾保留可执行 demo main block，其中唯一未注释的 db.marks_add_by_price() 会在运维、IDE 或调试命令直接运行模块时向当前配置数据库写入固定测试标记。
- **b. 我是怎么修复的？** 删除整个可执行 demo main block及其历史注释示例；保留生产 DB 类和模块级 db 单例。数据库 smoke/demo 操作只能放在使用临时数据库的 pytest 中，不再从生产模块直接执行。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_mx06_db_module_safe.py`，3 项测试全部通过。
  - AST 确认 db.py 顶层不再存在 __main__ 条件块。
  - 静态确认无测试标记文本或 db.marks_add_by_price 调用，同时生产 `db: DB = DB()` 保留。
  - 执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项专项测试通过；直接执行文件不再触发测试业务写入）
- **提交：** fix(MX-06): remove executable database demo writes
- **修改文件：** `src/tradingview_zy/db.py`, `tests/test_mx06_db_module_safe.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - db.py import 时仍创建 DB 实例/schema，这是与本条不同的模块导入副作用，后续架构/数据库条目继续处理。
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 删除全部可执行测试写入；数据库 smoke test 移到临时 SQLite pytest fixture。模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。

### 22. MX-02 · ZB 被配置文档声明支持，但工厂无法选择

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Exchange Factory
- **本轮状态：** 已完成（通过移除不支持能力）
- **问题是否存在：** 是
- **a. 这个问题是什么？** 配置模板把 ZB 列为数字货币合约 provider，但标准工厂从未注册 zb；遗留 exchange_zb.py 只能被直接导入，并显式关闭 TLS 证书校验。因此文档支持矩阵、工厂可选项与运行包能力互相矛盾。
- **b. 我是怎么修复的？** 从配置模板和本地运行配置移除 zb 支持声明与 ZB 密钥项；删除孤立 ExchangeZB 运行时代码；在统一工厂为旧 EXCHANGE_CURRENCY=zb 配置增加导入/缓存前 fail-closed 错误；补充不支持 provider 文档与防回归测试。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_mx02_zb_removed.py tests/test_cr05_ctp_removed.py`，7 项测试全部通过。
  - 动态将 EXCHANGE_CURRENCY 设为 zb，确认抛 UnsupportedProviderError，未导入 exchange_zb 且未污染 exchange cache。
  - 扫描 src/script/web，确认无 exchange_zb 或 ccxt.zb 运行时引用；配置模板不再包含 zb/ZB_APIKEY/ZB_SECRET。
  - 执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（4 项 MX-02 专项测试及 3 项相邻 provider 下线测试通过；支持声明与可选工厂已一致）
- **提交：** fix(MX-02): remove unsupported ZB provider
- **修改文件：** `src/tradingview_zy/config.py.demo`, `src/tradingview_zy/exchange/__init__.py`, `src/tradingview_zy/exchange/exchange_zb.py（删除）`, `docs/unsupported-providers.md`, `tests/test_mx02_zb_removed.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本条选择正式移除 ZB，不提供旧 API 兼容层；外部私有脚本必须迁移到 binance/db。
  - 本地部署用 config.py 被 .gitignore 排除，但已同步清除旧 ZB 项；可版本化契约以 config.py.demo 为准。
- **原报告最新结论：** config.py.demo 仍声明数字货币支持 binance / zb / db；MarketRegistry/工厂只有 binance 与 db，zb 配置仍不可选择。
- **原报告建议：** 从配置与文档删除 zb，或重新实现并注册；支持矩阵必须由注册表自动生成。

### 23. MX-04 · ExchangeDB.now_trading 返回 None，Python 与前端调用方对三态结果解释不一致

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / ExchangeDB / Scheduling
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** ExchangeDB.now_trading() 只有 pass，实际返回 None。Python 监控与 history 路由用 `is False`，会把 None 当成继续运行；前端把 JSON null 通过 `!== true` 当成停止，形成同一 provider 的相反三态语义。
- **b. 我是怎么修复的？** 把 ExchangeDB.now_trading() 改为带 bool 返回标注的明确 fail-closed `False`。DB provider 能读取存储行情，但没有权威交易所日历或实时 session feed，因此不得把未知状态伪装为正在交易；Python 调度、history 和前端现在都得到一致布尔语义。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_mx04_exchange_db_trading_state.py`，3 项测试全部通过。
  - AST 验证 now_trading 具有 `-> bool`、唯一 `return False`，且无 pass/None 返回。
  - 隔离编译并动态调用实际方法节点，确认结果严格为 `False` 且 `type(result) is bool`。
  - 静态核对 alert/history/前端调用方均以 false/非 true 停止，执行 compileall 与 git diff --check。
- **e. 验证是否通过？** 通过（3 项专项测试通过；DB provider 不再暴露 None/null 三态）
- **提交：** fix(MX-04): make DB trading state explicit
- **修改文件：** `src/tradingview_zy/exchange/exchange_db.py`, `tests/test_mx04_exchange_db_trading_state.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 返回 False 是保守的未知状态策略，不等同于实现完整交易所日历；各市场节假日、午休、夜盘与 DST 由 ME-30 后续处理。
  - DB provider 仍可随时读取历史 K 线；本变更只影响是否触发近实时轮询/监控。
- **原报告最新结论：** ExchangeDB.now_trading() 仍为 pass，返回 None；Python 与前端对 None/null 的解释仍不统一。
- **原报告建议：** 返回严格 bool 或显式 UnsupportedCapabilityError；调用方不得把 None 当作交易中。

### 24. MX-05 · 自选涨跌幅轮询把函数返回值交给 setInterval

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Frontend
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** index.html 在页面初始化和自选面板展开时都调用 `setInterval(ZiXuan.stocks_update_rate(), 30000)`。这会先立即执行函数，再把其返回值（通常为 undefined/true）交给定时器，因此没有可周期调用的回调；重复展开还可能遗留多个 timer。
- **b. 我是怎么修复的？** 新增 `start_rate_update_timer()` / `stop_rate_update_timer()`。启动时先清理旧 timer，立即刷新一次，再把真正的函数回调交给 setInterval；页面初始化和折叠面板生命周期统一使用这两个 helper，并在停止后清空句柄。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `pytest -q tests/test_mx05_rate_timer.py`，3 项专项测试全部通过。
  - 静态断言模板中不再存在 `setInterval(ZiXuan.stocks_update_rate())` 立即调用反模式。
  - 使用 Node fake timer 执行从真实模板提取的 start/stop helper，验证首次立即刷新、30 秒回调可执行、重复启动会清理旧 timer、停止会清空句柄。
  - 对模板中所有无 src 的内联脚本完成 Jinja 占位替换后交给 Node `new Function` 编译，确认 JavaScript 语法有效；执行 `git diff --check`。
- **e. 验证是否通过？** 通过（3 项专项测试通过；定时回调、重启清理和停止语义均通过 Node 动态验证）
- **提交：** fix(MX-05): schedule watchlist rate refresh correctly
- **修改文件：** `web/tradingview_zy_chart/cl_app/templates/index.html`, `tests/test_mx05_rate_timer.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 未启动完整 Layui/TradingView 浏览器页面；定时器核心行为已在 Node fake timer 中动态验证，完整 UI 展开/收起交互仍建议在部署环境做一次浏览器烟雾测试。
- **原报告最新结论：** index.html 仍把 ZiXuan.stocks_update_rate() 的返回值传给 setInterval，函数立即执行而定时器没有回调。
- **原报告建议：** 传函数引用/箭头函数，并用前端定时器测试验证周期调用。

### 25. MX-17 · TDX 节点选优在缓存缺失或重置时串行探测全部候选，缺少总体 deadline

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / TDX / Performance
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** TDX 节点选优通过列表推导串行探测所有候选。缓存缺失、过期或 reset 时，总延迟会按候选数累加；即使单个 SDK 探测卡住，也没有调用级总体 deadline。节点缓存还永久有效，无法定期重新验证健康状态。
- **b. 我是怎么修复的？** 新增独立 `select_fastest_node`：以有界 daemon worker 并发探测，在一个全局 3 秒 wall-clock budget 内收集健康结果，按延迟和原始顺序稳定选优，单节点异常被隔离，无健康节点时抛出可解释的 `NodeSelectionError`。所有 TDX 适配器写入节点缓存时增加 6 小时绝对 TTL。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 运行 `PYTHONPATH=src pytest -q tests/test_mx17_tdx_node_selection.py`，6 项专项测试全部通过。
  - 用 12 个延迟探针验证并发度至少为 4，耗时显著低于串行总和，并确认最快健康节点胜出。
  - 故障注入一个快速成功节点和多个违反自身 timeout 的挂起节点，确认调用在全局 deadline 内返回；全部挂起时在 deadline 内抛出包含完成数量的明确错误。
  - AST 检查 6 个 TDX 适配器的节点缓存均传入 `expire=best_ip.cache_expiry_epoch()`；运行 NX-20 相邻重试测试、compileall 与 `git diff --check`。
- **e. 验证是否通过？** 通过（6 项专项测试及相邻 NX-20 测试通过；冷启动/重置扫描具有并发上限、全局 deadline 与有限缓存 TTL）
- **提交：** fix(MX-17): bound and parallelize TDX node selection
- **修改文件：** `src/tradingview_zy/tools/tdx_best_ip.py`, `src/tradingview_zy/tools/tdx_node_selector.py`, `src/tradingview_zy/exchange/exchange_tdx.py`, `src/tradingview_zy/exchange/exchange_tdx_hk.py`, `src/tradingview_zy/exchange/exchange_tdx_futures.py`, `src/tradingview_zy/exchange/exchange_tdx_us.py`, `src/tradingview_zy/exchange/exchange_tdx_fx.py`, `src/tradingview_zy/exchange/exchange_tdx_ny_futures.py`, `tests/test_mx17_tdx_node_selection.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 未对真实公网 TDX 候选做网络基准；探测并发、deadline、错误隔离和缓存 TTL 已用确定性故障注入验证。
  - 缓存过期后仍在请求线程同步刷新，但刷新总耗时被严格限制为默认 3 秒；项目当前没有适合承载后台节点健康刷新的独立生命周期服务。
- **原报告最新结论：** TDX 选优和各 TDX 构造器没有修改；Web 文件的安全变更不影响串行探测和总体 deadline。
- **原报告建议：** 并发有界探测；设置全局 deadline、最小成功数和 TTL 健康缓存；后台刷新而非阻塞请求。

### 26. NX-08 · POSITION.get_close_profit 会修改调用方传入列表

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Backtesting Model
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** POSITION.get_close_profit() 把调用方传入的 uids 列表直接交给私有查询方法；该方法为加入兜底记录执行 `uids.append("clear")`。同一列表被复用时会被静默污染，影响后续过滤、缓存键和错误信息。
- **b. 我是怎么修复的？** 私有查询方法现在先构造局部 `set(uids)` 副本，再在副本中加入 `clear`；所有成员判断与错误信息都使用局部集合，调用方容器在成功、fallback、重复调用和异常路径中保持不变。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前运行最小复现，确认输入 `["uid-a"]` 在调用后变为 `["uid-a", "clear"]`。
  - 运行 `pytest -q tests/test_nx08_position_close_profit.py`，3 项专项测试全部通过。
  - 覆盖指定 uid 命中、缺失 uid 自动使用 clear fallback、clear 也缺失时抛错；每条路径都断言原输入列表不变，并验证同一列表重复调用无状态泄漏。
  - 执行 `python -m compileall` 针对实现与测试文件，并运行 `git diff --check`。
- **e. 验证是否通过？** 通过（3 项专项测试通过；成功、fallback、重复调用和异常路径均不再修改调用方列表）
- **提交：** fix(NX-08): keep close-profit queries side-effect free
- **修改文件：** `src/tradingview_zy/backtesting/base.py`, `tests/test_nx08_position_close_profit.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 容器缺失 `empyrical`，相邻 `tests/test_backtesting_base_generic.py` 在收集阶段被阻断；本条专项测试仅导入 POSITION，完整覆盖该副作用根因且不需要绩效库。
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/base.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 复制输入或使用不可变 tuple/set。

### 27. NX-03 · 飞书配置读取会原地修改全局默认字典

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Configuration / Messaging
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** config_get_feishu_keys() 直接把 `config.FEISHU_KEYS[market]` 或 default 子字典赋给局部变量，再执行 `keys["user_id"] = ...`。局部变量和全局配置指向同一对象，因此一次读取就会污染全局默认值，返回值被调用方修改时也会继续回写。
- **b. 我是怎么修复的？** 先通过 `FEISHU_KEYS.get()` 选择来源映射，再用 `dict(source)` 创建独立副本；user_id 只写入副本并返回。数据库覆盖分支继续构造新的规范化字典，同时为函数补充 `str -> dict[str, str]` 类型契约。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前 AST 检查确认函数对从 FEISHU_KEYS 取得的映射执行下标赋值。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx03_feishu_config_copy.py`，3 项专项测试全部通过。
  - 分别验证市场专用配置、未知市场 default fallback 和数据库覆盖；修改返回值并重复/跨市场调用后，全局配置与缓存输入均保持原样。
  - 执行实现与测试 compileall、相邻消息通道静态测试及 `git diff --check`。
- **e. 验证是否通过？** 通过（3 项专项测试通过；所有配置来源均返回独立映射，不再污染全局默认字典）
- **提交：** fix(NX-03): avoid mutating global Feishu config
- **修改文件：** `src/tradingview_zy/utils.py`, `tests/test_nx03_feishu_config_copy.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 当前 FEISHU_KEYS 子项是扁平字符串映射，因此浅拷贝足够；若未来加入嵌套可变配置，应改用不可变配置模型或显式深拷贝。
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/utils.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 返回 `dict(source)` 副本，使用不可变配置对象。

### 28. NX-22 · db.py import 时全局关闭所有 warnings

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Database / Diagnostics
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** src/tradingview_zy/db.py 在模块顶层执行 `warnings.filterwarnings("ignore")`。warnings 过滤器是进程全局状态，因此只要导入数据库模块，SQLAlchemy、pandas、弃用警告以及其他业务模块的 UserWarning 都可能被静默吞掉。
- **b. 我是怎么修复的？** 删除 db.py 中未限定类别、模块或作用域的 warnings import 和全局 ignore 调用。数据库模块本身没有需要压制的已知警告；其他模块已有的 `catch_warnings` 局部精确过滤保持不变。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前 AST 检查确认 db.py 顶层存在 `warnings.filterwarnings("ignore")`。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx22_db_warning_scope.py tests/test_mx06_db_module_safe.py tests/test_remediation_report_counts.py`，6 项专项、相邻和报告测试全部通过。
  - 在隔离子进程中先设置 `UserWarning` 为 error，再真实执行 tradingview_zy.db 的 SQLAlchemy/SQLite 导入初始化；导入后 sentinel UserWarning 仍被抛出。容器缺少可选 tzlocal，因此测试只为该导入提供返回 UTC 的最小兼容 stub，并把 HOME 指向临时目录。
  - AST 断言 db.py 不再导入 warnings 或调用顶层 filterwarnings；执行 compileall 和 `git diff --check`。
- **e. 验证是否通过？** 通过（6 项专项、相邻及报告测试通过；数据库模块不再覆盖进程 warning 策略）
- **提交：** fix(NX-22): preserve process warning policy on DB import
- **修改文件：** `src/tradingview_zy/db.py`, `tests/test_nx22_db_warning_scope.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 容器缺少项目锁文件声明的 tzlocal，动态导入测试使用只返回 UTC 的最小兼容 stub；数据库模块、SQLAlchemy 和 SQLite 初始化均为真实代码。
  - 未来若发现特定第三方无害警告，应只在对应调用点按 category/module/message 局部过滤。
- **原报告最新结论：** src/tradingview_zy/db.py 模块级仍执行 warnings.filterwarnings("ignore")，会全局吞掉与数据库无关的警告。
- **原报告建议：** 删除全局 ignore；仅在已知第三方调用点使用精确 category/module/message 过滤。

### 29. NX-21 · MySQL DSN 直接字符串插值，特殊字符密码会破坏 URL

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Database Configuration
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** DB.__init__ 通过 f-string 直接拼接 `mysql+pymysql://user:password@host:port/database`。用户名、密码或数据库名包含 @、:、/、%、#、?、空格等 URL 保留字符时会被误解析；完整 DSN 进入异常文本时还可能暴露凭据。
- **b. 我是怎么修复的？** 新增纯函数 `build_mysql_url()`，用 SQLAlchemy `URL.create` 分字段传入 driver、用户名、密码、主机、端口、数据库和 charset；MySQL create_engine 路径只接收结构化 URL。URL 默认字符串渲染自动把密码隐藏为 `***`。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前 AST 检查确认 DB 构造器包含 `mysql+pymysql://` 的 JoinedStr/f-string。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx21_mysql_url.py`，3 项专项测试全部通过。
  - 以包含 @、:、/、%、#、?、& 和空格的用户名/密码/数据库名构造 URL，再用 SQLAlchemy make_url 解析，确认所有原值、端口和 charset 完整 round-trip。
  - 验证 `str(URL)` 不含明文密码且显示 `***`；AST 确认 DB.__init__ 调用结构化 builder，不再拼接 MySQL DSN；执行 compileall、DB 相邻测试和 `git diff --check`。
- **e. 验证是否通过？** 通过（3 项专项测试及相邻 DB 测试通过；特殊字符凭据可正确解析且默认字符串脱敏）
- **提交：** fix(NX-21): build MySQL URLs without credential interpolation
- **修改文件：** `src/tradingview_zy/db.py`, `tests/test_nx21_mysql_url.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 未连接真实 MySQL 服务；URL 编码、解析和 create_engine 入参契约由 SQLAlchemy 2.x 的真实 URL/make_url 实现验证。
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。

### 30. NX-23 · ExchangeDB.all_stocks() 永远为空，与“db 可作为 Web 数据源”冲突

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / ExchangeDB
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** ExchangeDB 可以读取已持久化的 K 线，但 `all_stocks()` 固定返回空列表。因此 Web 搜索、自选导入和全市场选股在 DB provider 下会把真实存在的行情数据解释成“没有任何标的”，形成静默能力冲突。
- **b. 我是怎么修复的？** 新增只读数据库目录发现器：通过 SQLAlchemy inspector 只枚举当前市场前缀的 K 线分区表，用反射 Table 和 DISTINCT code 安全读取、去空、去重并排序；DB 增加 `klines_codes()`，ExchangeDB.all_stocks() 将代码映射为既有 `{code, name}` 契约。同步调整 NEW-06 行为门禁：允许这种持久化代码目录，但继续禁止把它过报为含发行人名称、上市状态或板块关系的权威 security master。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前直接调用与源码检查确认 `ExchangeDB.all_stocks()` 无条件返回 `[]`，即使数据库存在 K 线记录也不会查询。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx23_exchange_db_catalog.py tests/test_new06_db_capability_guard.py tests/test_nx21_mysql_url.py tests/test_mx04_exchange_db_trading_state.py tests/test_nx22_db_warning_scope.py tests/test_remediation_report_counts.py`，17 项专项、相邻、能力边界和报告测试全部通过。
  - 在内存 SQLite 中建立两个 A 股分区、一个港股分区和一个缺少 code 列的同前缀表，确认按市场隔离、忽略非 K 线表、跨分区去重并稳定排序。
  - 在隔离子进程中使用真实项目 DB/SQLAlchemy/SQLite 路径插入 SH.600000 与 SH.600001 K 线，再实例化 ExchangeDB('a')，端到端确认 all_stocks 返回两只标的。
  - NEW-06 门禁验证 all_stocks 只能返回 code/name=code 的持久化目录，板块方法仍未实现，未来 registry 仍不得声明 SECURITY_MASTER/PLATES；同时验证空市场拒绝、compileall 与 `git diff --check`。
- **e. 验证是否通过？** 通过（17 项专项、相邻、能力边界及报告测试通过；DB provider 可恢复持久化标的目录且未过报证券主数据能力）
- **提交：** fix(NX-23): discover DB-backed instrument universe
- **修改文件：** `src/tradingview_zy/database_catalog.py`, `src/tradingview_zy/db.py`, `src/tradingview_zy/exchange/exchange_db.py`, `docs/provider-capabilities.md`, `tests/test_nx23_exchange_db_catalog.py`, `tests/test_new06_db_capability_guard.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 数据库当前只持久化 K 线 code，不含权威证券名称、上市/退市状态或板块关系；返回对象因此以 code 同时作为 name，文档和 NEW-06 门禁禁止把该行为过报为完整 SECURITY_MASTER/PLATES 能力。
  - 未连接真实 MySQL；表枚举、标识符引用和 DISTINCT 查询使用 SQLAlchemy inspector/reflection，由 SQLite 端到端与 SQLAlchemy 跨方言契约验证。
- **原报告最新结论：** ExchangeDB.all_stocks() 仍固定返回 []，与 db 可作为 Web provider 及新增 SECURITY_MASTER 能力声明冲突。
- **原报告建议：** 实现证券主数据表/查询，或撤销 security_master 能力并让依赖该能力的页面明确不可用。

### 31. NX-16 · /ticks 可提交无上限代码数组并同步扇出到数据源

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web Security / Availability
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 原 `/ticks` 路由把客户端提供的 `codes` JSON 直接交给 `ex.ticks(codes)`：没有数组类型、空值、原始数量、单代码长度、重复值、请求速率或 provider 等待时间边界。攻击者或误操作可让单个同步请求扇出大量第三方行情调用；provider 卡住时还会长期占用 Web worker。
- **b. 我是怎么修复的？** 新增集中式 tick 请求契约：在构造 provider 前验证市场与 JSON 数组，限制原始数组数量和单代码 UTF-8 字节数，拒绝空值、非字符串和控制字符，并按首次出现顺序去重；增加线程安全、键目录有界的滑动窗口限流；用有界 daemon 调用槽为同步 provider 增加总 deadline，超时调用最多占用固定槽位，容量耗尽时新请求快速失败。路由分别返回 422、429、502、503、504，所有阈值在配置模板中可调。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前读取 `/ticks` 路由，确认 JSON 解析后直接同步调用 provider，没有数量、去重、长度、速率或 deadline 检查。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx16_tick_request_limits.py tests/test_me05_lazy_web_startup.py tests/test_remediation_report_counts.py`，20 项专项、相邻惰性启动和报告测试全部通过。
  - 解析器覆盖非数组、空数组、超量、超长、非字符串、控制字符、前后空白与稳定去重；原始数组数量在去重前受限。
  - 以 20 个并发线程验证同一限流键严格只有 5 次通过，并确认限流键目录保持有界。
  - 真实线程故障注入验证 provider 总 deadline、daemon worker、最大并发槽、超时后快速 busy 拒绝，以及阻塞调用返回后的槽位恢复。
  - 源码契约检查确认请求校验在 `get_exchange` 前执行，provider 调用通过 `BoundedProviderCaller`；执行 compileall、CRLF 字节计数和 `git diff --check`。
- **e. 验证是否通过？** 通过（20 项专项及相邻测试通过；输入扇出、请求速率、provider 并发和等待时间均有明确上限）
- **提交：** fix(NX-16): bound tick fanout and provider waits
- **修改文件：** `src/tradingview_zy/tick_request.py`, `src/tradingview_zy/config.py.demo`, `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_nx16_tick_request_limits.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 限流器是单进程边界；多 worker 部署仍应在反向代理或共享存储中聚合全局速率。
  - Python 无法强制取消任意阻塞的第三方同步 SDK。超时 worker 会以 daemon 线程继续到 SDK 返回，但总数受固定并发槽严格限制；槽满后新请求返回 503，不会无限创建线程。
  - 未连接真实行情 provider；故障时序由真实线程、信号量和可控 fake provider 注入验证。
- **原报告最新结论：** Web 安全改动没有为 /ticks 增加代码数量、去重、长度或 provider 批量上限。
- **原报告建议：** 限制 symbol 数、去重、请求超时和速率；批量上限按 provider 能力。

### 32. NX-14 · 读取不存在的 chart/template 会直接解引用 None

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web Storage
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 图表和指标模板读取路由假设数据库查询必定返回对象，随后直接访问 `chart.content`、`template.name` 等属性。不存在、已删除、错误主体或畸形 chart ID 会得到 `None` 或数据库类型错误，最终表现为 500，而不是稳定的资源不存在/参数错误响应。
- **b. 我是怎么修复的？** 新增无 Web 框架依赖的参数校验器，严格接受正整数 chart ID 和非空短文本模板名。charts 的 GET、DELETE 和已有图表更新路径统一在数据库/请求体处理前校验 ID；GET 查询为空返回 `chart_not_found`/404。study_templates 的 GET、DELETE 统一校验名称，GET 查询为空返回 `template_not_found`/404；既有列表和成功读取响应结构保持不变。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前源码确认 `db.tv_chart_get()` 与 `db.tv_chart_get_by_name()` 返回值未做 None 检查，路由立即解引用属性。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx14_storage_not_found.py tests/test_nx16_tick_request_limits.py tests/test_remediation_report_counts.py`，37 项专项、相邻输入边界和报告测试全部通过。
  - 参数测试覆盖 None、bool、0、负数、小数、前导零、空白、控制字符和超长模板名；合法 ID 与模板名按规范化值返回。
  - 源码顺序契约确认 chart ID 校验发生在数据库查询前，已有图表更新在读取表单字段前校验；chart/template 查询为空分别返回稳定 404。
  - 验证列表与成功读取响应结构保持不变；执行 compileall、CRLF 字节计数（bare-LF=0）和 `git diff --check`。
- **e. 验证是否通过？** 通过（37 项专项与相邻测试通过；不存在资源稳定返回 404，畸形标识在数据库访问前返回 422）
- **提交：** fix(NX-14): return stable storage not-found responses
- **修改文件：** `src/tradingview_zy/web_api_validation.py`, `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_nx14_storage_not_found.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 本轮以真实路由函数的 AST 隔离动态执行验证响应分支；完整 Flask/TradingView 浏览器集成仍由后续 Web API 统一契约回归覆盖。
- **原报告最新结论：** 图表/模板读取路由没有补 None/404 处理，相关 ORM 查询未变。
- **原报告建议：** None 返回 404/规范 UDF 错误；校验 ID 类型。

### 33. NX-15 · 绘图保存异常被吞掉并始终返回 status ok

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web Storage
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** `/tv/<version>/drawings` 的 POST 路径在数据库保存抛异常时只打印 traceback，随后无条件返回 `{status: ok}`；缺少必填字段时也返回成功。前端因此会把未持久化的绘图当作已保存，刷新后数据消失且没有可重试、可关联的错误信息。
- **b. 我是怎么修复的？** 保存前显式检查 client、user、chart、layout 和 state，缺失时返回 `invalid_drawing_request`/422 且不写数据库。保存调用必须得到严格 `True` 确认；异常、False 或 None 均返回 `drawing_save_failed`/500，并生成 request_id 写入结构化应用日志与响应，方便定位。只有确认提交成功才返回 `{status: ok}`；GET 加载契约保持不变。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前源码确认保存异常被捕获后仍执行无条件成功返回，缺少必填字段同样返回成功。
  - 运行 `PYTHONPATH=src pytest -q tests/test_nx15_drawing_save_errors.py tests/test_nx14_storage_not_found.py tests/test_remediation_report_counts.py`，26 项专项、相邻存储和报告测试全部通过。
  - 从真实 Flask 源文件 AST 提取并动态执行 `tv_drawings`：数据库严格返回 True 时保持原成功响应，并核对六个保存参数。
  - 故障注入 RuntimeError，确认返回 500、响应与 logger.exception 使用同一 32 位 request_id，且不泄露底层异常文本。
  - 分别让数据库返回 False 与 None，确认均返回 500；缺失 layout/state 返回 422 且数据库零调用；GET 加载契约未改变。
  - 执行 compileall、CRLF 字节计数（bare-LF=0）和 `git diff --check`。
- **e. 验证是否通过？** 通过（26 项专项与相邻测试通过；异常、未确认结果和缺参不再返回伪成功）
- **提交：** fix(NX-15): report drawing persistence failures
- **修改文件：** `web/tradingview_zy_chart/cl_app/__init__.py`, `tests/test_nx15_drawing_save_errors.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 本轮以真实路由函数和可控数据库故障注入验证；未运行完整 TradingView 浏览器，但 HTTP 状态与 JSON 响应契约已动态执行。
- **原报告最新结论：** 绘图保存的宽泛异常捕获和无条件成功返回未被本轮修改。
- **原报告建议：** 返回 4xx/5xx 与 request_id；仅幂等成功返回 ok。

### 34. RV-05 · 多进程回测允许省略 save_file，但 run_by_code 无条件对 None 调 split()

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Backtesting / Process
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** BackTest 把 `save_file` 作为可选配置，但 `run_process()` 没有在主进程验证；worker 的 `run_by_code()` 首句无条件执行 `self.save_file.split(".pkl")`。省略 save_file 的合法单进程配置切换到多进程后会在子进程中以 AttributeError 失败，错误晚且难定位；字符串 split 还会误截断名称中含 `.pkl` 的父目录。
- **b. 我是怎么修复的？** 新增独立的多进程输出路径契约：None、空白和目录路径立即抛出明确 `ProcessOutputConfigurationError`；`run_process()` 在创建 ProcessPoolExecutor 前验证并创建父目录。每个标的输出路径改用 pathlib 和受限代码文件名生成，不再对完整路径做字符串 split；`run_by_code()` 仍在直接调用时确保父目录存在。普通单进程回测继续允许不保存。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前源码确认构造器允许 `save_file=None`，而 `run_by_code()` 无条件 `.split()`，`run_process()` 在创建进程池前没有校验。
  - 运行 `PYTHONPATH=src pytest -q tests/test_rv05_process_save_file.py tests/test_nx15_drawing_save_errors.py tests/test_remediation_report_counts.py`，18 项专项、相邻和报告测试全部通过。
  - 纯函数覆盖 None、空白、非路径、已有目录、父目录名含 `.pkl`、多后缀、危险/空代码名和父目录自动创建。
  - 源码顺序契约确认 `prepare_process_output_base()` 在 `ProcessPoolExecutor` 前执行，worker 使用 pathlib 构造路径且不再对完整路径 `.split(".pkl")`。
  - 执行 compileall、CRLF 字节计数（bare-LF=0）和 `git diff --check`。
- **e. 验证是否通过？** 通过（18 项专项与相邻测试通过；缺少保存路径在主进程明确失败，合法路径安全生成）
- **提交：** fix(RV-05): validate process backtest output paths
- **修改文件：** `src/tradingview_zy/backtesting/process_output.py`, `src/tradingview_zy/backtesting/backtest.py`, `tests/test_rv05_process_save_file.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 容器缺失 empyrical/pyfolio 等完整回测依赖，因此未启动真实 ProcessPoolExecutor 执行完整历史回测；主进程终止顺序和 worker 路径通过真实方法 AST 动态执行与依赖无关路径模块验证。
- **原报告最新结论：** 年化修复没有触及多进程 save_file 契约；可选配置与 worker 无条件 split() 的冲突仍在。
- **原报告建议：** 主进程提前要求 save_file，或自动创建安全临时目录；不要在 worker 内才发现。

### 35. RV-04 · 盈亏为 0 的平仓被计入失败交易

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Backtesting Metrics
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** 平仓统计只有 `profit > 0` 与 `else` 两个分支，因此 `profit == 0` 以及浮点计算产生的极小正负噪声都会增加 `loss_num`。这会系统性压低胜率、放大失败次数和平均亏损，并把保本交易错误展示为亏损。
- **b. 我是怎么修复的？** 为统计结果增加独立 `flat_num`，并使用绝对容差 1e-9 将接近零的收益归类为持平；严格正收益计胜、严格负收益计亏。新建和动态信号结果都包含 flat_num，旧 pickle/旧结果字典在下一次统计时自动补字段。结果表与汇总增加“持平”列，总交易数包含持平；胜率继续按有方向结果 win/(win+loss) 计算，不把持平当输或赢。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前动态确认 `_record_closed_position` 的二分 `else` 会把零和浮点噪声计入 loss_num。
  - 运行 `PYTHONPATH=src pytest -q tests/test_rv04_flat_trade_metrics.py tests/test_rv05_process_save_file.py tests/test_nx08_position_close_profit.py tests/test_remediation_report_counts.py`，20 项专项、相邻和报告测试全部通过。
  - 用真实 BackTestTrader 连续记录 +10、-5、0、+0.5e-9、-0.5e-9，确认 win=1、loss=1、flat=3，金额只包含有方向收益。
  - 注入不含 flat_num 的旧结果字典后记录零收益，确认自动补字段且原 win/loss 不变；trade 模式持平平仓仍释放本金。
  - AST/源码检查确认结果表含“持平”、总交易数加入 flat_num，而胜率仍为 win/(win+loss)。
  - 执行 compileall、CRLF 字节计数（bare-LF=0）和 `git diff --check`。
- **e. 验证是否通过？** 通过（20 项专项与相邻测试通过；零值与容差内噪声计入持平，不再污染失败统计）
- **提交：** fix(RV-04): track breakeven trades separately
- **修改文件：** `src/tradingview_zy/backtesting/backtest_trader.py`, `src/tradingview_zy/backtesting/backtest.py`, `tests/test_rv04_flat_trade_metrics.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`, `task_plan.md`
- **验证限制：**
  - 完整 BackTest.result 动态导入受容器缺失 empyrical/pyfolio 阻断；核心分类使用真实 BackTestTrader 动态执行，结果表结构和汇总表达式由 AST 验证。
  - 1e-9 是以账本货币单位计的绝对统计容差；若未来支持超高精度资产，应把货币精度纳入统一领域模型。
- **原报告最新结论：** _record_closed_position() 仍仅以 profit > 0 判胜，其余（包括 0）全部计入 loss。
- **原报告建议：** 定义 breakeven 计数或至少 0 不计 loss；补零收益和手续费后零收益测试。

### 36. RV-01 · 添加“置顶”自选股时批量位移遗漏 market，跨市场同名组会被一起改序

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Database / Watchlist
- **本轮状态：** 已完成
- **问题是否存在：** 是
- **a. 这个问题是什么？** `zx_add_group_stock(..., location="top")` 删除目标市场旧记录后，对同名自选组执行 position+1，但 UPDATE 只过滤 zx_group、遗漏 market。A 股和港股都使用“我的关注”等同名组时，在一个市场置顶会无提示改动另一个市场的排序。
- **b. 我是怎么修复的？** 将删除旧标的、重排目标市场/分组和插入新记录放入 `Session.begin()` 单事务。置顶时先 flush 删除，再只查询相同 market + zx_group 的剩余行并按原 position/id 压实为 1..N，新标的写入 position=0；这样既隔离跨市场同名组，也避免已有标的重新置顶后留下排序空洞。
- **c. 修复后是否验证？** 是
- **d. 怎么验证的？**
  - 修复前源码确认置顶排序只按 zx_group 更新，遗漏 market；删除、位移和插入依赖手工 commit。
  - 运行 `PYTHONPATH=src pytest -q tests/test_rv01_watchlist_market_isolation.py tests/test_nx21_mysql_url.py tests/test_remediation_report_counts.py`，7 项专项、相邻 DB URL 和报告测试全部通过。
  - 在真实 SQLAlchemy + 文件 SQLite 中建立 A/HK 两个同名组；向 A 组置顶后 A 为 0/1/2，HK 逐行不变。
  - 用 SQLite BEFORE INSERT trigger 注入失败，确认删除与重排全部回滚，A/HK 两组和调用前一致。
  - 重新添加已有 A 股标的，确认目标只保留一行、名称更新、位置为 0，其他行连续为 1..N。
  - 执行 compileall、CRLF 字节计数（bare-LF=0）和 `git diff --check`。
- **e. 验证是否通过？** 通过（7 项专项与相邻测试通过；跨市场隔离、失败回滚和连续重排均正确）
- **提交：** fix(RV-01): isolate watchlist top ordering by market
- **修改文件：** `src/tradingview_zy/db.py`, `tests/test_rv01_watchlist_market_isolation.py`, `audit/remediation_state.json`, `remediation_report.md`, `findings.md`, `progress.md`
- **验证限制：**
  - 未连接真实 MySQL；复合过滤、事务回滚和排序行为使用 SQLAlchemy ORM 与 SQLite 实际执行验证。现有生产库若已有重复行，仍需单独数据清理/迁移。
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py、src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 给 UPDATE 加 market 过滤；移动+插入放同一事务；增加 (market,zx_group,stock_code) 唯一约束并规范化 position。

### 37. RV-07 · UDF/search/marks 路由缺少统一参数校验，畸形请求返回 500

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web API Robustness
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 本轮 Web 改动没有为 UDF/search/marks 路由增加统一参数 schema 和 4xx 错误处理。
- **原报告建议：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间；UDF 返回 s:error/errmsg，普通 API 返回400/422。

### 38. ME-11 · Baostock 股票列表固定在 2022-04-18，分钟时间按序号重建

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Baostock
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_baostock.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 股票列表按当前交易日/可用最新日刷新并缓存版本；使用数据源原始时间；重试采用有界迭代与退避。

### 39. HI-17 · 行情同步脚本以顶层程序方式执行，缺少可恢复 checkpoint、统一 deadline 和可审计批次状态

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Scripts
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（script/crontab/reboot_sync_a_klines.py、script/crontab/reboot_sync_us_klines.py、script/crontab/reboot_sync_currency_klines.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 重构为显式 CLI/main；universe 外部化；每个 symbol/frequency 写 checkpoint 和失败原因；所有外部调用有 deadline/取消；以幂等 upsert 和批次状态支持断点续跑。

### 40. ME-12 · TDX 适配器存在递归重连、涨跌幅分母错误和硬编码交易时段

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / TDX Adapters
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx.py、src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 使用有界重试循环；统一 Tick 计算函数；引入交易所日历服务；对 0/缺失前收价明确返回 unavailable。

### 41. ME-23 · 期货手续费/保证金参数硬编码且没有生效日期与数据版本

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Backtesting Config
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/futures_contracts.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 参数外部化为带 effective_from/to、source、version 的数据集；回测产物嵌入 hash/快照；缺少目标日期配置时失败。

### 42. HI-16 · 文件缓存非原子写入、读错即删，且使用可执行反序列化格式

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / File Cache
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** file_db 仍使用非原子写入和可执行反序列化格式，读取异常时删除缓存；相关路径未被后续修复触及。
- **原报告建议：** 临时文件+fsync+原子 replace；优先安全序列化；校验失败隔离坏文件而不是无条件删除。

### 43. ME-17 · ExchangeQMT 使用可变默认参数、忽略 end_date 并缺少空数据校验

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / QMT Market Data
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_qmt.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 默认参数改 None；严格裁剪 start/end；分离下载与读取；schema 校验和明确错误类型。

### 44. ME-26 · 调度器在 Flask app factory 内立即 start，可能在多 worker/reloader 中重复运行

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Scheduler Lifecycle
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 最新 create_app() 仍在函数内创建并 scheduler.start()，进程内 job 状态设计没有变化。
- **原报告建议：** 调度器独立进程或 leader election；Web 仅管理持久化 job store；app factory 不启动后台线程。

### 45. ME-19 · 选股结果替换不是事务，写入中途失败会留下半成品；opt_type 参数未生效

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Selection Tasks
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** xuangu_tasks.py 只改策略加载；清空目标组后逐条写入、opt_type 未消费和任务状态键问题仍在。
- **原报告建议：** 写入 staging 并在单事务成功后替换；真正使用 opt_type 或删除；running_tasks 使用 (market,task_name)。

### 46. ME-18 · 选股/监控缺少失败标的隔离和输入数据协议校验

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Strategy Runners
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 设计文档被删除不等于功能修复；SelectionRunner/MonitoringRunner 的失败隔离与输入 schema 未修改。
- **原报告建议：** BatchRunResult 明确 hits、misses、failures；每个 symbol 独立错误；策略调用前做一次轻量 KlineFrame 校验。

### 47. ME-14 · TDX 美股时区通过 replace(tzinfo=pytz_zone) 附着，可能产生 LMT 偏移

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / TDX US
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx_us.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 使用 zoneinfo 或 pytz.localize，再 astimezone；为源字段建立映射文档和数据质量断言。

### 48. ME-30 · 多个市场 now_trading 使用粗粒度硬编码，未处理节假日、午休、夜盘品种差异和 DST

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Trading Calendar
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py、src/tradingview_zy/exchange/exchange_ctp.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 引入版本化 exchange calendar；按 instrument/session 查询；无法确认时返回 Unknown，而非 True。

### 49. ME-22 · 消息 HTTP、时间和 singleton 工具缺少可靠错误、时区和并发语义

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Utilities
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/utils.py、src/tradingview_zy/fun.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等；所有时间边界要求 aware datetime；单例改为依赖注入或线程安全初始化。

### 50. ME-02 · /tv/history 请求计数器无上限且无线程同步；首次请求返回完整历史是现有测试规定的行为

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web UDF
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** /tv/history 仍维护进程内 __history_req_counter 普通字典；键没有过期回收/容量上限，也没有并发同步。
- **原报告建议：** 使用有界 TTL/LRU 或外部限流器；加入锁/原子操作；按会话/IP/标的设计稳定限流键，并覆盖并发测试。

### 51. NX-10 · 策略 JSON 复用旧 String(200) 列，较长配置在 MySQL 上可能失败或截断

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Database Schema
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 监控保存改用 strategy_id，但配置 JSON 仍写入旧 String(200) 映射列，数据库 schema 未迁移。
- **原报告建议：** 新增 Text/JSON 列和独立 memo，做迁移；请求层限制合理大小并做保存后往返校验。

### 52. RV-06 · 图表布局、模板和绘图存储接口没有请求体/字段大小与配额限制

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Web Storage / Availability
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 安全改动未增加 charts/templates/drawings 的请求体、字段长度或用户配额限制。
- **原报告建议：** 设置全局和字段上限、每主体配额、去重/更新；超限返回 413/422。

### 53. ME-15 · Futu 全局上下文缺少生命周期、并发和失败隔离

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 中 / Futu
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_futu.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** Context manager + connection pool/lock；健康状态和重连状态机；显式 imports；进程退出钩子。

### 54. NX-01 · CTP 空前置地址不会触发默认地址兜底；当前属于修复抽象类后的后续阻断

- **原始状态 / 严重度 / 领域：** 🛡️ 未完全修复（已阻断或缓解） / 中 / CTP
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** CTP 的空字符串前置地址兜底逻辑没有修改，底层问题仍在。最新工厂会在导入 CTP 前直接拒绝 EXCHANGE_FUTURES="ctp"，标准路径不会触发该后续错误；这是风险封堵，不是功能修复。
- **原报告建议：** 修复 CR-05 时仍必须把地址读取改为 getattr(..., "") or DEFAULT 或明确要求必填，并做地址 schema 校验。

### 55. NX-25 · 孤立 ExchangeZB 显式关闭 TLS 证书校验

- **原始状态 / 严重度 / 领域：** 🛡️ 未完全修复（已阻断或缓解） / 中 / Legacy Exchange Security
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 标准工厂不注册 ZB，降低默认可达性；但 ExchangeZB 仍在运行源码树并显式 params["verify"]=False，可被直接导入使用。
- **原报告建议：** 删除/归档该适配器，或恢复 TLS 验证、证书配置与测试；保持标准入口不支持。

### 56. ME-29 · 当前提交无可见 CI 状态，测试集中在少数协议单元，核心风险无门禁

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Quality Gates
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 仓库已有持久化 GitHub Actions：Python 3.11 使用 uv sync --locked 运行完整 pytest 且 warnings-as-errors，Python 3.13 单独验证依赖 warning 基线。PR #15 最终合并检查为 172 passed。浏览器、MySQL 和真实外部 SDK 仍不在门禁内。
- **原报告建议：** 增加 MySQL、浏览器/DOM、核心 provider mock/沙箱矩阵；在仓库分支保护中把 checks 设为 required，并验证合并提交 push 检查。

### 57. ME-10 · 统一 Exchange 接口没有能力声明和统一错误模型

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Adapter Architecture
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 新增 Capability、统一领域错误、MarketRegistry 和 require_capability；未知市场/provider fail-closed，构造失败前不缓存。但旧 Exchange 大接口及部分 provider 的声明/实现一致性尚未完全解决。
- **原报告建议：** 拆分细粒度 Protocol；对每个 provider 做“声明能力必须有真实实现”的契约测试；修正 DB provider 的 security_master/plates 声明。

### 58. ME-20 · 策略输出只有形状约定，没有边界校验和领域类型

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Strategy Protocol
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 策略加载器现在会验证目标是类、具有 run()、构造参数签名和参数类型，这修复了“构造前无边界”的一部分。可是 StrategySignal 返回值的 action、score、时间、code/frequency 和有限数值仍未在 runner 边界统一校验。
- **原报告建议：** 为策略输出建立版本化 schema/validated dataclass，并在 SelectionRunner/MonitoringRunner 接受结果时逐项验证。

### 59. ME-25 · 依赖范围宽、旧 setup.py 与 pyproject 不一致，缺少可验证供应链清单

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Supply Chain
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 旧 setup.py 和 MANIFEST.in 已删除，Apache-2.0 与 setup.py 中 MIT 的许可证冲突、重复打包入口以及 PyArmor 依赖均已消除。仍存在大量仅设下界的依赖、本地 wheel 缺少显式哈希/来源说明、SBOM/漏洞审计门禁缺失等问题。
- **原报告建议：** 以 uv.lock 为唯一受支持安装路径并在 CI 校验；记录本地 wheel SHA-256/来源并生成 SBOM、许可证和漏洞报告。

### 60. ME-27 · 交易/API 密钥设计为明文 Python 配置，缺少分级与轮换机制

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Secrets
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** Web 登录密码和 Flask 会话密钥现在支持环境变量/随机持久化，且默认远程免密访问被阻止，降低了配置泄露后的直接利用面。但是数据库、交易所、券商、AI 和飞书等业务密钥仍集中在明文 Python 配置/通用缓存中，设置页仍回显飞书 Secret。
- **原报告建议：** 将业务密钥迁移到环境变量、系统 keyring 或 Vault；设置 API 只接受新值而不返回旧值，统一日志脱敏与轮换。

### 61. ME-04 · K 线 payload 对时区、schema、排序和重复值缺少边界校验

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Web Payload
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** K 线进入 TradingView 前已有 required columns、有限数、OHLC、volume、code/frequency、严格排序、重复时间和市场时区校验；但 /tv/history 在时区本地化之前先执行时间范围过滤，naive 市场本地时间会按服务器时区解释。
- **原报告建议：** 先补全 code/市场时区并规范化，再按 Unix 秒过滤；增加服务器 UTC、A 股 naive 时间的路由级测试。

### 62. ME-01 · TradingView 存储接口信任请求中的 client/user 作为授权边界

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 中 / Web Storage
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 登录、会话和远程免密边界已加强，匿名攻击面下降；但 TradingView chart/template/drawing 存储仍信任请求中的 client/user 作为数据分区，没有绑定已认证主体。
- **原报告建议：** 服务端从会话派生主体；忽略或校验客户端 user/client；为跨用户读写增加授权测试和迁移方案。

### 63. ME-03 · /tv/config 的周期并集遗漏 ny_futures；当前默认适配器无独有周期，属于潜在能力漂移

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Web UDF
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** market_frequencys 已包含 ny_futures，但 /tv/config 构造全局 supported_resolutions 时仍没有把该市场加入并集。
- **原报告建议：** 由 MarketRegistry 生成 UDF 配置，或至少把 ny_futures 纳入并集并增加“任一市场独有周期”回归测试。

### 64. MX-11 · 配置模板暴露具体 IB 账户标识

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Configuration
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 最新 config.py.demo 仍包含具体 IB_ACCOUNT = 'DU6941075'。
- **原报告建议：** 改为明显占位符/空值，并在启动时拒绝示例值。

### 65. MX-07 · alert.js 七个列定义把 field 拼成 filed，字段元数据和排序绑定失效

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Frontend
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** alert.js 仅修改策略列标题等少量文本，七处 filed: 拼写仍存在。
- **原报告建议：** 统一改为 field，并增加前端 lint/schema 测试；对可排序列在浏览器中验证排序请求/本地排序键。

### 66. MX-10 · 图表显示函数参数契约漂移

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Frontend
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（web/tradingview_zy_chart/cl_app/static/js/charts.js、web/tradingview_zy_chart/cl_app/templates/index.html）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 删除无效参数或让函数显式应用高度；用 TypeScript/JSDoc 固化签名。

### 67. NX-09 · 未实现的 fee_us() 作为公开函数残留，但仓库内未发现调用方

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Backtesting Fees
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/base.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 无兼容需求则删除；否则抛 NotImplementedError 或实现数据驱动费率。

### 68. NX-18 · zixuan.js 的 templet 未声明，泄漏为全局变量

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Frontend
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（web/tradingview_zy_chart/cl_app/static/js/zixuan.js）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 块级 `const templet` 或表达式返回。

### 69. NX-17 · TradingView UDF 把所有市场 session 声明为 24x7，并把 FX 类型标成 stock

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Web UDF
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 最新 Web 文件仍把所有市场 session 写为 24x7，FX 类型仍为 stock。
- **原报告建议：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type；FX 使用符合 UDF 的 forex 类型。

### 70. LO-02 · TDX/US/同步适配器存在大段复制（Duplicated Code）

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Maintainability
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** TDX、US 历史适配器和同步脚本仍包含重复的分页、日期解析、缓存与重试代码；PR #15 只新增注册表/领域边界，没有提取这些重复实现。
- **原报告建议：** 提取共享分页器、日期解析、Kline normalizer、缓存与 deadline 策略，用 provider contract tests 固定差异点。

### 71. LO-06 · 大量短变量、宽泛异常和 wildcard import 降低可审计性（Mysterious Name）

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Readability
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_alpaca.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **原报告建议：** 显式 import；领域命名；窄异常；结构化日志包含 market/code/request_id；启用 lint 规则 F403/F405/BLE001。

### 72. MX-16 · 存在未加载的 ai.js 和完全 no-op 的 OtherTasks

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Dead Code
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** ai.js 仍是未加载/不可用桩，OtherTasks.run_task() 仍为 pass；能力边界没有删除或实现。
- **原报告建议：** 删除无效资产和任务壳，或实现后显式注册、展示与测试。

### 73. MX-18 · StrategySignal 与 Operation 是两套独立协议，跨选股/监控/回测复用需要手工转换（架构债务）

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Strategy Architecture
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 删除架构文档没有合并协议；StrategySignal 与 Operation 两套模型仍独立存在。
- **原报告建议：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议；没有该需求时，应在文档中明确边界而不是强行统一。

### 74. NX-11 · 通用监控事件继续复用旧短字符串列，当前值可容纳但扩展空间受限

- **原始状态 / 严重度 / 领域：** ❌ 未修复 / 低 / Database Schema
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 策略加载改为注册表不改变监控事件数据库列长度；event_type/action/score 仍复用旧短字符串列。
- **原报告建议：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。

### 75. LO-05 · 新增市场需要跨枚举、配置、工厂、DB、UDF、模板和脚本散改（Shotgun Surgery）

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Architecture
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** MarketRegistry 已集中配置属性、时区、TradingView 类型/session、默认代码、provider、能力和 DB 分区；Exchange 工厂与 DB 路由已接入。Web UDF、模板和若干脚本仍有独立市场映射。
- **原报告建议：** 让 UDF/config、页面和脚本消费注册表，并删除重复映射；新增市场用单一注册+穷尽测试验收。

### 76. LO-07 · 保留多处 pass/旧桩/历史任务壳，能力边界不清（Speculative Generality）

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Dead Code
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 清理提交删除了 cl_myquant/cl_vnpy/cl_wtpy 和旧 trader 墓碑脚本，减少了一批历史桩。但 tradingview_zy.monitor、other_tasks.py、部分 Exchange 不支持方法和其他 pass/RuntimeError 桩仍在，能力边界仍不清楚。
- **原报告建议：** 从能力注册表移除未实现能力；真正需要兼容的入口使用单一、可测试的 Unsupported 错误，不再散布空桩。

### 77. LO-08 · 文档、测试现状和遗留授权描述存在漂移

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Documentation
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** CLAUDE.md、旧架构/迁移文档、PyArmor 授权说明、setup.py 许可证冲突和三个旧适配目录已清理，文档漂移明显减少。但 check_env.py 的 Python 版本/环境结论仍与 pyproject 不一致，joinquant/ 仍是活跃根目录遗留，README 对部分能力的支持边界仍需校准。
- **原报告建议：** 修复 check_env 契约；处理 joinquant；建立由能力注册表和 CI 自动生成/校验的支持矩阵。

### 78. LO-03 · 市场、周期、订单状态和方向广泛使用裸字符串（Primitive Obsession）

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Domain Model
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 新增 Market、OrderSide、PositionSide、OrderStatus、Capability 等枚举/领域对象，市场解析和部分订单边界不再依赖裸字符串；大量旧模块仍使用 market/frequency/order 字符串。
- **原报告建议：** 逐步迁移旧适配器、Web 路由和数据库字段；在序列化边界统一转换。

### 79. LO-04 · OHLCV、订单和策略参数以重复 dict 传递（Data Clumps）

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Domain Model
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 新增不可变 OrderRequest、Fill、OrderState 和严格 KlineFrame 边界，部分核心 dict 已被领域对象替代；旧适配器和策略参数仍广泛传 dict。
- **原报告建议：** 按模块边界渐进迁移，不要求内部 DataFrame 全部对象化；优先交易/成交和外部 provider payload。

### 80. LO-01 · Flask app factory 承担过多职责（Divergent Change）

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Maintainability
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** cl_app/__init__.py 继续集中认证、调度、UDF、存储、自选、监控和选股；文件职责没有拆分。
- **原报告建议：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分；依赖通过 app extensions 注入。

### 81. MX-12 · Web app factory 保留旧模块专用降级分支，当前成为无覆盖的迁移残留

- **原始状态 / 严重度 / 领域：** 🟡 部分修复 / 低 / Architecture / Spec
- **本轮状态：** 待处理
- **问题是否存在：** 待验证
- **a. 这个问题是什么？** 待验证
- **b. 我是怎么修复的？** 待处理
- **c. 修复后是否验证？** 待验证
- **d. 怎么验证的？**
  - 待处理
- **e. 验证是否通过？** 待处理
- **提交：** 待提交
- **修改文件：** 待处理
- **原报告最新结论：** 最新 create_app() 仍完整保留 _REMOVED_LEGACY_*、_UnavailableTasks 和 _LazyTasks。
- **原报告建议：** 清理旧模块专用判断；保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。
