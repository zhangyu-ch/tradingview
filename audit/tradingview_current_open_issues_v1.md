# tradingview 当前未完全关闭问题清单 V1

- **来源报告：** `tradingview_all_issues_latest_master_revalidated_v7.md`。
- **代码固定点：** [`3488462529c6ec052192eb41d1a6b74c5718c58f`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)（当前 `master`，PR #15 合并提交）。
- **整理范围：** 仅收录 V7 中尚未完全关闭的条目：部分修复、已阻断/缓解、未修复、真实回归和 V7 新增问题。
- **排除范围：** 33 条“已修复”和 1 条“通过移除不支持/失效能力修复”不在本清单重复展开。
- **当前问题总数：** **81 条**。
- **版本说明：** 本文件是从完整 V7 报告派生出的独立待处理问题清单，重新从 **V1** 起版；原问题编号保持不变，便于与历史报告、测试和 PR 对照。

> 本清单没有重新判定代码状态，也没有删除历史证据。每条详细内容直接继承 V7 当前结论、判定依据、剩余工作、证据与原始记录。

## 执行摘要

|当前状态|数量|含义|
|---|---:|---|
|🔴 回归（重新出现）|1|后续修改使原来一致或已关闭的契约重新失效。|
|🆕 新问题（未修复）|5|V7 审查中新发现，当前尚未修复。|
|❌ 未修复|54|当前固定点仍能确认问题存在，缺少直接关闭证据。|
|🛡️ 未完全修复（已阻断或缓解）|5|危险入口已被阻断或风险已降低，但底层实现仍未修好。|
|🟡 部分修复|16|已有实质修复，但原问题仍有根因、边界或动态验证未完成。|
|**合计**|**81**|全部为尚未完全关闭的待处理项。|

### 严重程度分布

|严重程度|数量|
|---|---:|
|严重|1|
|高|12|
|中|49|
|低|19|

### 变化类型分布

|变化类型|数量|说明|
|---|---:|---|
|真实回归|1|确认属于真实回归。|
|V7 新问题|5|V7 新发现问题。|
|V6 误标纠正|53|纠正 V6 顶层误标；不等同于后来发生代码回归。|
|代码进展/补齐|6|已有代码进展，但尚未达到完全关闭条件。|
|状态保持|16|V7 复核后状态保持不变。|

### 建议处理顺序（V1 整理建议）

该顺序是为了便于排期，不改变 V7 的事实判定：先处理真实回归和新增高风险问题；再处理“严重/高”级未修复项；随后处理已阻断但底层仍坏的能力；最后收敛中低严重度的架构与治理债务。同一严重度内，优先顺序建议为“回归 → 新问题 → 未修复 → 已阻断/缓解 → 部分修复”。

## 问题索引

|序号|编号|状态|严重度|领域|问题|
|---:|---|---|---|---|---|
|1|[`CR-02`](#CR-02)|🟡 部分修复|严重|Web Security|默认部署无有效认证，且会话签名密钥固定|
|2|[`NEW-02`](#NEW-02)|🆕 新问题（未修复）|高|CI / Supply Chain|临时修复传输分片与可写 force-push 工作流被合并进 master|
|3|[`NEW-03`](#NEW-03)|🆕 新问题（未修复）|高|Dependencies / Packaging|requirements.txt 与 pyproject/uv.lock 漂移，可重新解析出已知不兼容依赖|
|4|[`NEW-04`](#NEW-04)|🆕 新问题（未修复）|高|Web / Market Data|/tv/history 在市场时区本地化前过滤时间窗口，naive K 线会按服务器时区错筛|
|5|[`NEW-05`](#NEW-05)|🆕 新问题（未修复）|高|Backtesting / Accounting|FIFO lot 在结算校验完成前原地消费，异常会留下“lot 已减、聚合仓位未减”的半提交状态|
|6|[`NX-20`](#NX-20)|❌ 未修复|高|TDX Reliability|多个 TDX-ExHq 构造器用无上限 while True 重连|
|7|[`RV-08`](#RV-08)|❌ 未修复|高|Web Security / Secrets|系统设置页把已保存的飞书 App Secret 明文回显，并在控制台打印提交字段|
|8|[`HI-13`](#HI-13)|❌ 未修复|高|Binance|Binance 合约/现货增量分页可能重复边界或停滞，单行缓存会越界|
|9|[`HI-14`](#HI-14)|❌ 未修复|高|TQ SDK|ExchangeTq 构造即启动非 daemon 线程，队列/缓存无同步与确定性关闭|
|10|[`CR-05`](#CR-05)|🛡️ 未完全修复（已阻断或缓解）|高|CTP|CTP 行情与交易代码存在多处确定性失效，但当前未接入标准工厂或内置启动脚本|
|11|[`CR-04`](#CR-04)|🛡️ 未完全修复（已阻断或缓解）|高|QMT Trader|QMT 交易适配器真实买入确定性引用未定义 price；当前无内置活跃启动入口|
|12|[`HI-06`](#HI-06)|🛡️ 未完全修复（已阻断或缓解）|高|Web Security|状态变更接口无 CSRF 防护，删除任务还使用 GET|
|13|[`CR-03`](#CR-03)|🟡 部分修复|高|Live Trading|实盘订单缺少成交状态机，内部账本可与券商/交易所永久分叉|
|14|[`ME-24`](#ME-24)|🔴 回归（重新出现）|中|Environment|环境检查与 pyproject 的 Python 约束冲突，并在失败后仍打印“环境OK”|
|15|[`NEW-06`](#NEW-06)|🆕 新问题（未修复）|中|Architecture / Exchange Contract|MarketRegistry 过报 DB provider 的 security_master/plates 能力|
|16|[`HI-01`](#HI-01)|❌ 未修复|中|Futures Trader|TraderFutures 使用不存在的构造参数，实例化立即失败|
|17|[`ME-06`](#ME-06)|❌ 未修复|中|File Upload|自选导入和导出共用固定 zx.txt，缺少并发隔离与上传限制|
|18|[`ME-16`](#ME-16)|❌ 未修复|中|Interactive Brokers|IB Redis 请求使用 BRPOP timeout=0，可无限阻塞调用线程|
|19|[`ME-05`](#ME-05)|❌ 未修复|中|Web Startup|create_app 启动时 eager 实例化全部配置市场，单个可选适配器可拖垮整个服务|
|20|[`MX-01`](#MX-01)|❌ 未修复|中|Configuration / Messaging|钉钉配置契约破裂且 HK 分支永不可达|
|21|[`MX-06`](#MX-06)|❌ 未修复|中|Database / Operations|直接执行 db.py 会向配置数据库写测试标记|
|22|[`MX-02`](#MX-02)|❌ 未修复|中|Exchange Factory|ZB 被配置文档声明支持，但工厂无法选择|
|23|[`MX-04`](#MX-04)|❌ 未修复|中|ExchangeDB / Scheduling|ExchangeDB.now_trading 返回 None，Python 与前端调用方对三态结果解释不一致|
|24|[`MX-05`](#MX-05)|❌ 未修复|中|Frontend|自选涨跌幅轮询把函数返回值交给 setInterval|
|25|[`MX-17`](#MX-17)|❌ 未修复|中|TDX / Performance|TDX 节点选优在缓存缺失或重置时串行探测全部候选，缺少总体 deadline|
|26|[`NX-08`](#NX-08)|❌ 未修复|中|Backtesting Model|POSITION.get_close_profit 会修改调用方传入列表|
|27|[`NX-03`](#NX-03)|❌ 未修复|中|Configuration / Messaging|飞书配置读取会原地修改全局默认字典|
|28|[`NX-22`](#NX-22)|❌ 未修复|中|Database / Diagnostics|db.py import 时全局关闭所有 warnings|
|29|[`NX-21`](#NX-21)|❌ 未修复|中|Database Configuration|MySQL DSN 直接字符串插值，特殊字符密码会破坏 URL|
|30|[`NX-23`](#NX-23)|❌ 未修复|中|ExchangeDB|ExchangeDB.all_stocks() 永远为空，与“db 可作为 Web 数据源”冲突|
|31|[`NX-16`](#NX-16)|❌ 未修复|中|Web Security / Availability|/ticks 可提交无上限代码数组并同步扇出到数据源|
|32|[`NX-14`](#NX-14)|❌ 未修复|中|Web Storage|读取不存在的 chart/template 会直接解引用 None|
|33|[`NX-15`](#NX-15)|❌ 未修复|中|Web Storage|绘图保存异常被吞掉并始终返回 status ok|
|34|[`RV-05`](#RV-05)|❌ 未修复|中|Backtesting / Process|多进程回测允许省略 save_file，但 run_by_code 无条件对 None 调 split()|
|35|[`RV-04`](#RV-04)|❌ 未修复|中|Backtesting Metrics|盈亏为 0 的平仓被计入失败交易|
|36|[`RV-01`](#RV-01)|❌ 未修复|中|Database / Watchlist|添加“置顶”自选股时批量位移遗漏 market，跨市场同名组会被一起改序|
|37|[`RV-07`](#RV-07)|❌ 未修复|中|Web API Robustness|UDF/search/marks 路由缺少统一参数校验，畸形请求返回 500|
|38|[`ME-11`](#ME-11)|❌ 未修复|中|Baostock|Baostock 股票列表固定在 2022-04-18，分钟时间按序号重建|
|39|[`HI-17`](#HI-17)|❌ 未修复|中|Scripts|行情同步脚本以顶层程序方式执行，缺少可恢复 checkpoint、统一 deadline 和可审计批次状态|
|40|[`ME-12`](#ME-12)|❌ 未修复|中|TDX Adapters|TDX 适配器存在递归重连、涨跌幅分母错误和硬编码交易时段|
|41|[`ME-23`](#ME-23)|❌ 未修复|中|Backtesting Config|期货手续费/保证金参数硬编码且没有生效日期与数据版本|
|42|[`HI-16`](#HI-16)|❌ 未修复|中|File Cache|文件缓存非原子写入、读错即删，且使用可执行反序列化格式|
|43|[`ME-17`](#ME-17)|❌ 未修复|中|QMT Market Data|ExchangeQMT 使用可变默认参数、忽略 end_date 并缺少空数据校验|
|44|[`ME-26`](#ME-26)|❌ 未修复|中|Scheduler Lifecycle|调度器在 Flask app factory 内立即 start，可能在多 worker/reloader 中重复运行|
|45|[`ME-19`](#ME-19)|❌ 未修复|中|Selection Tasks|选股结果替换不是事务，写入中途失败会留下半成品；opt_type 参数未生效|
|46|[`ME-18`](#ME-18)|❌ 未修复|中|Strategy Runners|选股/监控缺少失败标的隔离和输入数据协议校验|
|47|[`ME-14`](#ME-14)|❌ 未修复|中|TDX US|TDX 美股时区通过 replace(tzinfo=pytz_zone) 附着，可能产生 LMT 偏移|
|48|[`ME-30`](#ME-30)|❌ 未修复|中|Trading Calendar|多个市场 now_trading 使用粗粒度硬编码，未处理节假日、午休、夜盘品种差异和 DST|
|49|[`ME-22`](#ME-22)|❌ 未修复|中|Utilities|消息 HTTP、时间和 singleton 工具缺少可靠错误、时区和并发语义|
|50|[`ME-02`](#ME-02)|❌ 未修复|中|Web UDF|/tv/history 请求计数器无上限且无线程同步；首次请求返回完整历史是现有测试规定的行为|
|51|[`NX-10`](#NX-10)|❌ 未修复|中|Database Schema|策略 JSON 复用旧 String(200) 列，较长配置在 MySQL 上可能失败或截断|
|52|[`RV-06`](#RV-06)|❌ 未修复|中|Web Storage / Availability|图表布局、模板和绘图存储接口没有请求体/字段大小与配额限制|
|53|[`ME-15`](#ME-15)|❌ 未修复|中|Futu|Futu 全局上下文缺少生命周期、并发和失败隔离|
|54|[`NX-01`](#NX-01)|🛡️ 未完全修复（已阻断或缓解）|中|CTP|CTP 空前置地址不会触发默认地址兜底；当前属于修复抽象类后的后续阻断|
|55|[`NX-25`](#NX-25)|🛡️ 未完全修复（已阻断或缓解）|中|Legacy Exchange Security|孤立 ExchangeZB 显式关闭 TLS 证书校验|
|56|[`ME-29`](#ME-29)|🟡 部分修复|中|Quality Gates|当前提交无可见 CI 状态，测试集中在少数协议单元，核心风险无门禁|
|57|[`ME-10`](#ME-10)|🟡 部分修复|中|Adapter Architecture|统一 Exchange 接口没有能力声明和统一错误模型|
|58|[`ME-20`](#ME-20)|🟡 部分修复|中|Strategy Protocol|策略输出只有形状约定，没有边界校验和领域类型|
|59|[`ME-25`](#ME-25)|🟡 部分修复|中|Supply Chain|依赖范围宽、旧 setup.py 与 pyproject 不一致，缺少可验证供应链清单|
|60|[`ME-27`](#ME-27)|🟡 部分修复|中|Secrets|交易/API 密钥设计为明文 Python 配置，缺少分级与轮换机制|
|61|[`ME-04`](#ME-04)|🟡 部分修复|中|Web Payload|K 线 payload 对时区、schema、排序和重复值缺少边界校验|
|62|[`ME-01`](#ME-01)|🟡 部分修复|中|Web Storage|TradingView 存储接口信任请求中的 client/user 作为授权边界|
|63|[`ME-03`](#ME-03)|❌ 未修复|低|Web UDF|/tv/config 的周期并集遗漏 ny_futures；当前默认适配器无独有周期，属于潜在能力漂移|
|64|[`MX-11`](#MX-11)|❌ 未修复|低|Configuration|配置模板暴露具体 IB 账户标识|
|65|[`MX-07`](#MX-07)|❌ 未修复|低|Frontend|alert.js 七个列定义把 field 拼成 filed，字段元数据和排序绑定失效|
|66|[`MX-10`](#MX-10)|❌ 未修复|低|Frontend|图表显示函数参数契约漂移|
|67|[`NX-09`](#NX-09)|❌ 未修复|低|Backtesting Fees|未实现的 fee_us() 作为公开函数残留，但仓库内未发现调用方|
|68|[`NX-18`](#NX-18)|❌ 未修复|低|Frontend|zixuan.js 的 templet 未声明，泄漏为全局变量|
|69|[`NX-17`](#NX-17)|❌ 未修复|低|Web UDF|TradingView UDF 把所有市场 session 声明为 24x7，并把 FX 类型标成 stock|
|70|[`LO-02`](#LO-02)|❌ 未修复|低|Maintainability|TDX/US/同步适配器存在大段复制（Duplicated Code）|
|71|[`LO-06`](#LO-06)|❌ 未修复|低|Readability|大量短变量、宽泛异常和 wildcard import 降低可审计性（Mysterious Name）|
|72|[`MX-16`](#MX-16)|❌ 未修复|低|Dead Code|存在未加载的 ai.js 和完全 no-op 的 OtherTasks|
|73|[`MX-18`](#MX-18)|❌ 未修复|低|Strategy Architecture|StrategySignal 与 Operation 是两套独立协议，跨选股/监控/回测复用需要手工转换（架构债务）|
|74|[`NX-11`](#NX-11)|❌ 未修复|低|Database Schema|通用监控事件继续复用旧短字符串列，当前值可容纳但扩展空间受限|
|75|[`LO-05`](#LO-05)|🟡 部分修复|低|Architecture|新增市场需要跨枚举、配置、工厂、DB、UDF、模板和脚本散改（Shotgun Surgery）|
|76|[`LO-07`](#LO-07)|🟡 部分修复|低|Dead Code|保留多处 pass/旧桩/历史任务壳，能力边界不清（Speculative Generality）|
|77|[`LO-08`](#LO-08)|🟡 部分修复|低|Documentation|文档、测试现状和遗留授权描述存在漂移|
|78|[`LO-03`](#LO-03)|🟡 部分修复|低|Domain Model|市场、周期、订单状态和方向广泛使用裸字符串（Primitive Obsession）|
|79|[`LO-04`](#LO-04)|🟡 部分修复|低|Domain Model|OHLCV、订单和策略参数以重复 dict 传递（Data Clumps）|
|80|[`LO-01`](#LO-01)|🟡 部分修复|低|Maintainability|Flask app factory 承担过多职责（Divergent Change）|
|81|[`MX-12`](#MX-12)|🟡 部分修复|低|Architecture / Spec|Web app factory 保留旧模块专用降级分支，当前成为无覆盖的迁移残留|

## 详细问题

## 严重程度：严重（1 条）

<a id="CR-02"></a>

### CR-02 · 默认部署无有效认证，且会话签名密钥固定

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 默认回环监听、远程免密启动拒绝、随机持久化会话密钥、密码哈希、登录限速、安全 Cookie 和登出仍在；但设置页继续把已保存的飞书 App Secret 放入普通文本框 value，并打印整个提交字段。
- **判定依据：** 认证与会话根因已有实质修复，但原问题还包含 Secret 回显/控制台泄露，当前源码仍可直接定位，因此不能关闭。
- **仍有什么问题 / 下一步：** 设置页不得返回旧 Secret；删除 console.log(data.field)；敏感设置更新应使用“留空不改”语义，并考虑重认证/更严格权限。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/web_security.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_security.py) — 认证、会话密钥和登录限速
- [`tests/test_web_security.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_web_security.py) — 远程免密拒绝、Cookie、密钥和限速测试
- [`web/tradingview_zy_chart/cl_app/templates/setting.html`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/templates/setting.html) — 仍存在 Secret 明文 value 与控制台打印

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### CR-02 · 默认部署无有效认证，且会话签名密钥固定

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [Web 安全模块](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/web_security.py) — 登录、会话密钥和限速
- [安全设置页](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/web/tradingview_zy_chart/cl_app/templates/setting.html) — 不再回显/打印 Secret
- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 严重
- **可信度：** 确定
- **领域：** Web Security
- **来源：** 此前审查
- **工作量：** M
- **标签：** 安全、规范、CWE-306 / CWE-798

#### 当前状态与最新验证

**最新 master 验证结论：** 默认监听已改为 127.0.0.1；非回环监听且无密码时拒绝启动；固定 Flask secret 已替换为自动生成并持久化的随机密钥；增加密码哈希、登录限速、登出和安全 Cookie。可是原条目还包含“系统设置页明文回显并在控制台打印飞书 App Secret”，该代码在最新 master 仍存在，所以不能标记为完全已修复。

**剩余工作：** 仍需修复设置页的 Secret 回显和 console.log，并为敏感设置变更增加重认证或更严格授权。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 示例配置默认 WEB_HOST=0.0.0.0、LOGIN_PWD 为空；登录路由自动登录 365 天；Flask secret_key 固定。系统设置 GET 还把数据库中的飞书 App Secret 以明文 text input 回显，提交脚本把整个表单（含 secret）打印到控制台。

**正确行为应该是什么：** 默认回环监听；空密码/默认 secret/非 loopback 组合启动失败；随机密钥、密码哈希、限速、登出、安全 Cookie；设置页不返回旧 secret，敏感变更重认证。

**直观例子：** 旧部署相当于管理后台默认把门开在所有网卡上、没有门锁，而且所有安装共用同一把 Cookie 签名钥匙。现在远程入口和会话密钥已加强，但飞书 Secret 仍会在设置页明文显示。

#### 2. 影响分析

按文档部署会把管理面和秘密读取/修改接口暴露到所有网卡。匿名访问者可自动登录并读取飞书 Secret、修改配置；固定密钥和长期 Cookie 放大 CSRF/XSS/RCE。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 默认不安全组合启动失败；响应/DOM/控制台/日志无旧 secret；未授权主体不可读写；测试 Cookie、登出和轮换。 修改前测试应失败。
2. **实施修复：** 默认回环监听
3. **实施修复：** 空密码/默认 secret/非 loopback 组合启动失败
4. **实施修复：** 随机密钥、密码哈希、限速、登出、安全 Cookie
5. **实施修复：** 设置页不返回旧 secret，敏感变更重认证。
6. **执行回归验证：** 默认不安全组合启动失败；响应/DOM/控制台/日志无旧 secret；未授权主体不可读写；测试 Cookie、登出和轮换。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 仍需修复设置页的 Secret 回显和 console.log，并为敏感设置变更增加重认证或更严格授权。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 默认监听已改为 127.0.0.1；非回环监听且无密码时拒绝启动；固定 Flask secret 已替换为自动生成并持久化的随机密钥；增加密码哈希、登录限速、登出和安全 Cookie。可是原条目还包含“系统设置页明文回显并在控制台打印飞书 App Secret”，该代码在最新 master 仍存在，所以不能标记为完全已修复。

**原报告采用的排查方法：** 沿默认配置、登录/会话、路由方法、Cookie 和前端 DOM 数据流逐层检查；对可控文本确认最终进入 text API 还是 HTML 解释器，并核对 CSRF/来源校验。

**可自行执行的复核命令：** `pytest -q tests/test_web_security.py && rg -n "fs_app_secret|console\.log\(data\.field\)" web/tradingview_zy_chart/cl_app/templates/setting.html`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`当前安全配置默认值`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo#L9-L27) — 回环监听、哈希、随机 secret 配置
- [`Web 安全辅助模块`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/web_security.py) — 远程免密拒绝、secret 生成、限速
- [`Web 安全测试`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_web_security.py#L24-L200) — 启动拒绝、密钥、Cookie、限速
- [`仍未修复的 Secret 回显`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L29-L34) — 明文 value
- [`仍未修复的控制台打印`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L125-L132) — console.log(data.field)
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo)
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：高 · 可信度：确定

</details>

## 严重程度：高 · 可信度：确定

</details>

## 严重程度：高 · 可信度：确定

## 严重程度：高（12 条）

<a id="NEW-02"></a>

### NEW-02 · 临时修复传输分片与可写 force-push 工作流被合并进 master

- **V7 状态：** 🆕 新问题（未修复）
- **严重程度 / 可信度：** 高 / 确定
- **领域：** CI / Supply Chain
- **来源：** V7 新发现（上一轮修复交付机制遗留）
- **最新结论：** master 仍包含 .github/remediation/current-remediation.part.*、临时 PR body 文件和 3 个 contents:write 工作流；这些工作流能重组补丁、git reset --soft，并向 agent/current-comprehensive-remediation 执行 force-with-lease。临时元数据文件自身写明“must not be merged”。
- **影响与判定依据：** 这些文件不属于产品或长期 CI，却已进入默认分支；未来同名分支 push 或误触发可能用写令牌重放旧补丁/重写分支历史，扩大供应链与维护面。
- **修复建议 / 关闭条件：** 删除 3 个临时工作流、全部 remediation 分片/marker/test 文件和临时 PR 元数据；增加仓库卫生检查，禁止此类 transport artifacts 合并。
- **最小复现：** 静态扫描命中 contents: write、git reset --soft 和 git push --force-with-lease。

#### 当前证据

- [`.github/PR_BODY_CURRENT_REMEDIATION.md`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/.github/PR_BODY_CURRENT_REMEDIATION.md) — 明确标注临时且不应合并
- [`.github/workflows/apply-current-comprehensive-remediation.yml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/.github/workflows/apply-current-comprehensive-remediation.yml) — 写权限、补丁重组和 force-with-lease
- [`.github/workflows/finalize-current-comprehensive-remediation.yml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/.github/workflows/finalize-current-comprehensive-remediation.yml) — soft reset 与强制推送
- [`.github/remediation`](https://github.com/zhangyu-ch/tradingview/tree/3488462529c6ec052192eb41d1a6b74c5718c58f/.github/remediation) — 补丁分片及 marker/test 遗留

<a id="NEW-03"></a>

### NEW-03 · requirements.txt 与 pyproject/uv.lock 漂移，可重新解析出已知不兼容依赖

- **V7 状态：** 🆕 新问题（未修复）
- **严重程度 / 可信度：** 高 / 确定
- **领域：** Dependencies / Packaging
- **来源：** 修改引入（依赖治理只更新了 pyproject/uv.lock）
- **最新结论：** pyproject 已删除 chardet 并固定 websockets>=13.1,<14；requirements.txt 仍直接列出无上界 chardet 和 lark-oapi，且没有 websockets 兼容约束。使用 requirements 安装可再次解析到 chardet 7.x / websockets 16.x，重现本次 CI 中已出现过的 Requests/Lark 导入告警或失败。
- **影响与判定依据：** 仓库存在两个互相矛盾的安装入口，而 CI 只验证 uv.lock；“一种安装方式通过”不能证明另一种仍被文档/用户使用的方式安全。
- **修复建议 / 关闭条件：** 将 pyproject+uv.lock 设为唯一依赖源；若必须发布 requirements，则从 lock 自动生成并在 CI 校验无漂移。
- **最小复现：** 文本对比即可确定约束不一致；此前 CI 日志已分别出现 chardet 7.x 和 websockets 16.x 导入问题。

#### 当前证据

- [`requirements.txt`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/requirements.txt) — 仍含无上界 chardet/lark-oapi，缺少 websockets pin
- [`pyproject.toml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/pyproject.toml) — 已删除 chardet并固定 websockets 13.x
- [`uv.lock`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/uv.lock) — CI 实际验证的锁定环境

<a id="NEW-04"></a>

### NEW-04 · /tv/history 在市场时区本地化前过滤时间窗口，naive K 线会按服务器时区错筛

- **V7 状态：** 🆕 新问题（未修复）
- **严重程度 / 可信度：** 高 / 确定
- **领域：** Web / Market Data
- **来源：** 修复后新暴露的独立边界（与 ME-04 交叉）
- **最新结论：** 路由先调用 filter_klines_by_timestamp_range，再由 klines_to_tv_history/_prepare_strict_history_frame 把 naive date 本地化到市场时区。Timestamp.timestamp() 对 naive 值使用主机本地时区；在 UTC 服务器上，A 股 09:30 会比 Asia/Shanghai 正确瞬间偏移 8 小时，可能返回 no_data 或错选窗口。
- **影响与判定依据：** PR #15 新增严格市场时区规范化，但调用顺序没有把规范化置于所有时间运算之前，形成同一路径内两套时间语义。
- **修复建议 / 关闭条件：** 公开 prepare/normalize 函数并在任何 range/first-row 时间判断前调用；增加 UTC 主机 + A 股 naive 时间的路由级回归测试。
- **最小复现：** 本地最小复现：naive 2026-05-03 09:30 与 Asia/Shanghai 本地化后的 Unix 秒相差 28800 秒。

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 第 686–697 行先过滤、后调用严格转换
- [`src/tradingview_zy/web_payloads.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_payloads.py) — 第 17–40 行才进行市场时区本地化；第 85–95 行过滤直接 timestamp

<a id="NEW-05"></a>

### NEW-05 · FIFO lot 在结算校验完成前原地消费，异常会留下“lot 已减、聚合仓位未减”的半提交状态

- **V7 状态：** 🆕 新问题（未修复）
- **严重程度 / 可信度：** 高 / 确定
- **领域：** Backtesting / Accounting
- **来源：** 修改引入（PR #15 新增 lot accounting）
- **最新结论：** 平仓路径先 consume_fifo_lots(pos.lots, ...) 原地减少/删除 lot，再调用 close_settlement 校验 close price、direction、期货 symbol_size 等。若后者抛错，后续聚合 amount/now_pos_rate/cash 尚未提交，但 pos.lots 已被修改，状态模型分叉。
- **影响与判定依据：** 新会计实现把“计算”和“提交”混在可失败操作之前，缺少事务式 all-or-nothing 边界。
- **修复建议 / 关闭条件：** 让 lot 消费成为纯函数/对深拷贝工作；所有结算参数验证通过后一次性替换 lots、amount、rate、cash、records。增加无效 symbol_size/fee/price 的故障注入回归测试。
- **最小复现：** 最小复现：10 单位 lot 先消费 5，随后 futures_symbol_size=0 抛错；异常后 lot 仍只剩 5、hold_balance 只剩 500。

#### 当前证据

- [`src/tradingview_zy/backtesting/accounting.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/accounting.py) — consume_fifo_lots 第 189–248 行原地修改；close_settlement 第 251–270 行仍可失败
- [`src/tradingview_zy/backtesting/backtest_trader.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/backtest_trader.py) — 平仓路径先消费 lots 再做结算校验

<a id="NX-20"></a>

### NX-20 · 多个 TDX-ExHq 构造器用无上限 while True 重连

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 多个 TDX-ExHq 构造器仍使用无上限 while True 重连；V6 顶层“已修复”没有源码依据。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 有限次数+指数退避+总 deadline；失败抛 ProviderUnavailableError；构造器不得永久阻塞。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tdx_futures.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_futures.py) — 无上限构造重试
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_hk.py) — 无上限构造重试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-20 · 多个 TDX-ExHq 构造器用无上限 while True 重连

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 确定
- **领域：** TDX Reliability
- **来源：** 本次补充排查新发现
- **标签：** 可靠性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_futures.py、src/tradingview_zy/exchange/exchange_tdx_hk.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 有界重试、总 deadline、熔断并把市场标记 degraded。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 初始化 market_maps 时捕获 TdxConnectionError 后重选 IP 并继续无限循环，没有总 deadline；选优本身也可能失败。

**正确行为应该是什么：** 有界重试、总 deadline、熔断并把市场标记 degraded。

**直观例子：** while True 只有连接成功才退出，持续故障时没有最大次数或总超时，服务可能一直卡在初始化。

#### 2. 影响分析

Web eager 初始化可永久卡住，健康检查和优雅退出失效。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 持续连接失败时在 deadline 内返回。 修改前测试应失败。
2. **实施修复：** 有界重试、总 deadline、熔断并把市场标记 degraded。
3. **执行回归验证：** 持续连接失败时在 deadline 内返回。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 有界重试、总 deadline、熔断并把市场标记 degraded。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_futures.py、src/tradingview_zy/exchange/exchange_tdx_hk.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 沿 TDX 候选筛选、results 空集、构造器 while True、异常捕获和 reset 路径检查终止性与总体 deadline。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_tdx_futures.py' 'src/tradingview_zy/exchange/exchange_tdx_hk.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_tdx_futures.py（43-L80）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_futures.py#L43-L80) — 无上限初始化循环
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py（41-L69）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_hk.py#L41-L69) — 同类模式
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-08"></a>

### RV-08 · 系统设置页把已保存的飞书 App Secret 明文回显，并在控制台打印提交字段

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** setting.html 当前仍以 type=text 和 value="{{ fs_app_secret }}" 回显旧 Secret，并在提交回调中 console.log(data.field)。
- **判定依据：** V6 顶层“已修复”与其展开记录及当前源代码直接冲突；该文件未被 PR #15 修改，因此这是 V6 误标纠正，不是新回归。
- **仍有什么问题 / 下一步：** 不返回旧 Secret；使用 password 输入与留空不改语义；删除日志；增加响应/DOM/控制台无 Secret 测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/templates/setting.html`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/templates/setting.html) — Secret value 和 console.log 仍存在

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-08 · 系统设置页把已保存的飞书 App Secret 明文回显，并在控制台打印提交字段

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 设置页不再回显或控制台打印 Secret。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 确定
- **领域：** Web Security / Secrets
- **来源：** 本次仓库复验新增
- **工作量：** M
- **标签：** 安全、CWE-200、CWE-522

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 Web 认证已加强，但 setting.html 仍把 fs_app_secret 放进普通文本框 value，并继续 console.log(data.field)。

**剩余工作：** GET 不返回旧 secret，只显示“已配置”；轮换重认证；移除日志；使用专用 secret store和最小权限。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** GET /setting 取出 fs_app_secret 并传模板；模板 type="text" + value 完整回显。保存前 console.log(data.field) 含 secret。默认空密码+0.0.0.0 形成直接远程读取链。

**正确行为应该是什么：** GET 不返回旧 secret，只显示“已配置”；轮换重认证；移除日志；使用专用 secret store和最小权限。

**直观例子：** 页面把 Secret 当普通文本写进 HTML，并把表单打印到浏览器控制台；能打开页面或读取控制台的人都能看到它。

#### 2. 影响分析

访问者可窃取飞书应用凭据、冒充机器人或访问授权 API，也可覆盖配置中断通知。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 预置哨兵 secret，请求/DOM/控制台/日志均不得出现；未授权不能读写；轮换后旧值失效。 修改前测试应失败。
2. **实施修复：** GET 不返回旧 secret，只显示“已配置”
3. **实施修复：** 轮换重认证
4. **实施修复：** 移除日志
5. **实施修复：** 使用专用 secret store和最小权限。
6. **执行回归验证：** 预置哨兵 secret，请求/DOM/控制台/日志均不得出现；未授权不能读写；轮换后旧值失效。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** GET 不返回旧 secret，只显示“已配置”；轮换重认证；移除日志；使用专用 secret store和最小权限。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 Web 认证已加强，但 setting.html 仍把 fs_app_secret 放进普通文本框 value，并继续 console.log(data.field)。

**原报告采用的排查方法：** 追踪秘密从配置/数据库读取到模板、DOM、JavaScript 日志和网络提交的完整数据流，并结合默认认证检查可读取范围。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/templates/setting.html' 'web/tradingview_zy_chart/cl_app/templates/setting.html'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`web/tradingview_zy_chart/cl_app/templates/setting.html（29-L34）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L29-L34)
- [`web/tradingview_zy_chart/cl_app/templates/setting.html（125-L132）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L125-L132)
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：高 · 可信度：高

</details>

## 严重程度：高 · 可信度：高

</details>

## 严重程度：高 · 可信度：高

<a id="HI-13"></a>

### HI-13 · Binance 合约/现货增量分页可能重复边界或停滞，单行缓存会越界

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** Binance 合约/现货增量逻辑仍读取 db_klines.iloc[-2]，单行缓存会越界；分页起点仍可能停在上页最后时间戳，造成重复边界或停滞。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 单行/空缓存显式分支；下一页起点推进一个最小周期；去重并检测无进展。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_binance.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_binance.py) — 合约增量分页
- [`src/tradingview_zy/exchange/exchange_binance_spot.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_binance_spot.py) — 现货增量分页

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-13 · Binance 合约/现货增量分页可能重复边界或停滞，单行缓存会越界

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 高
- **领域：** Binance
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、可靠性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_binance.py、src/tradingview_zy/exchange/exchange_binance_spot.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 实现统一分页游标：验证 next_cursor 严格前进、端点偏移、最大页数、空页终止；缓存 0/1/N 行均安全；最后按主键去重并验证连续性。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 缓存更新读取 iloc[-2]，只有一行时直接越界；分页使用上次边界时间继续请求，未统一 +1ms/-1ms 与严格进度断言，包含端点的 API 可能反复返回同一根。合约和现货实现重复该模式。

**正确行为应该是什么：** 实现统一分页游标：验证 next_cursor 严格前进、端点偏移、最大页数、空页终止；缓存 0/1/N 行均安全；最后按主键去重并验证连续性。

**直观例子：** 分页游标必须严格向前移动；若下一页仍从同一边界开始，就可能重复、停滞或漏数据。

#### 2. 影响分析

同步任务崩溃、无限循环、重复 K 线或缺口；定时任务可能持续占用 API 配额。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 伪造包含端点、空页、仅一行、重复页和乱序页的 API 响应；断言有限终止且输出无重无缺。 修改前测试应失败。
2. **实施修复：** 实现统一分页游标：验证 next_cursor 严格前进、端点偏移、最大页数、空页终止
3. **实施修复：** 缓存 0/1/N 行均安全
4. **实施修复：** 最后按主键去重并验证连续性。
5. **执行回归验证：** 伪造包含端点、空页、仅一行、重复页和乱序页的 API 响应；断言有限终止且输出无重无缺。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 实现统一分页游标：验证 next_cursor 严格前进、端点偏移、最大页数、空页终止；缓存 0/1/N 行均安全；最后按主键去重并验证连续性。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_binance.py、src/tradingview_zy/exchange/exchange_binance_spot.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 沿缓存增量更新和 fetch_ohlcv 分页游标检查单行索引、端点包含、严格进度、去重和终止条件。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_binance.py' 'src/tradingview_zy/exchange/exchange_binance_spot.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_binance.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_binance.py)
- [`src/tradingview_zy/exchange/exchange_binance_spot.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_binance_spot.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="HI-14"></a>

### HI-14 · ExchangeTq 构造即启动非 daemon 线程，队列/缓存无同步与确定性关闭

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** ExchangeTq 构造仍启动非 daemon 线程；共享队列/字典缺少同步，close() 只置标记并 sleep，没有 join/确定性释放。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 显式 start/close 生命周期、daemon 策略、锁/线程安全队列、join timeout 和资源释放测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tq.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tq.py) — 线程启动、共享状态和关闭路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-14 · ExchangeTq 构造即启动非 daemon 线程，队列/缓存无同步与确定性关闭

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 高
- **领域：** TQ SDK
- **来源：** 此前审查
- **工作量：** L
- **标签：** 可靠性、正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tq.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 显式 start/close 生命周期；Queue + Lock/Event；正常关闭必须 join；删除带参数单例或按配置键缓存实例。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 单例构造时启动默认非 daemon Thread；command_tasks、past_commands、res_klines/res_ticks 在调用线程和工作线程间直接共享；关闭只设置布尔并 sleep，不 join。单例还固定第一次构造参数。

**正确行为应该是什么：** 显式 start/close 生命周期；Queue + Lock/Event；正常关闭必须 join；删除带参数单例或按配置键缓存实例。

**直观例子：** 缓存读写键、原子写入和损坏恢复必须一致，否则缓存反而制造重复请求或数据缺口。

#### 2. 影响分析

测试/进程无法退出、竞态导致漏命令或脏读、Web 多实例生命周期失控；API 重启期间订单和行情状态可能丢失。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 并发提交命令、重复启动/关闭、异常重启、进程退出和多线程读写压力测试。 修改前测试应失败。
2. **实施修复：** 显式 start/close 生命周期
3. **实施修复：** Queue + Lock/Event
4. **实施修复：** 正常关闭必须 join
5. **实施修复：** 删除带参数单例或按配置键缓存实例。
6. **执行回归验证：** 并发提交命令、重复启动/关闭、异常重启、进程退出和多线程读写压力测试。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 显式 start/close 生命周期；Queue + Lock/Event；正常关闭必须 join；删除带参数单例或按配置键缓存实例。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tq.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 ExchangeTq 构造时线程启动、daemon/join、共享队列/字典、停止事件和带参数 singleton 语义。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_tq.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_tq.py（19-L145）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tq.py#L19-L145)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="CR-05"></a>

### CR-05 · CTP 行情与交易代码存在多处确定性失效，但当前未接入标准工厂或内置启动脚本

- **V7 状态：** 🛡️ 未完全修复（已阻断或缓解）
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** CTP 行情/交易实现仍未达到可用状态，标准工厂继续 fail-closed，不会把未完成实现作为正常 provider 加载。底层文件仍保留。
- **判定依据：** V6 将标准入口阻断标成“通过移除已修复”，但实现没有真正删除或修复；V7 按功能根因仍在、风险入口被阻断，调整为“未完全修复（已阻断或缓解）”。
- **仍有什么问题 / 下一步：** 继续保持 fail-closed。恢复 CTP 前必须补齐抽象方法、Tick 契约、交易状态机、回报/重连/资源释放，并在仿真前置环境验证。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/__init__.py) — 标准工厂对不可用 CTP fail-closed
- [`tests/test_ctp_unavailable.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_ctp_unavailable.py) — 不导入、缓存不污染测试
- [`src/tradingview_zy/exchange/exchange_ctp.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_ctp.py) — 底层未完成实现仍在

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### CR-05 · CTP 行情与交易代码存在多处确定性失效，但当前未接入标准工厂或内置启动脚本

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 未完成 CTP 行情/交易实现已下线；配置和工厂不再声称可用。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🛡️ **未修复（已阻断/缓解）**
- **历史严重程度：** 高
- **可信度：** 确定
- **领域：** CTP
- **来源：** 双方
- **工作量：** XL
- **标签：** 正确性、需求、规范、外部 O-07、遗漏报告 NX-02（已并入本项）

#### 当前状态与最新验证

**最新 master 验证结论：** CTP 行情和交易实现本身没有修复。最新 master 采取 fail-closed：当 EXCHANGE_FUTURES="ctp" 时，标准工厂明确抛出“CTP 当前不可用”，且不会导入未完成模块；README、配置模板和测试也明确标注 CR-05 尚未修复。这降低了误配置风险，但 CTP 功能依然不可用。

**剩余工作：** 要标记已修复，仍需补齐抽象接口、Tick 类型、时间调用、交易 API、订单回报和仿真集成测试。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** MarketCTP 未实现 Exchange 的 all_stocks、stock_info、stock_owner_plate、plate_stocks 等抽象方法；行情回调向基础 Tick dataclass 传入 time、amount 和多档盘口字段；now_trading 又在 `from datetime import datetime` 后调用 `datetime.datetime.now()`。CTPTrader 还重复定义多个方法，后定义覆盖前定义，并含未导入/不一致的 API 名称。完整仓库调用图同时表明：当前 get_exchange() 的期货分支只支持 tq、tdx_futures、db，未接入 CTP；`script/trader/reboot_trader_ctp.py` 只是不可用提示。

**正确行为应该是什么：** 启用 CTP 前必须修复；若当前不计划支持，应从配置、文档和运行包中明确移除该能力。统一 OpenCTP SDK，拆分行情与交易协议，补齐抽象方法，建立可容纳盘口深度的类型，删除重复方法，并在仿真前置环境完成登录、行情、下单、回报、断线恢复和释放资源测试。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

直接实例化或由外部私有脚本启用 CTP 时，类会先因抽象方法缺失而无法实例化；即使补齐抽象方法，行情回调和部分交易路径仍会继续失败。它不构成当前默认 Web 启动阻断，但对任何准备启用 CTP 的部署仍是明确的上线阻断。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 底层功能仍未修好，只是标准入口已经拒绝或风险已降低。必须保留当前阻断，禁止绕过标准入口启用该功能。

1. **先写失败测试：** 先执行 import/abstract-class/instantiate smoke test；再用假的 CTP SPI 回调验证五档和二十档 Tick；最后在仿真环境覆盖认证、登录、订阅、开多、开空、平今、平昨、拒单、部分成交和重连。标准 Web 工厂测试还应断言未配置 CTP 时不会导入该模块。 修改前测试应失败。
2. **实施修复：** 启用 CTP 前必须修复
3. **实施修复：** 若当前不计划支持，应从配置、文档和运行包中明确移除该能力。
4. **实施修复：** 统一 OpenCTP SDK，拆分行情与交易协议，补齐抽象方法，建立可容纳盘口深度的类型，删除重复方法，并在仿真前置环境完成登录、行情、下单、回报、断线恢复和释放资源测试。
5. **执行回归验证：** 先执行 import/abstract-class/instantiate smoke test；再用假的 CTP SPI 回调验证五档和二十档 Tick；最后在仿真环境覆盖认证、登录、订阅、开多、开空、平今、平昨、拒单、部分成交和重连。标准 Web 工厂测试还应断言未配置 CTP 时不会导入该模块。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 要标记已修复，仍需补齐抽象接口、Tick 类型、时间调用、交易 API、订单回报和仿真集成测试。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** CTP 行情和交易实现本身没有修复。最新 master 采取 fail-closed：当 EXCHANGE_FUTURES="ctp" 时，标准工厂明确抛出“CTP 当前不可用”，且不会导入未完成模块；README、配置模板和测试也明确标注 CR-05 尚未修复。这降低了误配置风险，但 CTP 功能依然不可用。

**原报告采用的排查方法：** 在完整工作树中比较 Exchange 抽象方法与 MarketCTP 方法集合，统计 CTPTrader 重复定义，核对 Tick 构造参数，并沿 get_exchange() 与 script/trader 启动入口检查可达性。

**可自行执行的复核命令：** `pytest -q tests/test_ctp_unavailable.py`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 没有连接 CTP 仿真或实盘前置；第三方 SDK 的具体报错文本和回调时序仍需动态验证。

**最新证据：**

- [`CTP fail-closed 工厂`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py#L66-L85) — 不导入未完成模块
- [`CTP 不可用测试`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_ctp_unavailable.py) — 模块未导入、缓存未污染
- [`底层未修复实现`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_ctp.py) — 功能仍不可用
- [`src/tradingview_zy/exchange/exchange.py（24-L150）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange.py#L24-L150)
- [`src/tradingview_zy/exchange/exchange_ctp.py（25-L310）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_ctp.py#L25-L310)
- [`src/tradingview_zy/trader/trader_ctp.py（116-L340）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_ctp.py#L116-L340)
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py) — 标准期货工厂无 CTP 分支
- [`script/trader/reboot_trader_ctp.py（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 内置启动脚本仅输出已移除提示
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="CR-04"></a>

### CR-04 · QMT 交易适配器真实买入确定性引用未定义 price；当前无内置活跃启动入口

- **V7 状态：** 🛡️ 未完全修复（已阻断或缓解）
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** QMT 交易类的底层错误实现仍在仓库并可被直接导入；标准应用当前没有内置活跃启动入口，且统一能力模型没有把它作为可用交易执行能力暴露。
- **判定依据：** V6 把“无标准入口”直接等同于“已修复（移除）”过度关闭了问题。代码并未删除，也没有修好真实下单路径，因此只能判为已阻断/缓解。
- **仍有什么问题 / 下一步：** 不得绕过标准工厂启用该类。若恢复支持，需修正报价/数量、订单状态、真实失败不得模拟成功，并完成 QMT 沙箱集成测试；否则应真正移出运行包。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/trader/trader_qmt_stock.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/trader/trader_qmt_stock.py) — 底层 QMT trader 仍存在
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 当前能力注册未把该 trader 声明为可用交易执行入口

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### CR-04 · QMT 交易适配器真实买入确定性引用未定义 price；当前无内置活跃启动入口

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 包含未定义 price 和模拟成功回退的 QMT trader 已从运行树移除。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 确定
- **领域：** QMT Trader
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、需求

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/trader/trader_qmt_stock.py、src/tradingview_zy/trader/trader_qmt_stock.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 任何实际启用 QMT 交易前必须修复。先取得并校验报价；将路径、账号和模式改成强制配置；使用 client_order_id/order_id 驱动订单终态与成交明细；真实模式失败绝不能自动降级为模拟并写真实账本。若此适配器不再维护，应从运行包移除。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** QMTTraderStock.open_buy() 在真实交易分支先执行 `amount = int(balance / price / 100) * 100`，但 price 尚未赋值；若将该行修掉而订单列表中又找不到 order_id，price/amount 仍可能未绑定。持仓达到上限或计算数量不足 100 时，代码转入模拟成交分支并继续发送消息、修改自选和写订单表。完整仓库 `git grep` 未找到该类的内置调用方，类只在自身文件中定义和演示。

**正确行为应该是什么：** 任何实际启用 QMT 交易前必须修复。先取得并校验报价；将路径、账号和模式改成强制配置；使用 client_order_id/order_id 驱动订单终态与成交明细；真实模式失败绝不能自动降级为模拟并写真实账本。若此适配器不再维护，应从运行包移除。

**直观例子：** 直观地看，这项问题意味着：直接或由外部脚本启用 QMT 交易类时，真实买入首先触发 NameError；

#### 2. 影响分析

直接或由外部脚本启用 QMT 交易类时，真实买入首先触发 NameError；某些不满足实盘条件的路径又会落成“模拟成功”并写入与真实订单共用的记录。当前普通 Web 行情选择 qmt 只使用 ExchangeQMT，不会自动实例化 QMTTraderStock，因此不属于默认 Web 启动故障。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 使用 fake XtQuantTrader 覆盖无报价、资金不足、持仓达到上限、订单未出现、拒单、部分成交和连接失败；断言真实模式异常时不写订单、不修改持仓组，也不返回成功成交。另做调用图门禁，防止未审计适配器被启动脚本重新接入。 修改前测试应失败。
2. **实施修复：** 任何实际启用 QMT 交易前必须修复。
3. **实施修复：** 先取得并校验报价
4. **实施修复：** 将路径、账号和模式改成强制配置
5. **实施修复：** 使用 client_order_id/order_id 驱动订单终态与成交明细
6. **实施修复：** 真实模式失败绝不能自动降级为模拟并写真实账本。
7. **实施修复：** 若此适配器不再维护，应从运行包移除。
8. **执行回归验证：** 使用 fake XtQuantTrader 覆盖无报价、资金不足、持仓达到上限、订单未出现、拒单、部分成交和连接失败；断言真实模式异常时不写订单、不修改持仓组，也不返回成功成交。另做调用图门禁，防止未审计适配器被启动脚本重新接入。 同时运行相邻模块测试。
9. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 任何实际启用 QMT 交易前必须修复。先取得并校验报价；将路径、账号和模式改成强制配置；使用 client_order_id/order_id 驱动订单终态与成交明细；真实模式失败绝不能自动降级为模拟并写真实账本。若此适配器不再维护，应从运行包移除。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/trader/trader_qmt_stock.py、src/tradingview_zy/trader/trader_qmt_stock.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 逐行跟踪 QMTTraderStock 构造、open_buy 的变量赋值和订单查询分支，并在完整仓库执行类名/模块引用搜索确认内置可达性。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/trader/trader_qmt_stock.py' 'src/tradingview_zy/trader/trader_qmt_stock.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未安装或连接 QMT；结论不依赖 SDK 行为，但真实订单状态和回调时序仍需 QMT 沙箱验证。

**最新证据：**

- [`src/tradingview_zy/trader/trader_qmt_stock.py（77-L189）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_qmt_stock.py#L77-L189)
- [`src/tradingview_zy/trader/trader_qmt_stock.py（92-L109）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_qmt_stock.py#L92-L109) — 硬编码路径和资金账号
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="HI-06"></a>

### HI-06 · 状态变更接口无 CSRF 防护，删除任务还使用 GET

- **V7 状态：** 🛡️ 未完全修复（已阻断或缓解）
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 登录与 Cookie 已加强，但状态变更接口仍没有 CSRF token/Origin 校验，删除提醒任务继续使用 GET。
- **判定依据：** 当前只能证明危险路径 fail-closed/不可达，不能证明底层实现正确，因此不能标记已修复。
- **仍有什么问题 / 下一步：** 引入 CSRF 中间件；所有写操作改 POST/DELETE；SameSite 只作纵深防御，不替代 token。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — alert_del 等写路由
- [`src/tradingview_zy/web_security.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_security.py) — 仅认证/会话防护

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-06 · 状态变更接口无 CSRF 防护，删除任务还使用 GET

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 高
- **领域：** Web Security
- **来源：** 此前审查
- **工作量：** M
- **标签：** 安全、CWE-352

#### 当前状态与最新验证

**最新 master 验证结论：** 登录与 Cookie 安全已加强，但项目仍没有 CSRF token、中间件或 Origin 校验；/alert_del/<id> 仍是 GET 写操作。

**剩余工作：** 启用全局 CSRF 中间件；所有写操作只允许 POST/PUT/DELETE；校验 Origin/Referer；危险操作要求二次确认或重认证。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 应用未配置 CSRF token；多条 POST 路由依赖 Cookie 登录态；/alert_del/<id> 通过 GET 删除并重建调度任务。

**正确行为应该是什么：** 启用全局 CSRF 中间件；所有写操作只允许 POST/PUT/DELETE；校验 Origin/Referer；危险操作要求二次确认或重认证。

**直观例子：** 用户登录后打开恶意网页，该网页可能借现有 Cookie 发删除请求；服务端没有 CSRF 令牌来确认请求是否来自本系统页面。

#### 2. 影响分析

已登录操作者可被恶意页面诱导执行删除、修改自选、保存策略或标记等操作。空密码默认配置进一步降低攻击门槛。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 无 token、错误 token、跨 Origin 和 GET 删除请求均返回 4xx；合法同源 token 请求成功。 修改前测试应失败。
2. **实施修复：** 启用全局 CSRF 中间件
3. **实施修复：** 所有写操作只允许 POST/PUT/DELETE
4. **实施修复：** 校验 Origin/Referer
5. **实施修复：** 危险操作要求二次确认或重认证。
6. **执行回归验证：** 无 token、错误 token、跨 Origin 和 GET 删除请求均返回 4xx；合法同源 token 请求成功。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 启用全局 CSRF 中间件；所有写操作只允许 POST/PUT/DELETE；校验 Origin/Referer；危险操作要求二次确认或重认证。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 登录与 Cookie 安全已加强，但项目仍没有 CSRF token、中间件或 Origin 校验；/alert_del/<id> 仍是 GET 写操作。

**原报告采用的排查方法：** 沿默认配置、登录/会话、路由方法、Cookie 和前端 DOM 数据流逐层检查；对可控文本确认最终进入 text API 还是 HTML 解释器，并核对 CSRF/来源校验。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：中 · 可信度：确定

</details>

## 严重程度：中 · 可信度：确定

</details>

## 严重程度：中 · 可信度：确定

<a id="CR-03"></a>

### CR-03 · 实盘订单缺少成交状态机，内部账本可与券商/交易所永久分叉

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 旧 trader 启动提示脚本已删除，但 QMT/TQ/Binance 等交易类的订单提交、成交确认和重启对账没有改变；状态机缺口仍在。
- **判定依据：** V6 已记录部分缓解；最新 master 未出现足以关闭全部根因的新增证据，状态保持部分修复。
- **仍有什么问题 / 下一步：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账；未确认成交必须 fail closed。现有启动器保持禁用，直到每个适配器通过沙箱验收。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/trader/trader_qmt_stock.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/trader/trader_qmt_stock.py) — 当前实现路径
- [`src/tradingview_zy/trader/trader_futures.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/trader/trader_futures.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tq.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tq.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_binance.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_binance.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### CR-03 · 实盘订单缺少成交状态机，内部账本可与券商/交易所永久分叉

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 高
- **可信度：** 高
- **领域：** Live Trading
- **来源：** 此前审查
- **工作量：** XL
- **标签：** 正确性、需求

#### 当前状态与最新验证

**最新 master 验证结论：** 旧 trader 启动提示脚本已删除，但 QMT/TQ/Binance 等交易类的订单提交、成交确认和重启对账没有改变；状态机缺口仍在。

**剩余工作：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账；未确认成交必须 fail closed。现有启动器保持禁用，直到每个适配器通过沙箱验收。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 多个交易适配器把“已提交”“等待固定秒数后查询一次”“外部当前无持仓”或“本地行情价格”当成成功成交，缺少统一 Submitted/Accepted/PartiallyFilled/Filled/Cancelled/Rejected 状态、成交明细累计、client_order_id 幂等和重启对账。完整仓库还显示内置 trader 启动脚本当前均为不可用提示，风险主要在直接调用或外部私有脚本重新接入这些类时触发。

**正确行为应该是什么：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账；未确认成交必须 fail closed。现有启动器保持禁用，直到每个适配器通过沙箱验收。

**直观例子：** 直观地看，这项问题意味着：一旦真实启用，拒单、部分成交、延迟成交、撤单和断线可能使内部仓位、现金和数据库订单与券商永久分叉，继而引发重复下单或错误平仓。

#### 2. 影响分析

一旦真实启用，拒单、部分成交、延迟成交、撤单和断线可能使内部仓位、现金和数据库订单与券商永久分叉，继而引发重复下单或错误平仓。当前提交不会通过内置启动脚本自动进入实盘，但项目仍公开这些类并自述为交易工具，不能据此视为安全。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 强烈建议优先修复；该问题可能直接影响安全、资金、核心数据正确性或服务可用性。

1. **先写失败测试：** 每个适配器都要覆盖拒单、部分成交、延迟回报、取消、断线重连、重复回调、进程重启和外部手工改仓；逐笔断言外部 fills、内部数量、均价、费用、现金和数据库一致。 修改前测试应失败。
2. **实施修复：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账
3. **实施修复：** 未确认成交必须 fail closed。
4. **实施修复：** 现有启动器保持禁用，直到每个适配器通过沙箱验收。
5. **执行回归验证：** 每个适配器都要覆盖拒单、部分成交、延迟回报、取消、断线重连、重复回调、进程重启和外部手工改仓；逐笔断言外部 fills、内部数量、均价、费用、现金和数据库一致。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 真实资金启用前必须建立统一 Order/Fill 状态机、幂等 client_order_id、持久化成交明细和重启对账；未确认成交必须 fail closed。现有启动器保持禁用，直到每个适配器通过沙箱验收。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 旧 trader 启动提示脚本已删除，但 QMT/TQ/Binance 等交易类的订单提交、成交确认和重启对账没有改变；状态机缺口仍在。

**原报告采用的排查方法：** 跨 trader/exchange/DB 跟踪订单提交、固定等待、查询、返回值和内部落账；再检查 script/trader 的实际入口。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/trader/trader_qmt_stock.py' 'src/tradingview_zy/trader/trader_futures.py' 'src/tradingview_zy/exchange/exchange_tq.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未连接真实券商/交易所，故实际分叉概率和回报时序需要沙箱验证；静态缺口本身明确。

**最新证据：**

- [`src/tradingview_zy/trader/trader_qmt_stock.py（117-L191）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_qmt_stock.py#L117-L191)
- [`src/tradingview_zy/trader/trader_futures.py（111-L155）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_futures.py#L111-L155)
- [`src/tradingview_zy/exchange/exchange_tq.py（19-L150）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tq.py#L19-L150)
- [`src/tradingview_zy/exchange/exchange_binance.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_binance.py)
- [`script/trader/reboot_trader_futures.py（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 内置期货交易启动器为墓碑
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

## 严重程度：中（49 条）

<a id="ME-24"></a>

### ME-24 · 环境检查与 pyproject 的 Python 约束冲突，并在失败后仍打印“环境OK”

- **V7 状态：** 🔴 回归（重新出现）
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** 真实回归
- **回归判定：** 是，真实回归
- **最新结论：** PR #15 将包元数据收紧为 Python >=3.11,<3.12，以匹配 cp311-only TA-Lib wheel；但 check_env.py 仍以“>=3.11”为判定，_python_version_supported((3,12,0)) 实测返回 True，并输出“3.11 或更高版本”。
- **判定依据：** V6 快照中 pyproject 与检查器都接受 >=3.11；后续仅修改包元数据而未同步检查器，形成真实回归。
- **仍有什么问题 / 下一步：** 把环境检查改为同一 SpecifierSet/单一元数据来源，明确拒绝 3.12+；增加 pyproject 与 check_env 契约一致性测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`check_env.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/check_env.py) — 仍使用 MIN_PYTHON=(3,11) 的单下界检查
- [`pyproject.toml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/pyproject.toml) — 当前 requires-python 为 >=3.11,<3.12
- [`tests/test_batch01_small_fixes.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_batch01_small_fixes.py) — 现有环境检查测试未覆盖上界

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-24 · 环境检查与 pyproject 的 Python 约束冲突，并在失败后仍打印“环境OK”

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Environment
- **来源：** 双方
- **工作量：** S
- **标签：** 规范、可靠性、外部 O-12、外部 O-35

#### 当前状态与最新验证

**最新 master 验证结论：** 旧 PyArmor 授权检查已经从 check_env.py 和依赖中删除，这是有效修复。但最新 check_env.py 仍只接受 3.8–3.11，与 pyproject.toml 的 >=3.11 不一致；仍导入 Python 3.13 已移除的 telnetlib，网络检查缺少明确 timeout/close，最后仍可能打印“环境OK”。

**剩余工作：** 统一 Python 版本来源、替换 telnetlib、让必需检查失败返回非零退出码，并区分 OK/DEGRADED/FAILED。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** pyproject 要求 >=3.11；check_env 接受 3.8–3.11并拒绝 3.12+。代理/Redis/MySQL/授权失败多仅打印，结尾无条件输出环境OK；telnet 无显式超时/关闭，保留旧 pyarmor 授权检查。

**正确行为应该是什么：** 从项目 metadata 读取版本约束；每项返回结构化 status，必需项失败 exit!=0，可选项 degraded；删除过时授权逻辑。

**直观例子：** 直观地看，这项问题意味着：用户可能在不支持环境中继续运行，或在 3.12+ 被错误拒绝；

#### 2. 影响分析

用户可能在不支持环境中继续运行，或在 3.12+ 被错误拒绝；自动化无法从退出码判断健康。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 3.10/3.11/3.12 版本模拟、各依赖失败和退出码测试。 修改前测试应失败。
2. **实施修复：** 从项目 metadata 读取版本约束
3. **实施修复：** 每项返回结构化 status，必需项失败 exit!=0，可选项 degraded
4. **实施修复：** 删除过时授权逻辑。
5. **执行回归验证：** 3.10/3.11/3.12 版本模拟、各依赖失败和退出码测试。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 统一 Python 版本来源、替换 telnetlib、让必需检查失败返回非零退出码，并区分 OK/DEGRADED/FAILED。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 旧 PyArmor 授权检查已经从 check_env.py 和依赖中删除，这是有效修复。但最新 check_env.py 仍只接受 3.8–3.11，与 pyproject.toml 的 >=3.11 不一致；仍导入 Python 3.13 已移除的 telnetlib，网络检查缺少明确 timeout/close，最后仍可能打印“环境OK”。

**原报告采用的排查方法：** 比较 pyproject Python 约束与 check_env 白名单/导入顺序，并在当前 Python 版本核对已移除标准库。

**可自行执行的复核命令：** `python check_env.py; echo $?`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 仓库文件和本地测试环境已核对；未执行所有平台原生安装、在线漏洞数据库或托管 CI 服务。

**最新证据：**

- [`当前环境检查`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/check_env.py#L15-L76) — 版本列表、telnetlib、环境OK
- [`项目 Python 约束`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/pyproject.toml#L3-L9) — >=3.11
- [`遗留清理提交`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — PyArmor 授权检查已删除
- [`check_env.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/check_env.py)
- [`pyproject.toml`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/pyproject.toml)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NEW-06"></a>

### NEW-06 · MarketRegistry 过报 DB provider 的 security_master/plates 能力

- **V7 状态：** 🆕 新问题（未修复）
- **严重程度 / 可信度：** 中 / 确定
- **领域：** Architecture / Exchange Contract
- **来源：** 修改引入（PR #15 新增能力注册表）
- **最新结论：** DB_CAPABILITIES 被定义为 MARKET_DATA + TICKS + SECURITY_MASTER + PLATES，并用于所有市场的 db provider；但 ExchangeDB.all_stocks() 固定返回空列表，stock_owner_plate() 和 plate_stocks() 为 pass。调用方通过 require_capability 后仍会得到空/None，而不是“能力不支持”。
- **影响与判定依据：** 能力声明的目的就是在调用前可靠判断；声明与实现不一致会把 fail-closed 重新变成静默空结果。该问题也放大了历史 NX-23。
- **修复建议 / 关闭条件：** DB provider 只声明真实实现的 MARKET_DATA/TICKS；或实现安全主数据/板块查询。为每个 Capability 增加行为级契约测试，不能只检查集合存在。
- **最小复现：** 静态契约复核：registry 声明 SECURITY_MASTER/PLATES，目标方法分别返回 []/None。

#### 当前证据

- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — DB_CAPABILITIES=MD_PLATES 并应用于所有 db provider
- [`src/tradingview_zy/exchange/exchange_db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_db.py) — all_stocks 空列表、板块方法 pass
- [`tests/test_v6_market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_market_registry.py) — 当前测试只验证声明/路由，未验证方法行为

<a id="HI-01"></a>

### HI-01 · TraderFutures 使用不存在的构造参数，实例化立即失败

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** TraderFutures 虽已传入 market，但仍调用 ExchangeTq(use_account=True)，而构造器参数是 use_simulate_account；直接实例化仍会 TypeError。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 统一构造参数与 order_type；若不支持该 trader，应从运行包删除并加不可达测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/trader/trader_futures.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/trader/trader_futures.py) — 错误 ExchangeTq 构造参数
- [`src/tradingview_zy/exchange/exchange_tq.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tq.py) — 实际构造签名

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-01 · TraderFutures 使用不存在的构造参数，实例化立即失败

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Futures Trader
- **来源：** 双方
- **工作量：** S
- **标签：** 正确性、需求、外部 O-19

#### 当前状态与最新验证

**最新 master 验证结论：** 旧启动提示脚本被删除，但 TraderFutures 和 ExchangeTq 本体没有修改，错误构造参数和错误 order_type 仍存在。

**剩余工作：** 若继续保留，统一构造模式枚举并修正落库 order_type；若不再支持则移出运行包。不要仅把参数名改对而忽略订单账本错误。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** TraderFutures 调用 `ExchangeTq(use_account=True)`，而 ExchangeTq.__init__ 只接受 use_simulate_account，直接实例化会 TypeError；close_buy() 成功后又把平多落库为 `open_long`。完整仓库没有活跃的内置启动入口，`reboot_trader_futures.py` 仅输出已移除提示。

**正确行为应该是什么：** 若继续保留，统一构造模式枚举并修正落库 order_type；若不再支持则移出运行包。不要仅把参数名改对而忽略订单账本错误。

**直观例子：** 直观地看，这项问题意味着：直接或由外部脚本实例化时，类在进入交易逻辑前失败；

#### 2. 影响分析

直接或由外部脚本实例化时，类在进入交易逻辑前失败；修正构造后，平多订单仍会被错误记成开多。当前默认 Web/任务路径不调用该类。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 参数化测试 market-data/sim/live 构造；fake ExchangeTq 覆盖四种开平仓，断言外部操作和数据库 order_type 一致；调用图测试保证未验收前无内置启动器。 修改前测试应失败。
2. **实施修复：** 若继续保留，统一构造模式枚举并修正落库 order_type
3. **实施修复：** 若不再支持则移出运行包。
4. **实施修复：** 不要仅把参数名改对而忽略订单账本错误。
5. **执行回归验证：** 参数化测试 market-data/sim/live 构造；fake ExchangeTq 覆盖四种开平仓，断言外部操作和数据库 order_type 一致；调用图测试保证未验收前无内置启动器。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 若继续保留，统一构造模式枚举并修正落库 order_type；若不再支持则移出运行包。不要仅把参数名改对而忽略订单账本错误。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 旧启动提示脚本被删除，但 TraderFutures 和 ExchangeTq 本体没有修改，错误构造参数和错误 order_type 仍存在。

**原报告采用的排查方法：** 比较调用方实参与 ExchangeTq 签名，检查 close_buy 落库类型，并搜索完整仓库启动入口。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/trader/trader_futures.py' 'src/tradingview_zy/exchange/exchange_tq.py' 'script/trader/reboot_trader_futures.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未运行 TQ SDK；TypeError 和错误常量不依赖 SDK。

**最新证据：**

- [`src/tradingview_zy/trader/trader_futures.py（17-L140）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_futures.py#L17-L140)
- [`src/tradingview_zy/exchange/exchange_tq.py（19-L50）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tq.py#L19-L50)
- [`script/trader/reboot_trader_futures.py（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-06"></a>

### ME-06 · 自选导入和导出共用固定 zx.txt，缺少并发隔离与上传限制

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 自选导出和导入仍共用 data/zx.txt；上传直接 file.save()，没有请求体/文件大小、并发隔离和流式限制。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 每请求临时文件或内存流；MAX_CONTENT_LENGTH；扩展名/编码/行数验证；finally 清理。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 固定 zx.txt 的导入/导出路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-06 · 自选导入和导出共用固定 zx.txt，缺少并发隔离与上传限制

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** File Upload
- **来源：** 此前审查
- **工作量：** S
- **标签：** 安全、可靠性、CWE-400

#### 当前状态与最新验证

**最新 master 验证结论：** cl_app/__init__.py 的安全/策略改动没有触及自选导入导出；共享 zx.txt、一次性读取和大小限制问题仍在。

**剩余工作：** 使用请求唯一临时文件或内存流，流式解析；设置 MAX_CONTENT_LENGTH、最大行数和字段长度；响应完成后清理。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 导入和导出都使用同一个 `DATA_PATH/zx.txt`。导入直接保存并用 readlines() 一次读入；导出写同一文件，交给 send_file 后在 finally 尝试删除。并发请求会互相覆盖/删除；没有体积、行数和字段长度限制。

**正确行为应该是什么：** 使用请求唯一临时文件或内存流，流式解析；设置 MAX_CONTENT_LENGTH、最大行数和字段长度；响应完成后清理。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

并发导入/导出可串数据或返回错误文件；超大文件放大内存、CPU 和数据库写入；Windows 下文件句柄与立即删除还可能导致残留或下载失败。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 并发导入、导入/导出交叉、超限文件、长行、异常中断和 Windows 文件句柄测试。 修改前测试应失败。
2. **实施修复：** 使用请求唯一临时文件或内存流，流式解析
3. **实施修复：** 设置 MAX_CONTENT_LENGTH、最大行数和字段长度
4. **实施修复：** 响应完成后清理。
5. **执行回归验证：** 并发导入、导入/导出交叉、超限文件、长行、异常中断和 Windows 文件句柄测试。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用请求唯一临时文件或内存流，流式解析；设置 MAX_CONTENT_LENGTH、最大行数和字段长度；响应完成后清理。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** cl_app/__init__.py 的安全/策略改动没有触及自选导入导出；共享 zx.txt、一次性读取和大小限制问题仍在。

**原报告采用的排查方法：** 比较导入和导出文件路径、并发请求时序、异常清理、readlines 和应用上传大小设置。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-16"></a>

### ME-16 · IB Redis 请求使用 BRPOP timeout=0，可无限阻塞调用线程

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** ExchangeIB.ticks() 仍 BRPOP timeout=0，order 路径也存在 0 超时；调用线程可永久阻塞。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 统一有限 deadline、取消/清理响应键、明确 TimeoutError，并覆盖 Redis 无响应测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_ib.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_ib.py) — 无限 BRPOP 路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-16 · IB Redis 请求使用 BRPOP timeout=0，可无限阻塞调用线程

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Interactive Brokers
- **来源：** 此前审查
- **工作量：** M
- **标签：** 可靠性、CWE-400

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_ib.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 所有 RPC 使用有限 deadline、correlation ID、心跳和取消；超时返回 Unavailable 并触发熔断。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** ticks/订单等路径等待 Redis 返回时使用 timeout=0（永久阻塞），没有请求级 deadline、取消或 worker 存活检测。

**正确行为应该是什么：** 所有 RPC 使用有限 deadline、correlation ID、心跳和取消；超时返回 Unavailable 并触发熔断。

**直观例子：** Redis 的 BRPOP timeout=0 表示无限等待；worker 消失后调用线程不会自动返回。

#### 2. 影响分析

IB worker 停止或消息丢失时，Web 请求、同步脚本和进程池永久挂起，无法优雅停机。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** worker 不存在、延迟、错误 correlation、重复响应和 SIGTERM；所有调用在 deadline 内返回。 修改前测试应失败。
2. **实施修复：** 所有 RPC 使用有限 deadline、correlation ID、心跳和取消
3. **实施修复：** 超时返回 Unavailable 并触发熔断。
4. **执行回归验证：** worker 不存在、延迟、错误 correlation、重复响应和 SIGTERM；所有调用在 deadline 内返回。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 所有 RPC 使用有限 deadline、correlation ID、心跳和取消；超时返回 Unavailable 并触发熔断。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_ib.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 沿 Redis 请求/响应和 correlation ID 检查 BRPOP deadline、worker 心跳、取消和错误返回。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_ib.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_ib.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_ib.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-05"></a>

### ME-05 · create_app 启动时 eager 实例化全部配置市场，单个可选适配器可拖垮整个服务

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** create_app() 启动阶段仍对全部市场调用 get_exchange().support_frequencys()/default_code()，单个可选 provider 失败仍可阻断整个 Web 服务。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 注册表提供静态元数据；provider 按请求惰性实例化；可选市场失败降级为该市场不可用。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 第 173–194 行 eager 构造全部市场
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 可用于替代构造的静态元数据

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-05 · create_app 启动时 eager 实例化全部配置市场，单个可选适配器可拖垮整个服务

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Web Startup
- **来源：** 此前审查
- **工作量：** L
- **标签：** 可靠性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** create_app() 新增安全初始化后，仍在启动时创建 scheduler 并对全部市场调用 get_exchange()。

**剩余工作：** 能力注册表只读取静态 metadata；适配器按首次请求 lazy init，失败隔离为该市场 unavailable；健康检查报告原因而不终止其他市场。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** 构建 market_frequencys/default_codes 时立即对每个 Market 调 get_exchange；某一 SDK 缺失、账号未配置、网络不可达或适配器构造失败会使 Web 整体启动失败。

**正确行为应该是什么：** 能力注册表只读取静态 metadata；适配器按首次请求 lazy init，失败隔离为该市场 unavailable；健康检查报告原因而不终止其他市场。

**直观例子：** 直观地看，这项问题意味着：例如 CTP/TQ/IB 的问题会阻断只想查看 A 股图表的用户；

#### 2. 影响分析

例如 CTP/TQ/IB 的问题会阻断只想查看 A 股图表的用户；测试应用创建也产生网络/线程副作用。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 让每个适配器逐一抛错，Web 仍能启动并服务其他市场；健康接口显示 degraded。 修改前测试应失败。
2. **实施修复：** 能力注册表只读取静态 metadata
3. **实施修复：** 适配器按首次请求 lazy init，失败隔离为该市场 unavailable
4. **实施修复：** 健康检查报告原因而不终止其他市场。
5. **执行回归验证：** 让每个适配器逐一抛错，Web 仍能启动并服务其他市场；健康接口显示 degraded。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 能力注册表只读取静态 metadata；适配器按首次请求 lazy init，失败隔离为该市场 unavailable；健康检查报告原因而不终止其他市场。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** create_app() 新增安全初始化后，仍在启动时创建 scheduler 并对全部市场调用 get_exchange()。

**原报告采用的排查方法：** 沿 create_app 的顶层执行顺序追踪 scheduler 和各市场 get_exchange 构造，确认单个可选依赖失败是否被隔离。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 完整固定提交已静态核对；若需量化实际影响，仍应增加针对该路径的动态回归测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-01"></a>

### MX-01 · 钉钉配置契约破裂且 HK 分支永不可达

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 最新配置模板仍没有 DINGDING_KEY_*，utils.py 也未修改；配置契约和 HK 分支问题仍在。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 若已废弃钉钉，应删除接口和死配置分支；若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/utils.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/utils.py) — 当前实现路径
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/config.py.demo) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-01 · 钉钉配置契约破裂且 HK 分支永不可达

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 本轮没有处理钉钉配置键缺失与 HK 分支重复判断。
- **仍有什么问题 / 下一步：** 统一消息配置 schema，修复 market 映射并增加每市场路由测试。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Configuration / Messaging
- **来源：** 外部审查新增
- **标签：** 配置、可靠性、外部 O-05

#### 当前状态与最新验证

**最新 master 验证结论：** 最新配置模板仍没有 DINGDING_KEY_*，utils.py 也未修改；配置契约和 HK 分支问题仍在。

**剩余工作：** 若已废弃钉钉，应删除接口和死配置分支；若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** config_get_dingding_keys() 引用配置模板中不存在的 DINGDING_KEY_A/HK/US/FUTURES/CURRENCY，且 HK 分支再次判断 `market == "a"`。完整仓库搜索只找到 send_dd_msg 定义和已注释的调用，当前主路径使用飞书。

**正确行为应该是什么：** 若已废弃钉钉，应删除接口和死配置分支；若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。

**直观例子：** 直观地看，这项问题意味着：外部脚本或未来重新启用旧钉钉接口时会在默认模板配置下 AttributeError；

#### 2. 影响分析

外部脚本或未来重新启用旧钉钉接口时会在默认模板配置下 AttributeError；即使补齐配置，HK 仍取不到正确键。当前内置运行路径不会主动触发，因此不是默认高风险故障。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 遍历 a/hk/us/futures/currency，确认每个市场返回独立合法配置；缺配置返回明确 Unsupported/Disabled，而非 AttributeError；仓库引用扫描应与支持声明一致。 修改前测试应失败。
2. **实施修复：** 若已废弃钉钉，应删除接口和死配置分支
3. **实施修复：** 若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。
4. **执行回归验证：** 遍历 a/hk/us/futures/currency，确认每个市场返回独立合法配置；缺配置返回明确 Unsupported/Disabled，而非 AttributeError；仓库引用扫描应与支持声明一致。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 若已废弃钉钉，应删除接口和死配置分支；若继续支持，则把配置加入模板、改正 HK 判断、使用结构化配置对象并加入单元测试。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新配置模板仍没有 DINGDING_KEY_*，utils.py 也未修改；配置契约和 HK 分支问题仍在。

**原报告采用的排查方法：** 比较 utils.py 的配置属性访问与 config.py.demo，并执行全仓 send_dd_msg 引用搜索。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/utils.py' 'src/tradingview_zy/config.py.demo'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 外部私有脚本是否调用该函数无法从仓库内证明。

**最新证据：**

- [`src/tradingview_zy/utils.py（31-L46）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/utils.py#L31-L46)
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo) — 模板中没有 DINGDING_KEY_*
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-06"></a>

### MX-06 · 直接执行 db.py 会向配置数据库写测试标记

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 删除全部可执行测试写入；数据库 smoke test 移到临时 SQLite pytest fixture。模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-06 · 直接执行 db.py 会向配置数据库写测试标记

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Database / Operations
- **来源：** 外部审查新增
- **标签：** 运维、数据完整性、外部 O-21

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 删除全部可执行测试写入；数据库 smoke test 移到临时 SQLite pytest fixture。模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** db.py 在模块级创建全局 DB；文件末尾的 `if __name__ == "__main__"` 块中保留一条未注释的 marks_add_by_price() 测试写入。普通 import 会初始化数据库，但只有把 db.py 作为脚本直接运行时才写测试标记。

**正确行为应该是什么：** 删除全部可执行测试写入；数据库 smoke test 移到临时 SQLite pytest fixture。模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。

**直观例子：** 直观地看，这项问题意味着：运维人员、IDE 或调试命令直接执行该文件时会向当前配置数据库写测试价格标记；

#### 2. 影响分析

运维人员、IDE 或调试命令直接执行该文件时会向当前配置数据库写测试价格标记；结合 marks_add_by_price 的错表问题，还可能误删同键的时间轴标记。默认导入路径不会执行这条写入。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 直接运行模块时不得产生业务记录；import smoke test 不创建/修改生产 schema；数据库测试仅连接临时路径。 修改前测试应失败。
2. **实施修复：** 删除全部可执行测试写入
3. **实施修复：** 数据库 smoke test 移到临时 SQLite pytest fixture。
4. **实施修复：** 模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。
5. **执行回归验证：** 直接运行模块时不得产生业务记录；import smoke test 不创建/修改生产 schema；数据库测试仅连接临时路径。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 删除全部可执行测试写入；数据库 smoke test 移到临时 SQLite pytest fixture。模块导入也应避免自动 create_all，改由显式应用初始化或迁移命令。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查模块级初始化与文件末尾 main guard 的控制流，并定位唯一未注释写库调用。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 实际污染目标取决于运行时 config.py；测试中未执行该写库语句。

**最新证据：**

- [`src/tradingview_zy/db.py（1443-L1608）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L1443-L1608)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-02"></a>

### MX-02 · ZB 被配置文档声明支持，但工厂无法选择

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** config.py.demo 仍声明数字货币支持 binance / zb / db；MarketRegistry/工厂只有 binance 与 db，zb 配置仍不可选择。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 从配置与文档删除 zb，或重新实现并注册；支持矩阵必须由注册表自动生成。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/config.py.demo) — 仍宣称支持 zb
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — Currency provider 不含 zb

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-02 · ZB 被配置文档声明支持，但工厂无法选择

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Exchange Factory
- **来源：** 外部审查新增
- **标签：** 需求、配置、外部 O-06

#### 当前状态与最新验证

**最新 master 验证结论：** 最新工厂只新增 CTP 拒绝分支；ZB 仍被配置注释宣称支持，但工厂无 zb 分支。

**剩余工作：** 明确二选一：恢复工厂、依赖与 contract tests；或删除 ZB 说明、凭据项和适配器。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** 配置模板允许 EXCHANGE_CURRENCY='zb'，get_exchange 没有对应分支，遗留 exchange_zb.py 又不在工厂注册。

**正确行为应该是什么：** 明确二选一：恢复工厂、依赖与 contract tests；或删除 ZB 说明、凭据项和适配器。

**直观例子：** 直观地看，这项问题意味着：按受支持配置部署会在启动/首次请求失败；

#### 2. 影响分析

按受支持配置部署会在启动/首次请求失败；孤立适配器继续积累未维护代码。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 遍历配置模板列出的所有 provider，工厂必须成功返回或在启动时给出 Unsupported。 修改前测试应失败。
2. **实施修复：** 明确二选一：恢复工厂、依赖与 contract tests
3. **实施修复：** 或删除 ZB 说明、凭据项和适配器。
4. **执行回归验证：** 遍历配置模板列出的所有 provider，工厂必须成功返回或在启动时给出 Unsupported。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 明确二选一：恢复工厂、依赖与 contract tests；或删除 ZB 说明、凭据项和适配器。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新工厂只新增 CTP 拒绝分支；ZB 仍被配置注释宣称支持，但工厂无 zb 分支。

**原报告采用的排查方法：** 逐个对照 config.py.demo 支持声明、Market 分支、else 错误和返回缓存，验证合法/非法配置的实际异常。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/config.py.demo' 'src/tradingview_zy/exchange/__init__.py' 'src/tradingview_zy/exchange/exchange_zb.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 完整固定提交已静态核对；若需量化实际影响，仍应增加针对该路径的动态回归测试。

**最新证据：**

- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo) — 配置说明
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py) — 工厂
- [`src/tradingview_zy/exchange/exchange_zb.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_zb.py) — 孤立实现
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-04"></a>

### MX-04 · ExchangeDB.now_trading 返回 None，Python 与前端调用方对三态结果解释不一致

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** ExchangeDB.now_trading() 仍为 pass，返回 None；Python 与前端对 None/null 的解释仍不统一。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 返回严格 bool 或显式 UnsupportedCapabilityError；调用方不得把 None 当作交易中。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_db.py) — now_trading pass

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-04 · ExchangeDB.now_trading 返回 None，Python 与前端调用方对三态结果解释不一致

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** ExchangeDB / Scheduling
- **来源：** 外部审查新增
- **标签：** 正确性、调度、外部 O-09

#### 当前状态与最新验证

**最新 master 验证结论：** 策略加载改动没有修改 ExchangeDB.now_trading() 的 pass，也没有统一 Python/JavaScript 对 None/null 的解释。

**剩余工作：** now_trading 必须返回显式 bool 或结构化 Open/Closed/Unknown；DB 数据源应配置对应市场日历。所有调用方统一处理 Unknown，不能分别使用 `is False` 与 `!== true`。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** ExchangeDB.now_trading() 只有 pass，实际返回 None。AlertTasks 和 `/tv/history` 使用 `is False` 判断闭市，None 不满足条件，因此继续执行；`/ticks` 则把 None 原样作为 JSON null 返回，zixuan.js 检查 `now_trading !== true` 后停止涨跌幅轮询。

**正确行为应该是什么：** now_trading 必须返回显式 bool 或结构化 Open/Closed/Unknown；DB 数据源应配置对应市场日历。所有调用方统一处理 Unknown，不能分别使用 `is False` 与 `!== true`。

**直观例子：** 直观地看，这项问题意味着：同一数据源在监控/历史接口中被当成可继续运行，在前端 tick 轮询中又被当成不可继续，形成相反行为。

#### 2. 影响分析

同一数据源在监控/历史接口中被当成可继续运行，在前端 tick 轮询中又被当成不可继续，形成相反行为。闭市时可能继续跑监控，而自选涨跌幅更新会提前停止；不能概括为所有路径都按 24x7。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 对 True/False/Unknown 参数化测试 AlertTasks、tv_history、ticks 和前端轮询；Unknown 应按明确策略处理并可观测。 修改前测试应失败。
2. **实施修复：** now_trading 必须返回显式 bool 或结构化 Open/Closed/Unknown
3. **实施修复：** DB 数据源应配置对应市场日历。
4. **实施修复：** 所有调用方统一处理 Unknown，不能分别使用 `is False` 与 `!== true`。
5. **执行回归验证：** 对 True/False/Unknown 参数化测试 AlertTasks、tv_history、ticks 和前端轮询；Unknown 应按明确策略处理并可观测。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** now_trading 必须返回显式 bool 或结构化 Open/Closed/Unknown；DB 数据源应配置对应市场日历。所有调用方统一处理 Unknown，不能分别使用 `is False` 与 `!== true`。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 策略加载改动没有修改 ExchangeDB.now_trading() 的 pass，也没有统一 Python/JavaScript 对 None/null 的解释。

**原报告采用的排查方法：** 沿 ExchangeDB.now_trading 返回值进入 AlertTasks、tv_history、ticks JSON 和 zixuan.js，分别计算 `None is False` 与 `null !== true`。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_db.py' 'web/tradingview_zy_chart/cl_app/alert_tasks.py' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未在浏览器中运行；分支结果由语言语义可直接推出。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_db.py（277-L300）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_db.py#L277-L300)
- [`web/tradingview_zy_chart/cl_app/alert_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/alert_tasks.py)
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`web/tradingview_zy_chart/cl_app/static/js/zixuan.js（82-L85）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/static/js/zixuan.js#L82-L85)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-05"></a>

### MX-05 · 自选涨跌幅轮询把函数返回值交给 setInterval

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** index.html 仍把 ZiXuan.stocks_update_rate() 的返回值传给 setInterval，函数立即执行而定时器没有回调。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 传函数引用/箭头函数，并用前端定时器测试验证周期调用。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/templates/index.html`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/templates/index.html) — 错误 setInterval 调用

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-05 · 自选涨跌幅轮询把函数返回值交给 setInterval

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Frontend
- **来源：** 外部审查新增
- **标签：** 前端、正确性、外部 O-18

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/templates/index.html、web/tradingview_zy_chart/cl_app/templates/index.html）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 传函数引用或箭头函数；封装 interval 生命周期并避免重复定时器。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 模板两次写 `setInterval(ZiXuan.stocks_update_rate(), 30000)`，函数只立即执行一次。

**正确行为应该是什么：** 传函数引用或箭头函数；封装 interval 生命周期并避免重复定时器。

**直观例子：** setInterval(fn(), 30000) 会先执行 fn，再把返回值交给定时器；正确方式是传函数本身。

#### 2. 影响分析

行情涨跌幅不会按 30 秒刷新，用户看到陈旧数据。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 用 fake timers 断言 30/60 秒调用次数和关闭面板后的清理。 修改前测试应失败。
2. **实施修复：** 传函数引用或箭头函数
3. **实施修复：** 封装 interval 生命周期并避免重复定时器。
4. **执行回归验证：** 用 fake timers 断言 30/60 秒调用次数和关闭面板后的清理。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 传函数引用或箭头函数；封装 interval 生命周期并避免重复定时器。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/templates/index.html、web/tradingview_zy_chart/cl_app/templates/index.html）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 JavaScript 作用域、事件初始化顺序、定时器回调、Layui 字段配置、DOM 拼接和函数实参与签名；需要时用 node 语法检查和浏览器契约推演。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/templates/index.html' 'web/tradingview_zy_chart/cl_app/templates/index.html'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/templates/index.html（491-L505）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/index.html#L491-L505) — 定时器
- [`web/tradingview_zy_chart/cl_app/templates/index.html（650-L659）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/index.html#L650-L659) — 初始化
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-17"></a>

### MX-17 · TDX 节点选优在缓存缺失或重置时串行探测全部候选，缺少总体 deadline

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** TDX 选优和各 TDX 构造器没有修改；Web 文件的安全变更不影响串行探测和总体 deadline。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 并发有界探测；设置全局 deadline、最小成功数和 TTL 健康缓存；后台刷新而非阻塞请求。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/tools/tdx_best_ip.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/tools/tdx_best_ip.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_hk.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_futures.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_futures.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-17 · TDX 节点选优在缓存缺失或重置时串行探测全部候选，缺少总体 deadline

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** TDX / Performance
- **来源：** 外部审查新增
- **标签：** 性能、可靠性、外部 O-28

#### 当前状态与最新验证

**最新 master 验证结论：** TDX 选优和各 TDX 构造器没有修改；Web 文件的安全变更不影响串行探测和总体 deadline。

**剩余工作：** 并发有界探测；设置全局 deadline、最小成功数和 TTL 健康缓存；后台刷新而非阻塞请求。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** select_best_ip() 通过列表推导顺序调用每个候选的 ping；A 股使用 `tdx_connect_ip`，HK/期货/FX/NY/US 共用 `tdxex_connect_ip`。缓存缺失、失效重置或首次冷启动时会串行扫描对应候选集；缓存命中时不会扫描。

**正确行为应该是什么：** 并发有界探测；设置全局 deadline、最小成功数和 TTL 健康缓存；后台刷新而非阻塞请求。

**直观例子：** 缓存读写键、原子写入和损坏恢复必须一致，否则缓存反而制造重复请求或数据缺口。

#### 2. 影响分析

冷启动或故障重选延迟随候选和单节点超时线性增长，并发生在 Web eager 初始化/请求路径；外部报告的固定 38 秒未复现，且不能乘以每个 ExHq 适配器。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 模拟 40 个候选、超时和半失效节点；确认冷启动只进行两个共享扫描、总耗时受 deadline 限制、缓存命中零扫描。 修改前测试应失败。
2. **实施修复：** 并发有界探测
3. **实施修复：** 设置全局 deadline、最小成功数和 TTL 健康缓存
4. **实施修复：** 后台刷新而非阻塞请求。
5. **执行回归验证：** 模拟 40 个候选、超时和半失效节点；确认冷启动只进行两个共享扫描、总耗时受 deadline 限制、缓存命中零扫描。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 并发有界探测；设置全局 deadline、最小成功数和 TTL 健康缓存；后台刷新而非阻塞请求。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** TDX 选优和各 TDX 构造器没有修改；Web 文件的安全变更不影响串行探测和总体 deadline。

**原报告采用的排查方法：** 检查 tdx_best_ip.select_best_ip 的迭代方式，并沿六个 TDX 构造器核对 cache_get/cache_set 键、reset 调用和 Web eager 初始化顺序。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/tools/tdx_best_ip.py' 'src/tradingview_zy/exchange/exchange_tdx.py' 'src/tradingview_zy/exchange/exchange_tdx_hk.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未对真实候选网络测速；延迟规模取决于网络、候选数和 pytdx 行为。

**最新证据：**

- [`src/tradingview_zy/tools/tdx_best_ip.py（145-L207）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/tools/tdx_best_ip.py#L145-L207)
- [`src/tradingview_zy/exchange/exchange_tdx.py（32-L63）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx.py#L32-L63)
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py（30-L78）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_hk.py#L30-L78)
- [`src/tradingview_zy/exchange/exchange_tdx_futures.py（32-L89）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_futures.py#L32-L89)
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-08"></a>

### NX-08 · POSITION.get_close_profit 会修改调用方传入列表

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/base.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 复制输入或使用不可变 tuple/set。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/backtesting/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/base.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-08 · POSITION.get_close_profit 会修改调用方传入列表

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Backtesting Model
- **来源：** 本次补充排查新发现
- **标签：** 副作用

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/base.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 复制输入或使用不可变 tuple/set。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分属于回测引擎。回测会按照历史 K 线模拟下单、持仓、现金和绩效指标；任何日期、数量、成本、手续费或年化公式错误都会沿后续计算持续放大。

**当前/原始错误行为：** `__close_records_by_uids` 在参数列表中原地 append('clear')。

**正确行为应该是什么：** 复制输入或使用不可变 tuple/set。

**直观例子：** 直观地看，这项问题意味着：同一个列表复用时内容被静默改变，缓存键/后续过滤出现意外行为。

#### 2. 影响分析

同一个列表复用时内容被静默改变，缓存键/后续过滤出现意外行为。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 调用前后原列表保持相等。 修改前测试应失败。
2. **实施修复：** 复制输入或使用不可变 tuple/set。
3. **执行回归验证：** 调用前后原列表保持相等。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 复制输入或使用不可变 tuple/set。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/base.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查对象方法对调用方传入容器的原地修改，并用同一列表重复调用观察副作用。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/base.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 公式和状态更新位置可静态/最小算例确认；未用真实历史数据做大样本回归，影响规模需黄金基准测试。

**最新证据：**

- [`src/tradingview_zy/backtesting/base.py（70-L87）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/base.py#L70-L87) — 原地 append
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-03"></a>

### NX-03 · 飞书配置读取会原地修改全局默认字典

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/utils.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 返回 `dict(source)` 副本，使用不可变配置对象。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/utils.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/utils.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-03 · 飞书配置读取会原地修改全局默认字典

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 当前 PR 没有与该条原始根因一一对应的实现和测试证明。
- **仍有什么问题 / 下一步：** 按原始证据路径复现并补专项测试；在此之前不标记已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Configuration / Messaging
- **来源：** 本次补充排查新发现
- **标签：** 状态管理

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/utils.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 返回 `dict(source)` 副本，使用不可变配置对象。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** `keys = config.FEISHU_KEYS['default']` 或市场子字典后直接写 `keys['user_id']`，返回的是原对象。

**正确行为应该是什么：** 返回 `dict(source)` 副本，使用不可变配置对象。

**直观例子：** 直观地看，这项问题意味着：一次调用会污染全局配置；

#### 2. 影响分析

一次调用会污染全局配置；测试/并发/市场切换可能互相泄露 user_id 或后续修改。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 连续不同市场调用后原 FEISHU_KEYS 必须不变。 修改前测试应失败。
2. **实施修复：** 返回 `dict(source)` 副本，使用不可变配置对象。
3. **执行回归验证：** 连续不同市场调用后原 FEISHU_KEYS 必须不变。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 返回 `dict(source)` 副本，使用不可变配置对象。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/utils.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 比较消息配置读取与 config.py.demo，检查分支可达性、全局字典原地修改和全仓调用图。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/utils.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 配置和数据流可静态确认；实际暴露范围取决于部署访问控制、日志和外部服务。

**最新证据：**

- [`src/tradingview_zy/utils.py（50-L69）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/utils.py#L50-L69) — 共享字典写入
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-22"></a>

### NX-22 · db.py import 时全局关闭所有 warnings

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** src/tradingview_zy/db.py 模块级仍执行 warnings.filterwarnings("ignore")，会全局吞掉与数据库无关的警告。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 删除全局 ignore；仅在已知第三方调用点使用精确 category/module/message 过滤。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 第 38 行全局 warnings ignore

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-22 · db.py import 时全局关闭所有 warnings

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Database / Diagnostics
- **来源：** 本次补充排查新发现
- **标签：** 可观测性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 删除全局过滤；对已知无害警告局部 context+精确 category/message。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** 模块顶层 `warnings.filterwarnings('ignore')` 影响整个进程，不限类别/来源。

**正确行为应该是什么：** 删除全局过滤；对已知无害警告局部 context+精确 category/message。

**直观例子：** 直观地看，这项问题意味着：SQLAlchemy、pandas、弃用和数据转换警告被静默吞掉，迁移问题更难发现。

#### 2. 影响分析

SQLAlchemy、pandas、弃用和数据转换警告被静默吞掉，迁移问题更难发现。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 测试中将 warnings 设为 error，关键路径无意外警告。 修改前测试应失败。
2. **实施修复：** 删除全局过滤
3. **实施修复：** 对已知无害警告局部 context+精确 category/message。
4. **执行回归验证：** 测试中将 warnings 设为 error，关键路径无意外警告。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 删除全局过滤；对已知无害警告局部 context+精确 category/message。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查模块级 warnings 配置的作用域和导入时机，确认是否影响进程内其他库。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/db.py（1-L34）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L1-L34) — 全局 warning filter
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-21"></a>

### NX-21 · MySQL DSN 直接字符串插值，特殊字符密码会破坏 URL

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-21 · MySQL DSN 直接字符串插值，特殊字符密码会破坏 URL

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Database Configuration
- **来源：** 本次补充排查新发现
- **标签：** 配置、安全

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** 用户名/密码/主机直接拼进 `mysql+pymysql://...`，没有 URL 编码。

**正确行为应该是什么：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。

**直观例子：** 数据库密码含 @ 或 : 时，直接拼进 URL 会被当成分隔符；应让 URL 构造器负责转义。

#### 2. 影响分析

密码含 @、:、/、% 等字符时连接解析错误，日志还可能暴露拼接后的 DSN。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 特殊字符密码连接构造测试，异常日志不得含秘密。 修改前测试应失败。
2. **实施修复：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。
3. **执行回归验证：** 特殊字符密码连接构造测试，异常日志不得含秘密。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用 `sqlalchemy.engine.URL.create()` 和 secret 类型。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 SQLAlchemy 连接 URL 的字符串构造与特殊字符解析，和 URL.create/转义的正确方式比较。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/db.py（260-L289）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L260-L289) — DSN 构造
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-23"></a>

### NX-23 · ExchangeDB.all_stocks() 永远为空，与“db 可作为 Web 数据源”冲突

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** ExchangeDB.all_stocks() 仍固定返回 []，与 db 可作为 Web provider 及新增 SECURITY_MASTER 能力声明冲突。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 实现证券主数据表/查询，或撤销 security_master 能力并让依赖该能力的页面明确不可用。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_db.py) — all_stocks 固定空
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — DB provider 过报 security_master

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-23 · ExchangeDB.all_stocks() 永远为空，与“db 可作为 Web 数据源”冲突

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** ExchangeDB
- **来源：** 本次补充排查新发现
- **标签：** 需求、正确性

#### 当前状态与最新验证

**最新 master 验证结论：** xuangu_tasks.py 只改为注册表加载策略；ExchangeDB.all_stocks() 仍返回空列表。

**剩余工作：** 从数据库表/独立 instruments 表维护证券目录，能力声明区分 catalog 与 klines。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** DB provider 的 K 线读取可用，但 `all_stocks()` 固定返回空列表；Web 搜索、导入自选和选股 all universe 依赖该方法。

**正确行为应该是什么：** 从数据库表/独立 instruments 表维护证券目录，能力声明区分 catalog 与 klines。

**直观例子：** 直观地看，这项问题意味着：切换 EXCHANGE_*=db 后图表已知代码可能可用，但证券搜索/导入/全市场任务为空。

#### 2. 影响分析

切换 EXCHANGE_*=db 后图表已知代码可能可用，但证券搜索/导入/全市场任务为空。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** db provider 下搜索、导入和选股 universe contract tests。 修改前测试应失败。
2. **实施修复：** 从数据库表/独立 instruments 表维护证券目录，能力声明区分 catalog 与 klines。
3. **执行回归验证：** db provider 下搜索、导入和选股 universe contract tests。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 从数据库表/独立 instruments 表维护证券目录，能力声明区分 catalog 与 klines。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** xuangu_tasks.py 只改为注册表加载策略；ExchangeDB.all_stocks() 仍返回空列表。

**原报告采用的排查方法：** 沿 ExchangeDB 的 support_frequencys、klines、all_stocks 和 DB 动态表路由检查 key/value 语义与市场覆盖。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_db.py' 'web/tradingview_zy_chart/cl_app/xuangu_tasks.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_db.py（279-L305）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_db.py#L279-L305) — all_stocks 空实现
- [`web/tradingview_zy_chart/cl_app/xuangu_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/xuangu_tasks.py) — 选股依赖 all_stocks
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-16"></a>

### NX-16 · /ticks 可提交无上限代码数组并同步扇出到数据源

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** Web 安全改动没有为 /ticks 增加代码数量、去重、长度或 provider 批量上限。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 限制 symbol 数、去重、请求超时和速率；批量上限按 provider 能力。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-16 · /ticks 可提交无上限代码数组并同步扇出到数据源

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Web Security / Availability
- **来源：** 本次补充排查新发现
- **标签：** 可用性、CWE-400

#### 当前状态与最新验证

**最新 master 验证结论：** Web 安全改动没有为 /ticks 增加代码数量、去重、长度或 provider 批量上限。

**剩余工作：** 限制 symbol 数、去重、请求超时和速率；批量上限按 provider 能力。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 请求 JSON 直接传给 `ex.ticks(codes)`，没有数量、长度、重复和市场合法性限制。

**正确行为应该是什么：** 限制 symbol 数、去重、请求超时和速率；批量上限按 provider 能力。

**直观例子：** 直观地看，这项问题意味着：登录用户或 CSRF 攻击可触发大规模外部请求，阻塞 worker、触发限流或费用。

#### 2. 影响分析

登录用户或 CSRF 攻击可触发大规模外部请求，阻塞 worker、触发限流或费用。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 超限列表返回 413/422，不调用 provider。 修改前测试应失败。
2. **实施修复：** 限制 symbol 数、去重、请求超时和速率
3. **实施修复：** 批量上限按 provider 能力。
4. **执行回归验证：** 超限列表返回 413/422，不调用 provider。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 限制 symbol 数、去重、请求超时和速率；批量上限按 provider 能力。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** Web 安全改动没有为 /ticks 增加代码数量、去重、长度或 provider 批量上限。

**原报告采用的排查方法：** 从请求体规模和循环扇出追踪同步数据源调用，检查 Flask/代理层是否存在代码内上限、超时、批次或拒绝策略。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py) — ticks 路由
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-14"></a>

### NX-14 · 读取不存在的 chart/template 会直接解引用 None

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 图表/模板读取路由没有补 None/404 处理，相关 ORM 查询未变。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** None 返回 404/规范 UDF 错误；校验 ID 类型。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-14 · 读取不存在的 chart/template 会直接解引用 None

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Web Storage
- **来源：** 本次补充排查新发现
- **标签：** 可靠性

#### 当前状态与最新验证

**最新 master 验证结论：** 图表/模板读取路由没有补 None/404 处理，相关 ORM 查询未变。

**剩余工作：** None 返回 404/规范 UDF 错误；校验 ID 类型。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** `tv_chart_get`/`tv_chart_get_by_name` 返回 None 时，路由直接访问 `.content/.name`。

**正确行为应该是什么：** None 返回 404/规范 UDF 错误；校验 ID 类型。

**直观例子：** 直观地看，这项问题意味着：任意不存在 ID/名称造成 500，且可用于枚举错误行为。

#### 2. 影响分析

任意不存在 ID/名称造成 500，且可用于枚举错误行为。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 不存在和越权资源均返回稳定 404。 修改前测试应失败。
2. **实施修复：** None 返回 404/规范 UDF 错误
3. **实施修复：** 校验 ID 类型。
4. **执行回归验证：** 不存在和越权资源均返回稳定 404。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** None 返回 404/规范 UDF 错误；校验 ID 类型。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 图表/模板读取路由没有补 None/404 处理，相关 ORM 查询未变。

**原报告采用的排查方法：** 沿 client/user/resource ID 从请求进入 ORM 查询、更新和删除，检查认证主体绑定、None 处理、错误返回和所有权约束。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py) — chart/template GET
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-15"></a>

### NX-15 · 绘图保存异常被吞掉并始终返回 status ok

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 绘图保存的宽泛异常捕获和无条件成功返回未被本轮修改。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 返回 4xx/5xx 与 request_id；仅幂等成功返回 ok。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-15 · 绘图保存异常被吞掉并始终返回 status ok

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Web Storage
- **来源：** 本次补充排查新发现
- **标签：** 可靠性、数据丢失

#### 当前状态与最新验证

**最新 master 验证结论：** 绘图保存的宽泛异常捕获和无条件成功返回未被本轮修改。

**剩余工作：** 返回 4xx/5xx 与 request_id；仅幂等成功返回 ok。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** drawings POST 捕获所有异常只打印 traceback，随后无条件返回成功。

**正确行为应该是什么：** 返回 4xx/5xx 与 request_id；仅幂等成功返回 ok。

**直观例子：** 直观地看，这项问题意味着：前端认为已保存，刷新后绘图丢失，无法重试或告警。

#### 2. 影响分析

前端认为已保存，刷新后绘图丢失，无法重试或告警。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 数据库故障注入时前端收到失败并保留本地状态。 修改前测试应失败。
2. **实施修复：** 返回 4xx/5xx 与 request_id
3. **实施修复：** 仅幂等成功返回 ok。
4. **执行回归验证：** 数据库故障注入时前端收到失败并保留本地状态。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 返回 4xx/5xx 与 request_id；仅幂等成功返回 ok。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 绘图保存的宽泛异常捕获和无条件成功返回未被本轮修改。

**原报告采用的排查方法：** 沿 client/user/resource ID 从请求进入 ORM 查询、更新和删除，检查认证主体绑定、None 处理、错误返回和所有权约束。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py) — 异常吞噬
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-05"></a>

### RV-05 · 多进程回测允许省略 save_file，但 run_by_code 无条件对 None 调 split()

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 年化修复没有触及多进程 save_file 契约；可选配置与 worker 无条件 split() 的冲突仍在。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 主进程提前要求 save_file，或自动创建安全临时目录；不要在 worker 内才发现。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/backtesting/backtest.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/backtest.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-05 · 多进程回测允许省略 save_file，但 run_by_code 无条件对 None 调 split()

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Backtesting / Process
- **来源：** 本次仓库复验新增
- **工作量：** S
- **标签：** 正确性、配置契约

#### 当前状态与最新验证

**最新 master 验证结论：** 年化修复没有触及多进程 save_file 契约；可选配置与 worker 无条件 split() 的冲突仍在。

**剩余工作：** 主进程提前要求 save_file，或自动创建安全临时目录；不要在 worker 内才发现。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分属于回测引擎。回测会按照历史 K 线模拟下单、持仓、现金和绩效指标；任何日期、数量、成本、手续费或年化公式错误都会沿后续计算持续放大。

**当前/原始错误行为：** 构造用 config.get("save_file") 使 save_file 可选；run_process 没有校验，worker 的 run_by_code 首句对 self.save_file.split()。未提供时必然 AttributeError。

**正确行为应该是什么：** 主进程提前要求 save_file，或自动创建安全临时目录；不要在 worker 内才发现。

**直观例子：** 配置表面允许不填保存路径，但子进程一启动就对空值调用字符串方法，错误被推迟到 worker 内。

#### 2. 影响分析

合法配置对象切换多进程后立即失败，且错误在 worker 路径增加排查成本。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 无 save_file 得明确配置错误或自动路径；有路径时文件名唯一可写并可清理。 修改前测试应失败。
2. **实施修复：** 主进程提前要求 save_file，或自动创建安全临时目录
3. **实施修复：** 不要在 worker 内才发现。
4. **执行回归验证：** 无 save_file 得明确配置错误或自动路径；有路径时文件名唯一可写并可清理。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 主进程提前要求 save_file，或自动创建安全临时目录；不要在 worker 内才发现。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 年化修复没有触及多进程 save_file 契约；可选配置与 worker 无条件 split() 的冲突仍在。

**原报告采用的排查方法：** 从可选配置进入多进程 worker、文件名生成、保存和汇总路径，检查 None/空路径和子进程错误传播。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/backtest.py' 'src/tradingview_zy/backtesting/backtest.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 公式和状态更新位置可静态/最小算例确认；未用真实历史数据做大样本回归，影响规模需黄金基准测试。

**最新证据：**

- [`src/tradingview_zy/backtesting/backtest.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/backtest.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-04"></a>

### RV-04 · 盈亏为 0 的平仓被计入失败交易

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** _record_closed_position() 仍仅以 profit > 0 判胜，其余（包括 0）全部计入 loss。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 定义 breakeven 计数或至少 0 不计 loss；补零收益和手续费后零收益测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/backtesting/backtest_trader.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/backtest_trader.py) — 零收益落入 loss 分支

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-04 · 盈亏为 0 的平仓被计入失败交易

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Backtesting Metrics
- **来源：** 本次仓库复验新增
- **工作量：** S
- **标签：** 正确性、绩效统计

#### 当前状态与最新验证

**最新 master 验证结论：** 年化修复没有触及 _record_closed_position() 的盈亏分类；0 盈亏仍进入 loss 分支。

**剩余工作：** 使用正/负/epsilon 内三分法并增加 flat_num，或明确产品定义。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分属于回测引擎。回测会按照历史 K 线模拟下单、持仓、现金和绩效指标；任何日期、数量、成本、手续费或年化公式错误都会沿后续计算持续放大。

**当前/原始错误行为：** _record_closed_position() 只判断 profit>0，其他全部进入 loss；profit==0 会增加 loss_num。

**正确行为应该是什么：** 使用正/负/epsilon 内三分法并增加 flat_num，或明确产品定义。

**直观例子：** 不赚不亏的交易应是持平；旧代码只有赢/输两个分支，0 盈亏被计入失败。

#### 2. 影响分析

胜率、失败次数、平均亏损和盈亏比语义偏差，保本交易多时影响参数优化。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 关闭 +1、0、-1 三笔，win/loss/flat 各增加一次；覆盖浮点 epsilon。 修改前测试应失败。
2. **实施修复：** 使用正/负/epsilon 内三分法并增加 flat_num，或明确产品定义。
3. **执行回归验证：** 关闭 +1、0、-1 三笔，win/loss/flat 各增加一次；覆盖浮点 epsilon。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用正/负/epsilon 内三分法并增加 flat_num，或明确产品定义。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 年化修复没有触及 _record_closed_position() 的盈亏分类；0 盈亏仍进入 loss 分支。

**原报告采用的排查方法：** 把当前绩效公式代入已知收益序列和零值边界，核对百分比/小数单位、年化、无风险收益和除零表现。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/backtest_trader.py' 'src/tradingview_zy/backtesting/backtest.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 公式和状态更新位置可静态/最小算例确认；未用真实历史数据做大样本回归，影响规模需黄金基准测试。

**最新证据：**

- [`src/tradingview_zy/backtesting/backtest_trader.py（206-L225）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/backtest_trader.py#L206-L225)
- [`src/tradingview_zy/backtesting/backtest.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/backtest.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-01"></a>

### RV-01 · 添加“置顶”自选股时批量位移遗漏 market，跨市场同名组会被一起改序

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/db.py、src/tradingview_zy/db.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 给 UPDATE 加 market 过滤；移动+插入放同一事务；增加 (market,zx_group,stock_code) 唯一约束并规范化 position。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-01 · 添加“置顶”自选股时批量位移遗漏 market，跨市场同名组会被一起改序

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Database / Watchlist
- **来源：** 本次仓库复验新增
- **工作量：** S
- **标签：** 正确性、数据完整性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py、src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 给 UPDATE 加 market 过滤；移动+插入放同一事务；增加 (market,zx_group,stock_code) 唯一约束并规范化 position。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** zx_add_group_stock() 在 location="top" 时，对已有行执行 position+1 的 UPDATE 只过滤 zx_group，没有过滤 market。各市场默认都可能有同名“我的关注”组，因此某市场置顶新增会同时移动其他市场排序。

**正确行为应该是什么：** 给 UPDATE 加 market 过滤；移动+插入放同一事务；增加 (market,zx_group,stock_code) 唯一约束并规范化 position。

**直观例子：** 两个市场都可能有“我的关注”组；UPDATE 只按组名匹配时，在 A 股置顶会连港股同名组排序一起改。

#### 2. 影响分析

跨市场自选排序被无提示修改；重复执行导致其他市场 position 漂移和不可预测顺序。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** A/HK 创建同名组，各放标的；向 A 组 top 添加，HK position 必须完全不变，事务失败不留半状态。 修改前测试应失败。
2. **实施修复：** 给 UPDATE 加 market 过滤
3. **实施修复：** 移动+插入放同一事务
4. **实施修复：** 增加 (market,zx_group,stock_code) 唯一约束并规范化 position。
5. **执行回归验证：** A/HK 创建同名组，各放标的；向 A 组 top 添加，HK position 必须完全不变，事务失败不留半状态。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 给 UPDATE 加 market 过滤；移动+插入放同一事务；增加 (market,zx_group,stock_code) 唯一约束并规范化 position。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/db.py、src/tradingview_zy/db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 比较同一自选 CRUD/排序函数的复合过滤条件，并用两个市场同名组做符号推演。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/db.py' 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/db.py（577-L606）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L577-L606)
- [`src/tradingview_zy/db.py（663-L679）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L663-L679)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-07"></a>

### RV-07 · UDF/search/marks 路由缺少统一参数校验，畸形请求返回 500

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 本轮 Web 改动没有为 UDF/search/marks 路由增加统一参数 schema 和 4xx 错误处理。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间；UDF 返回 s:error/errmsg，普通 API 返回400/422。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-07 · UDF/search/marks 路由缺少统一参数校验，畸形请求返回 500

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Web API Robustness
- **来源：** 本次仓库复验新增
- **工作量：** M
- **标签：** 可靠性、输入校验

#### 当前状态与最新验证

**最新 master 验证结论：** 本轮 Web 改动没有为 UDF/search/marks 路由增加统一参数 schema 和 4xx 错误处理。

**剩余工作：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间；UDF 返回 s:error/errmsg，普通 API 返回400/422。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** /tv/search 对 query.lower、int(limit)、Market(exchange) 直接调用；/tv/history 对 symbol 直接 split 索引；marks 直接 int 和 resolution_maps 索引。缺失/错误格式会抛异常而非规范错误。

**正确行为应该是什么：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间；UDF 返回 s:error/errmsg，普通 API 返回400/422。

**直观例子：** 直观地看，这项问题意味着：错误或恶意请求制造 500、堆栈日志和重试放大，可能触发不必要适配器初始化。

#### 2. 影响分析

错误或恶意请求制造 500、堆栈日志和重试放大，可能触发不必要适配器初始化。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 缺失/空/超长 symbol、未知市场/周期、非数字参数和多冒号 code 的 fuzz；不得500。 修改前测试应失败。
2. **实施修复：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间
3. **实施修复：** UDF 返回 s:error/errmsg，普通 API 返回400/422。
4. **执行回归验证：** 缺失/空/超长 symbol、未知市场/周期、非数字参数和多冒号 code 的 fuzz；不得500。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 共享 parser/schema，验证 symbol、市场、周期、limit 和时间；UDF 返回 s:error/errmsg，普通 API 返回400/422。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 本轮 Web 改动没有为 UDF/search/marks 路由增加统一参数 schema 和 4xx 错误处理。

**原报告采用的排查方法：** 枚举缺失、空值、非法枚举、非数字和畸形 symbol/query 参数，沿第一处解析、split、索引或类型转换推导响应，并检查统一错误处理。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：中 · 可信度：高

</details>

## 严重程度：中 · 可信度：高

</details>

## 严重程度：中 · 可信度：高

<a id="ME-11"></a>

### ME-11 · Baostock 股票列表固定在 2022-04-18，分钟时间按序号重建

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_baostock.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 股票列表按当前交易日/可用最新日刷新并缓存版本；使用数据源原始时间；重试采用有界迭代与退避。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_baostock.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_baostock.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-11 · Baostock 股票列表固定在 2022-04-18，分钟时间按序号重建

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Baostock
- **来源：** 双方
- **工作量：** M
- **标签：** 正确性、可靠性、外部 O-27

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_baostock.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 股票列表按当前交易日/可用最新日刷新并缓存版本；使用数据源原始时间；重试采用有界迭代与退避。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 全市场列表查询日期硬编码为 2022-04-18；分钟 K 线时间并非完全信任数据源字段，而是按行序和交易时段推算。递归重登录路径缺少严格上限。

**正确行为应该是什么：** 股票列表按当前交易日/可用最新日刷新并缓存版本；使用数据源原始时间；重试采用有界迭代与退避。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

新上市/退市标的长期不准确；缺失或乱序 bar 会让后续所有时间戳错位；网络故障可能形成递归重试。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 新上市样例、缺 bar、午休、停牌、乱序与登录持续失败测试。 修改前测试应失败。
2. **实施修复：** 股票列表按当前交易日/可用最新日刷新并缓存版本
3. **实施修复：** 使用数据源原始时间
4. **实施修复：** 重试采用有界迭代与退避。
5. **执行回归验证：** 新上市样例、缺 bar、午休、停牌、乱序与登录持续失败测试。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 股票列表按当前交易日/可用最新日刷新并缓存版本；使用数据源原始时间；重试采用有界迭代与退避。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_baostock.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查股票列表查询日期、分钟 bar 时间来源、登录重试和对缺 bar/乱序的处理。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_baostock.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_baostock.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_baostock.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="HI-17"></a>

### HI-17 · 行情同步脚本以顶层程序方式执行，缺少可恢复 checkpoint、统一 deadline 和可审计批次状态

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（script/crontab/reboot_sync_a_klines.py、script/crontab/reboot_sync_us_klines.py、script/crontab/reboot_sync_currency_klines.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 重构为显式 CLI/main；universe 外部化；每个 symbol/frequency 写 checkpoint 和失败原因；所有外部调用有 deadline/取消；以幂等 upsert 和批次状态支持断点续跑。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`script/crontab/reboot_sync_a_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/script/crontab/reboot_sync_a_klines.py) — 当前实现路径
- [`script/crontab/reboot_sync_us_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/script/crontab/reboot_sync_us_klines.py) — 当前实现路径
- [`script/crontab/reboot_sync_currency_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/script/crontab/reboot_sync_currency_klines.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-17 · 行情同步脚本以顶层程序方式执行，缺少可恢复 checkpoint、统一 deadline 和可审计批次状态

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 当前 PR 没有重构批量同步脚本；硬编码 universe、导入副作用、checkpoint、总体 deadline 和 SIGTERM 恢复仍缺少完整实现。
- **仍有什么问题 / 下一步：** 将脚本改为显式 CLI，配置化 universe，增加 checkpoint、失败清单、总体超时和中断恢复测试。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Scripts
- **来源：** 双方
- **工作量：** L
- **标签：** 可靠性、需求、规范、外部 O-33

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（script/crontab/reboot_sync_a_klines.py、script/crontab/reboot_sync_us_klines.py、script/crontab/reboot_sync_currency_klines.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 重构为显式 CLI/main；universe 外部化；每个 symbol/frequency 写 checkpoint 和失败原因；所有外部调用有 deadline/取消；以幂等 upsert 和批次状态支持断点续跑。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 多份 script/crontab 文件在模块顶层创建数据源、发起网络请求并进入长循环，没有 main() 边界；A 股/美股脚本还内置大规模标的列表。它们作为直接执行脚本时功能可达，但缺少统一批次 ID、checkpoint、失败清单、整体 deadline 和中断恢复。

**正确行为应该是什么：** 重构为显式 CLI/main；universe 外部化；每个 symbol/frequency 写 checkpoint 和失败原因；所有外部调用有 deadline/取消；以幂等 upsert 和批次状态支持断点续跑。

**直观例子：** 直观地看，这项问题意味着：误 import 会触发外部连接；

#### 2. 影响分析

误 import 会触发外部连接；正常直接运行时，进程中断或数据源卡住会留下不可明确判定的部分完成状态，重跑会重复请求和增加数据库压力。该问题不阻断普通 Web 启动。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** import 模块无网络副作用；fake 小型 universe 覆盖 SIGTERM、超时、第 N 个标的失败和重复运行，确认可从 checkpoint 恢复且退出码反映部分失败。 修改前测试应失败。
2. **实施修复：** 重构为显式 CLI/main
3. **实施修复：** universe 外部化
4. **实施修复：** 每个 symbol/frequency 写 checkpoint 和失败原因
5. **实施修复：** 所有外部调用有 deadline/取消
6. **实施修复：** 以幂等 upsert 和批次状态支持断点续跑。
7. **执行回归验证：** import 模块无网络副作用；fake 小型 universe 覆盖 SIGTERM、超时、第 N 个标的失败和重复运行，确认可从 checkpoint 恢复且退出码反映部分失败。 同时运行相邻模块测试。
8. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 重构为显式 CLI/main；universe 外部化；每个 symbol/frequency 写 checkpoint 和失败原因；所有外部调用有 deadline/取消；以幂等 upsert 和批次状态支持断点续跑。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（script/crontab/reboot_sync_a_klines.py、script/crontab/reboot_sync_us_klines.py、script/crontab/reboot_sync_currency_klines.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 对 script/crontab 全部 Python 文件做 AST 顶层语句扫描，检查 main guard、网络/适配器构造、标的来源、循环终止、checkpoint 和退出码。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'script/crontab/reboot_sync_a_klines.py' 'script/crontab/reboot_sync_us_klines.py' 'script/crontab/reboot_sync_currency_klines.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 为避免真实网络和大规模写库，本次没有直接运行同步脚本；顶层副作用和恢复能力缺口可静态确认。

**最新证据：**

- [`script/crontab/reboot_sync_a_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/script/crontab/reboot_sync_a_klines.py)
- [`script/crontab/reboot_sync_us_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/script/crontab/reboot_sync_us_klines.py)
- [`script/crontab/reboot_sync_currency_klines.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/script/crontab/reboot_sync_currency_klines.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-12"></a>

### ME-12 · TDX 适配器存在递归重连、涨跌幅分母错误和硬编码交易时段

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx.py、src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 使用有界重试循环；统一 Tick 计算函数；引入交易所日历服务；对 0/缺失前收价明确返回 unavailable。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tdx.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_hk.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_us.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_fx.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_fx.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-12 · TDX 适配器存在递归重连、涨跌幅分母错误和硬编码交易时段

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** TDX 连接已增加有界重试和并发选优，市场日历也集中化；但全部 TDX 适配器的涨跌幅字段语义、volume/amount 映射仍未逐个以真实样本验证。
- **仍有什么问题 / 下一步：** 为 HK/US/FX/Futures 建立 Tick 映射黄金样本和节假日/DST 合同测试。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** TDX Adapters
- **来源：** 双方
- **工作量：** L
- **标签：** 正确性、可靠性、外部 O-28

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx.py、src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 使用有界重试循环；统一 Tick 计算函数；引入交易所日历服务；对 0/缺失前收价明确返回 unavailable。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** A 股 all_stocks 连接错误可递归调用自身；多个 TDX HK/US/Futures/FX 适配器用当前 price 而不是 pre_close 作为涨跌幅分母；now_trading 多为硬编码小时，不含节假日/夏令时。

**正确行为应该是什么：** 使用有界重试循环；统一 Tick 计算函数；引入交易所日历服务；对 0/缺失前收价明确返回 unavailable。

**直观例子：** 直观地看，这项问题意味着：持续故障可能堆栈溢出；

#### 2. 影响分析

持续故障可能堆栈溢出；UI 涨跌幅错误；节假日或夏令时期间错误判断交易状态并触发任务。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 连接持续失败、pre_close=0、已知涨跌幅、节假日、DST 切换和夜盘测试。 修改前测试应失败。
2. **实施修复：** 使用有界重试循环
3. **实施修复：** 统一 Tick 计算函数
4. **实施修复：** 引入交易所日历服务
5. **实施修复：** 对 0/缺失前收价明确返回 unavailable。
6. **执行回归验证：** 连接持续失败、pre_close=0、已知涨跌幅、节假日、DST 切换和夜盘测试。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用有界重试循环；统一 Tick 计算函数；引入交易所日历服务；对 0/缺失前收价明确返回 unavailable。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx.py、src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 比较多个 TDX 适配器的重连、rate 公式、pre_close 分母和 now_trading 日历逻辑。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_tdx.py' 'src/tradingview_zy/exchange/exchange_tdx_hk.py' 'src/tradingview_zy/exchange/exchange_tdx_us.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_tdx.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx.py)
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_hk.py)
- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_us.py)
- [`src/tradingview_zy/exchange/exchange_tdx_fx.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_fx.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-23"></a>

### ME-23 · 期货手续费/保证金参数硬编码且没有生效日期与数据版本

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/futures_contracts.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 参数外部化为带 effective_from/to、source、version 的数据集；回测产物嵌入 hash/快照；缺少目标日期配置时失败。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/backtesting/futures_contracts.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/futures_contracts.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-23 · 期货手续费/保证金参数硬编码且没有生效日期与数据版本

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [期货参数数据集](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/backtesting/futures_parameters.py) — 版本、生效日期、来源与摘要
- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Backtesting Config
- **来源：** 此前审查
- **工作量：** L
- **标签：** 正确性、治理

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/futures_contracts.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 参数外部化为带 effective_from/to、source、version 的数据集；回测产物嵌入 hash/快照；缺少目标日期配置时失败。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分属于回测引擎。回测会按照历史 K 线模拟下单、持仓、现金和绩效指标；任何日期、数量、成本、手续费或年化公式错误都会沿后续计算持续放大。

**当前/原始错误行为：** futures_contracts.py 保存静态合约乘数、保证金和手续费，注释来源日期固定；交易所规则会变化，但回测结果没有记录参数快照或有效期。

**正确行为应该是什么：** 参数外部化为带 effective_from/to、source、version 的数据集；回测产物嵌入 hash/快照；缺少目标日期配置时失败。

**直观例子：** 直观地看，这项问题意味着：同一回测在未来仍使用旧费率，利润和资金占用不可信；

#### 2. 影响分析

同一回测在未来仍使用旧费率，利润和资金占用不可信；无法复现当时规则。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 跨费率变更日期回测，验证选用不同版本；结果文件记录数据版本。 修改前测试应失败。
2. **实施修复：** 参数外部化为带 effective_from/to、source、version 的数据集
3. **实施修复：** 回测产物嵌入 hash/快照
4. **实施修复：** 缺少目标日期配置时失败。
5. **执行回归验证：** 跨费率变更日期回测，验证选用不同版本；结果文件记录数据版本。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 参数外部化为带 effective_from/to、source、version 的数据集；回测产物嵌入 hash/快照；缺少目标日期配置时失败。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/futures_contracts.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 比较回测日期与静态合约参数的版本/生效期，检查结果中是否记录配置快照和数据 hash。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/futures_contracts.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 公式和状态更新位置可静态/最小算例确认；未用真实历史数据做大样本回归，影响规模需黄金基准测试。

**最新证据：**

- [`src/tradingview_zy/backtesting/futures_contracts.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/futures_contracts.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="HI-16"></a>

### HI-16 · 文件缓存非原子写入、读错即删，且使用可执行反序列化格式

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** file_db 仍使用非原子写入和可执行反序列化格式，读取异常时删除缓存；相关路径未被后续修复触及。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 临时文件+fsync+原子 replace；优先安全序列化；校验失败隔离坏文件而不是无条件删除。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/file_db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/file_db.py) — 缓存读写和反序列化

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### HI-16 · 文件缓存非原子写入、读错即删，且使用可执行反序列化格式

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [文件缓存](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/file_db.py) — 原子写、隔离和可信 Pickle
- [缓存安全测试](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/tests/test_file_cache_safety.py) — 损坏、路径和完整性
- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** File Cache
- **来源：** 此前审查
- **工作量：** L
- **标签：** 可靠性、安全、CWE-502

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/file_db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** CSV/Parquet 使用临时文件+fsync+原子 rename 和文件锁；读取错误隔离而非立即删除；把“未完成 bar”作为显式参数/元数据；持久状态改用安全 schema 格式，或至少限制目录权限并验证来源。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** TDX CSV 直接写目标文件，没有临时文件、fsync/rename 或锁；任何 read_csv 异常都立即 unlink。读取成功后会按注释主动丢弃最后一行，这可能是未完成 bar 策略，但协议未记录，且单行缓存会变成空表。回测/交易状态缓存使用 pickle.load()，若加载目录可被不可信主体写入则可执行 payload。

**正确行为应该是什么：** CSV/Parquet 使用临时文件+fsync+原子 rename 和文件锁；读取错误隔离而非立即删除；把“未完成 bar”作为显式参数/元数据；持久状态改用安全 schema 格式，或至少限制目录权限并验证来源。

**直观例子：** 缓存读写键、原子写入和损坏恢复必须一致，否则缓存反而制造重复请求或数据缺口。

#### 2. 影响分析

并发写或进程崩溃可能产生半文件，暂时性读取错误被放大为删除；“去最后一行”对调用方是隐藏契约，可能造成单行/静态缓存意外为空。pickle 风险要求本地文件写权限，不是默认远程 RCE。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 并发写、断电半文件、单行缓存、只读权限和校验失败测试；恶意 pickle 必须无法被默认路径加载。 修改前测试应失败。
2. **实施修复：** CSV/Parquet 使用临时文件+fsync+原子 rename 和文件锁
3. **实施修复：** 读取错误隔离而非立即删除
4. **实施修复：** 把“未完成 bar”作为显式参数/元数据
5. **实施修复：** 持久状态改用安全 schema 格式，或至少限制目录权限并验证来源。
6. **执行回归验证：** 并发写、断电半文件、单行缓存、只读权限和校验失败测试；恶意 pickle 必须无法被默认路径加载。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** CSV/Parquet 使用临时文件+fsync+原子 rename 和文件锁；读取错误隔离而非立即删除；把“未完成 bar”作为显式参数/元数据；持久状态改用安全 schema 格式，或至少限制目录权限并验证来源。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/file_db.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 FileCacheDB 的读写异常分支、缓存行裁剪和 pickle 入口，并区分代码注释中的策略意图与未文档化风险。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/file_db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未执行并发/断电故障注入；pickle 风险取决于部署目录权限。

**最新证据：**

- [`src/tradingview_zy/file_db.py（47-L145）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/file_db.py#L47-L145)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-17"></a>

### ME-17 · ExchangeQMT 使用可变默认参数、忽略 end_date 并缺少空数据校验

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_qmt.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 默认参数改 None；严格裁剪 start/end；分离下载与读取；schema 校验和明确错误类型。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_qmt.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_qmt.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-17 · ExchangeQMT 使用可变默认参数、忽略 end_date 并缺少空数据校验

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** QMT Market Data
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_qmt.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 默认参数改 None；严格裁剪 start/end；分离下载与读取；schema 校验和明确错误类型。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 部分方法默认 list/dict 可变对象；klines 路径未完整应用 end_date，且每次可能触发下载；ticks 对 provider 字段直接除法，缺失/0 值处理不完整。

**正确行为应该是什么：** 默认参数改 None；严格裁剪 start/end；分离下载与读取；schema 校验和明确错误类型。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

调用间状态泄漏、回测区间超出预期、网络放大和空数据异常。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 连续调用不共享默认对象；区间边界、空表、lastClose=0、下载失败测试。 修改前测试应失败。
2. **实施修复：** 默认参数改 None
3. **实施修复：** 严格裁剪 start/end
4. **实施修复：** 分离下载与读取
5. **实施修复：** schema 校验和明确错误类型。
6. **执行回归验证：** 连续调用不共享默认对象；区间边界、空表、lastClose=0、下载失败测试。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 默认参数改 None；严格裁剪 start/end；分离下载与读取；schema 校验和明确错误类型。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_qmt.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 QMT 行情 start/end 参数、下载副作用、空响应、可变默认参数和 tick 分母边界。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_qmt.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_qmt.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_qmt.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-26"></a>

### ME-26 · 调度器在 Flask app factory 内立即 start，可能在多 worker/reloader 中重复运行

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 最新 create_app() 仍在函数内创建并 scheduler.start()，进程内 job 状态设计没有变化。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 调度器独立进程或 leader election；Web 仅管理持久化 job store；app factory 不启动后台线程。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-26 · 调度器在 Flask app factory 内立即 start，可能在多 worker/reloader 中重复运行

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Scheduler Lifecycle
- **来源：** 此前审查
- **工作量：** L
- **标签：** 可靠性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 create_app() 仍在函数内创建并 scheduler.start()，进程内 job 状态设计没有变化。

**剩余工作：** 调度器独立进程或 leader election；Web 仅管理持久化 job store；app factory 不启动后台线程。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责定时运行选股或监控策略。任务配置必须可验证、调度周期必须准确、重复运行要幂等，单个标的失败也不能悄悄伪装成整批成功。

**当前/原始错误行为：** 每次 create_app 都创建并启动 scheduler，任务状态保存在进程内 dict。测试、开发重载或多 worker 会产生多个独立调度器和重复任务。

**正确行为应该是什么：** 调度器独立进程或 leader election；Web 仅管理持久化 job store；app factory 不启动后台线程。

**直观例子：** 调度器放在每个 Web 进程里时，开两个 worker 就可能把同一任务执行两遍。

#### 2. 影响分析

监控重复执行、重复通知/落库；/jobs 只展示当前进程状态；扩容后行为不可预测。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 两个 Web worker 运行时只有一个 leader 执行任务；重载不重复注册；job 状态跨进程一致。 修改前测试应失败。
2. **实施修复：** 调度器独立进程或 leader election
3. **实施修复：** Web 仅管理持久化 job store
4. **实施修复：** app factory 不启动后台线程。
5. **执行回归验证：** 两个 Web worker 运行时只有一个 leader 执行任务；重载不重复注册；job 状态跨进程一致。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 调度器独立进程或 leader election；Web 仅管理持久化 job store；app factory 不启动后台线程。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 create_app() 仍在函数内创建并 scheduler.start()，进程内 job 状态设计没有变化。

**原报告采用的排查方法：** 沿 Flask app factory、reloader/多 worker 和进程内 job 状态检查 scheduler 启动次数、leader 和持久化。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 调度配置和状态更新路径已核对；未运行多 worker、长时间时钟和并发故障注入，实际重复频率需集成测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-19"></a>

### ME-19 · 选股结果替换不是事务，写入中途失败会留下半成品；opt_type 参数未生效

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** xuangu_tasks.py 只改策略加载；清空目标组后逐条写入、opt_type 未消费和任务状态键问题仍在。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 写入 staging 并在单事务成功后替换；真正使用 opt_type 或删除；running_tasks 使用 (market,task_name)。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/xuangu_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/xuangu_tasks.py) — 当前实现路径
- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-19 · 选股结果替换不是事务，写入中途失败会留下半成品；opt_type 参数未生效

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [选股任务](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/web/tradingview_zy_chart/cl_app/xuangu_tasks.py) — 失败不替换与方向筛选
- [自选事务替换](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/db.py) — 原子更新
- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Selection Tasks
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、可靠性

#### 当前状态与最新验证

**最新 master 验证结论：** xuangu_tasks.py 只改策略加载；清空目标组后逐条写入、opt_type 未消费和任务状态键问题仍在。

**剩余工作：** 写入 staging 并在单事务成功后替换；真正使用 opt_type 或删除；running_tasks 使用 (market,task_name)。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责定时运行选股或监控策略。任务配置必须可验证、调度周期必须准确、重复运行要幂等，单个标的失败也不能悄悄伪装成整批成功。

**当前/原始错误行为：** 策略和所有频率先计算 results，之后目标组才被清空并逐条 add_stock，因此旧版“先清空再计算”不准确；但 clear+逐条插入不是原子事务，插入中途失败仍会留下空/半组。opt_type 一直传入却未参与 SelectionRunner 或过滤。running_tasks 只按 task_name 保存，跨市场同名任务覆盖内存快照；scheduler id 已包含 market。

**正确行为应该是什么：** 写入 staging 并在单事务成功后替换；真正使用 opt_type 或删除；running_tasks 使用 (market,task_name)。

**直观例子：** 直观地看，这项问题意味着：数据库写入异常会破坏上一版结果；

#### 2. 影响分析

数据库写入异常会破坏上一版结果；UI 方向选项与实际行为不一致；跨市场同名任务的内存结果无法区分。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 策略计算失败旧组不变；第 N 条插入失败整个替换回滚；跨市场同名任务分别可查；opt_type 有可观察效果或被拒绝。 修改前测试应失败。
2. **实施修复：** 写入 staging 并在单事务成功后替换
3. **实施修复：** 真正使用 opt_type 或删除
4. **实施修复：** running_tasks 使用 (market,task_name)。
5. **执行回归验证：** 策略计算失败旧组不变；第 N 条插入失败整个替换回滚；跨市场同名任务分别可查；opt_type 有可观察效果或被拒绝。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 写入 staging 并在单事务成功后替换；真正使用 opt_type 或删除；running_tasks 使用 (market,task_name)。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** xuangu_tasks.py 只改策略加载；清空目标组后逐条写入、opt_type 未消费和任务状态键问题仍在。

**原报告采用的排查方法：** 按 _run_xuangu_job 的实际顺序检查策略计算、clear、逐条写、任务键和 opt_type 全仓引用。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/xuangu_tasks.py' 'web/tradingview_zy_chart/cl_app/xuangu_tasks.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 调度配置和状态更新路径已核对；未运行多 worker、长时间时钟和并发故障注入，实际重复频率需集成测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/xuangu_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/xuangu_tasks.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-18"></a>

### ME-18 · 选股/监控缺少失败标的隔离和输入数据协议校验

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 设计文档被删除不等于功能修复；SelectionRunner/MonitoringRunner 的失败隔离与输入 schema 未修改。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** BatchRunResult 明确 hits、misses、failures；每个 symbol 独立错误；策略调用前做一次轻量 KlineFrame 校验。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/strategies/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/strategies/base.py) — 当前实现路径
- [`src/tradingview_zy/selection.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/selection.py) — 当前实现路径
- [`src/tradingview_zy/monitoring.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/monitoring.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-18 · 选股/监控缺少失败标的隔离和输入数据协议校验

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [策略基础协议](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/strategies/base.py) — K 线与信号校验
- [选股 runner](https://github.com/zhangyu-ch/tradingview/blob/agent/current-comprehensive-remediation/src/tradingview_zy/selection.py) — 批量失败模型
- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Strategy Runners
- **来源：** 此前审查
- **工作量：** M
- **标签：** 需求、正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 设计文档被删除不等于功能修复；SelectionRunner/MonitoringRunner 的失败隔离与输入 schema 未修改。

**剩余工作：** BatchRunResult 明确 hits、misses、failures；每个 symbol 独立错误；策略调用前做一次轻量 KlineFrame 校验。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责定时运行选股或监控策略。任务配置必须可验证、调度周期必须准确、重复运行要幂等，单个标的失败也不能悄悄伪装成整批成功。

**当前/原始错误行为：** Runner 假定 K 线具备必需列、非空、时区正确；策略异常处理不统一。规格要求行情异常时记录失败标的，但当前结果模型没有标准 failed_codes/errors。

**正确行为应该是什么：** BatchRunResult 明确 hits、misses、failures；每个 symbol 独立错误；策略调用前做一次轻量 KlineFrame 校验。

**直观例子：** 同一个 09:30 在上海、纽约和 UTC 代表不同绝对时刻；naive datetime 会让结果依赖服务器时区。

#### 2. 影响分析

单标的脏数据可能中断批次或只在日志中消失；用户无法区分“未命中”与“执行失败”。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 混合正常/空/缺列/策略抛错标的，批次继续且失败列表准确。 修改前测试应失败。
2. **实施修复：** BatchRunResult 明确 hits、misses、failures
3. **实施修复：** 每个 symbol 独立错误
4. **实施修复：** 策略调用前做一次轻量 KlineFrame 校验。
5. **执行回归验证：** 混合正常/空/缺列/策略抛错标的，批次继续且失败列表准确。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** BatchRunResult 明确 hits、misses、failures；每个 symbol 独立错误；策略调用前做一次轻量 KlineFrame 校验。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 设计文档被删除不等于功能修复；SelectionRunner/MonitoringRunner 的失败隔离与输入 schema 未修改。

**原报告采用的排查方法：** 沿 exchange.klines→StrategyContext→strategy.run 检查空表/缺列、逐标的异常隔离和 failures 结果模型。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/selection.py' 'src/tradingview_zy/monitoring.py' 'docs/superpowers/specs/2026-05-03-remove-chanlun-design.md'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 完整固定提交已静态核对；若需量化实际影响，仍应增加针对该路径的动态回归测试。

**最新证据：**

- [`src/tradingview_zy/selection.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/selection.py)
- [`src/tradingview_zy/monitoring.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/monitoring.py)
- [`docs/superpowers/specs/2026-05-03-remove-chanlun-design.md（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-14"></a>

### ME-14 · TDX 美股时区通过 replace(tzinfo=pytz_zone) 附着，可能产生 LMT 偏移

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx_us.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 使用 zoneinfo 或 pytz.localize，再 astimezone；为源字段建立映射文档和数据质量断言。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_us.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-14 · TDX 美股时区通过 replace(tzinfo=pytz_zone) 附着，可能产生 LMT 偏移

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 市场日历已集中化，但 TDX US 的 pytz 附着和 volume/amount 源字段映射没有直接修复证据。
- **仍有什么问题 / 下一步：** 改用 zoneinfo/localize，并用供应商样本验证时间与成交量字段。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** TDX US
- **来源：** 此前审查
- **工作量：** S
- **标签：** 正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_us.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 使用 zoneinfo 或 pytz.localize，再 astimezone；为源字段建立映射文档和数据质量断言。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** pytz 时区应使用 localize；直接 replace 可能得到历史 Local Mean Time 偏移。代码还把 amount 赋给 volume，语义需与源字段核实。

**正确行为应该是什么：** 使用 zoneinfo 或 pytz.localize，再 astimezone；为源字段建立映射文档和数据质量断言。

**直观例子：** 同一个 09:30 在上海、纽约和 UTC 代表不同绝对时刻；naive datetime 会让结果依赖服务器时区。

#### 2. 影响分析

K 线 epoch 与交易日边界偏移，尤其在 DST；成交量字段可能实际是成交额。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 冬/夏令时各取一天，验证开收盘时间与 UTC；核对 provider volume/amount 样例。 修改前测试应失败。
2. **实施修复：** 使用 zoneinfo 或 pytz.localize，再 astimezone
3. **实施修复：** 为源字段建立映射文档和数据质量断言。
4. **执行回归验证：** 冬/夏令时各取一天，验证开收盘时间与 UTC；核对 provider volume/amount 样例。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用 zoneinfo 或 pytz.localize，再 astimezone；为源字段建立映射文档和数据质量断言。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_us.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 用 pytz replace/localize 最小复算时区偏移，并核对 provider amount/volume 字段映射。 pytz `replace` 复现 `-04:56` LMT，而 `localize` 为 `-05:00`。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_tdx_us.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_us.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-30"></a>

### ME-30 · 多个市场 now_trading 使用粗粒度硬编码，未处理节假日、午休、夜盘品种差异和 DST

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py、src/tradingview_zy/exchange/exchange_ctp.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 引入版本化 exchange calendar；按 instrument/session 查询；无法确认时返回 Unknown，而非 True。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_hk.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_us.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_tdx_fx.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_fx.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_ctp.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_ctp.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-30 · 多个市场 now_trading 使用粗粒度硬编码，未处理节假日、午休、夜盘品种差异和 DST

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 预期的关闭证据未在当前工作树全部找到，因此自动降级为部分修复。
- **仍有什么问题 / 下一步：** 继续按原修复建议补齐剩余根因和专项测试，在全部通过前不能标记为已修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Trading Calendar
- **来源：** 此前审查
- **工作量：** L
- **标签：** 正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py、src/tradingview_zy/exchange/exchange_ctp.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 引入版本化 exchange calendar；按 instrument/session 查询；无法确认时返回 Unknown，而非 True。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** HK、US、FX、CTP 等适配器用 weekday/hour 判断，部分直接 return True。市场和合约的真实交易日历未成为共享服务。

**正确行为应该是什么：** 引入版本化 exchange calendar；按 instrument/session 查询；无法确认时返回 Unknown，而非 True。

**直观例子：** 只看星期和小时无法覆盖节假日、半日市、夏令时和期货夜盘差异。

#### 2. 影响分析

闭市时仍拉行情/执行监控，开市时可能误停；美国 DST 和国内期货夜盘品种差异会产生系统性错误。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 春节、圣诞、半日市、DST 切换、国内夜盘品种和周末测试。 修改前测试应失败。
2. **实施修复：** 引入版本化 exchange calendar
3. **实施修复：** 按 instrument/session 查询
4. **实施修复：** 无法确认时返回 Unknown，而非 True。
5. **执行回归验证：** 春节、圣诞、半日市、DST 切换、国内夜盘品种和周末测试。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 引入版本化 exchange calendar；按 instrument/session 查询；无法确认时返回 Unknown，而非 True。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_tdx_hk.py、src/tradingview_zy/exchange/exchange_tdx_us.py、src/tradingview_zy/exchange/exchange_tdx_fx.py、src/tradingview_zy/exchange/exchange_ctp.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 逐市场检查 now_trading 的 weekday/hour/恒真分支，并与节假日、午休、夜盘品种和 DST 需求比较。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_tdx_hk.py' 'src/tradingview_zy/exchange/exchange_tdx_us.py' 'src/tradingview_zy/exchange/exchange_tdx_fx.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 窗口和时间规则可静态确认；完整市场日历、夜盘品种、节假日和 DST 仍需黄金数据集验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_hk.py)
- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_us.py)
- [`src/tradingview_zy/exchange/exchange_tdx_fx.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_fx.py)
- [`src/tradingview_zy/exchange/exchange_ctp.py（280-L301）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_ctp.py#L280-L301)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-22"></a>

### ME-22 · 消息 HTTP、时间和 singleton 工具缺少可靠错误、时区和并发语义

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/utils.py、src/tradingview_zy/fun.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等；所有时间边界要求 aware datetime；单例改为依赖注入或线程安全初始化。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/utils.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/utils.py) — 当前实现路径
- [`src/tradingview_zy/fun.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/fun.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-22 · 消息 HTTP、时间和 singleton 工具缺少可靠错误、时区和并发语义

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 飞书密钥和部分网络调用已加强，但 utils.py 中消息通道、HTTP timeout/status/idempotency 与全局配置副作用尚未全部统一。
- **仍有什么问题 / 下一步：** 抽取统一 HTTP 客户端和消息路由，补超时、500、重试和日志脱敏测试。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Utilities
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、可靠性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/utils.py、src/tradingview_zy/fun.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等；所有时间边界要求 aware datetime；单例改为依赖注入或线程安全初始化。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** 消息发送使用 requests.post 但未统一设置 timeout、检查 HTTP/业务状态或返回失败；部分时间工具接受 naive datetime 并依赖宿主环境，某些 timezone 参数没有形成强制契约；`fun.singleton` 的实例缓存没有锁。钉钉配置分支错误单独归入 MX-01，不在本项重复计数。

**正确行为应该是什么：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等；所有时间边界要求 aware datetime；单例改为依赖注入或线程安全初始化。

**直观例子：** 同一个 09:30 在上海、纽约和 UTC 代表不同绝对时刻；naive datetime 会让结果依赖服务器时区。

#### 2. 影响分析

网络卡住或服务返回错误时，调用方可能仍收到 True 并误以为通知成功；同一时间输入在不同主机可能产生不同结果；并发首次构造可能创建多个应为单例的昂贵连接对象。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** HTTP 超时/500/业务失败测试；跨 TZ 和 DST 测试；并发首次构造压力测试。 修改前测试应失败。
2. **实施修复：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等
3. **实施修复：** 所有时间边界要求 aware datetime
4. **实施修复：** 单例改为依赖注入或线程安全初始化。
5. **执行回归验证：** HTTP 超时/500/业务失败测试；跨 TZ 和 DST 测试；并发首次构造压力测试。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 统一 HTTP client，设置连接/读取 deadline、状态检查、重试和幂等；所有时间边界要求 aware datetime；单例改为依赖注入或线程安全初始化。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/utils.py、src/tradingview_zy/fun.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 requests 调用、时间转换函数和 singleton 实现，并与 MX-01 做根因去重。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/utils.py' 'src/tradingview_zy/fun.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未调用真实消息服务或执行线程竞态压力测试。

**最新证据：**

- [`src/tradingview_zy/utils.py（69-L189）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/utils.py#L69-L189)
- [`src/tradingview_zy/fun.py（1-L175）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/fun.py#L1-L175)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-02"></a>

### ME-02 · /tv/history 请求计数器无上限且无线程同步；首次请求返回完整历史是现有测试规定的行为

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** /tv/history 仍维护进程内 __history_req_counter 普通字典；键没有过期回收/容量上限，也没有并发同步。
- **判定依据：** V6 顶层“已修复”与当前源码不符。PR #15 仅在 history payload 增加契约校验，没有修改计数器生命周期。
- **仍有什么问题 / 下一步：** 使用有界 TTL/LRU 或外部限流器；加入锁/原子操作；按会话/IP/标的设计稳定限流键，并覆盖并发测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 无界 history 计数器及读改写流程

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-02 · /tv/history 请求计数器无上限且无线程同步；首次请求返回完整历史是现有测试规定的行为

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Web UDF
- **来源：** 此前审查
- **工作量：** M
- **标签：** 可靠性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** 安全改动未处理 __history_req_counter；最新文件仍保留无界进程内字典且无锁。

**剩余工作：** 删除隐式次数状态或使用有界 TTL/LRU 与线程安全限流器；为 key 数量、时间窗口和并发行为建立明确协议。保留 firstDataRequest 行为时，应在 UDF contract 文档中说明并设置最大返回量。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** `__history_req_counter` 是 app factory 闭包中的普通 dict，键由 symbol+resolution 组成，没有 TTL/容量上限或并发同步。旧版还把 firstDataRequest 返回整批历史列为错误；完整测试 `test_tv_history_first_request_returns_available_history_for_zoom_out` 明确断言该行为，因此该部分已撤回。

**正确行为应该是什么：** 删除隐式次数状态或使用有界 TTL/LRU 与线程安全限流器；为 key 数量、时间窗口和并发行为建立明确协议。保留 firstDataRequest 行为时，应在 UDF contract 文档中说明并设置最大返回量。

**直观例子：** 直观地看，这项问题意味着：长时间运行并接收大量不同 symbol/resolution 时字典可持续增长；

#### 2. 影响分析

长时间运行并接收大量不同 symbol/resolution 时字典可持续增长；并发请求的 counter/tm 更新可能丢失，导致不稳定的 no_data 限流。首次请求的超区间返回属于当前设计契约，不再作为问题影响。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 并发不同 key 和同 key 压测，断言内存有界、窗口可预测；继续保留并运行现有 firstDataRequest zoom-out 测试，避免把设计行为误修掉。 修改前测试应失败。
2. **实施修复：** 删除隐式次数状态或使用有界 TTL/LRU 与线程安全限流器
3. **实施修复：** 为 key 数量、时间窗口和并发行为建立明确协议。
4. **实施修复：** 保留 firstDataRequest 行为时，应在 UDF contract 文档中说明并设置最大返回量。
5. **执行回归验证：** 并发不同 key 和同 key 压测，断言内存有界、窗口可预测；继续保留并运行现有 firstDataRequest zoom-out 测试，避免把设计行为误修掉。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 删除隐式次数状态或使用有界 TTL/LRU 与线程安全限流器；为 key 数量、时间窗口和并发行为建立明确协议。保留 firstDataRequest 行为时，应在 UDF contract 文档中说明并设置最大返回量。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 安全改动未处理 __history_req_counter；最新文件仍保留无界进程内字典且无锁。

**原报告采用的排查方法：** 沿 tv_history 分支检查状态字典，并执行完整 pytest；定位现有 zoom-out 测试的明确断言。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/__init__.py' 'tests/test_selection_monitoring.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未进行长期并发内存压测；增长和竞态由状态结构直接可见。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`tests/test_selection_monitoring.py（484-L542）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_selection_monitoring.py#L484-L542) — 明确要求首次请求返回可用完整历史
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-10"></a>

### NX-10 · 策略 JSON 复用旧 String(200) 列，较长配置在 MySQL 上可能失败或截断

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 监控保存改用 strategy_id，但配置 JSON 仍写入旧 String(200) 映射列，数据库 schema 未迁移。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 新增 Text/JSON 列和独立 memo，做迁移；请求层限制合理大小并做保存后往返校验。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-10 · 策略 JSON 复用旧 String(200) 列，较长配置在 MySQL 上可能失败或截断

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Database Schema
- **来源：** 本次补充排查新发现
- **标签：** 数据完整性

#### 当前状态与最新验证

**最新 master 验证结论：** 监控保存改用 strategy_id，但配置 JSON 仍写入旧 String(200) 映射列，数据库 schema 未迁移。

**剩余工作：** 新增 Text/JSON 列和独立 memo，做迁移；请求层限制合理大小并做保存后往返校验。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** strategy_config 映射到 legacy `check_idx_ma_info=String(200)`；Web 接受任意 JSON kwargs 且无 200 字节限制。SQLite 通常不执行 VARCHAR 长度约束，MySQL 是否截断/报错取决于 SQL mode。

**正确行为应该是什么：** 新增 Text/JSON 列和独立 memo，做迁移；请求层限制合理大小并做保存后往返校验。

**直观例子：** 直观地看，这项问题意味着：较长模块路径或参数可能保存失败或截断后无法解析；

#### 2. 影响分析

较长模块路径或参数可能保存失败或截断后无法解析；SQLite 测试通过后才在 MySQL 暴露。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** SQLite/MySQL 保存 199/200/201 字节和多字节 JSON，要求完整往返或统一拒绝。 修改前测试应失败。
2. **实施修复：** 新增 Text/JSON 列和独立 memo，做迁移
3. **实施修复：** 请求层限制合理大小并做保存后往返校验。
4. **执行回归验证：** SQLite/MySQL 保存 199/200/201 字节和多字节 JSON，要求完整往返或统一拒绝。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 新增 Text/JSON 列和独立 memo，做迁移；请求层限制合理大小并做保存后往返校验。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 监控保存改用 strategy_id，但配置 JSON 仍写入旧 String(200) 映射列，数据库 schema 未迁移。

**原报告采用的排查方法：** 沿业务对象到兼容 property 和物理列类型检查长度、枚举范围、唯一键及 SQLite/MySQL 差异。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/db.py' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/db.py（78-L110）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L78-L110)
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="RV-06"></a>

### RV-06 · 图表布局、模板和绘图存储接口没有请求体/字段大小与配额限制

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 安全改动未增加 charts/templates/drawings 的请求体、字段长度或用户配额限制。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 设置全局和字段上限、每主体配额、去重/更新；超限返回 413/422。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径
- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### RV-06 · 图表布局、模板和绘图存储接口没有请求体/字段大小与配额限制

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Web Storage / Availability
- **来源：** 本次仓库复验新增
- **工作量：** M
- **标签：** 安全、可靠性、CWE-400

#### 当前状态与最新验证

**最新 master 验证结论：** 安全改动未增加 charts/templates/drawings 的请求体、字段长度或用户配额限制。

**剩余工作：** 设置全局和字段上限、每主体配额、去重/更新；超限返回 413/422。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** charts/templates/drawings 将 content/state 直接写入 Text 列；仓库未配置 MAX_CONTENT_LENGTH，也没有字段大小、记录数或总存储配额。

**正确行为应该是什么：** 设置全局和字段上限、每主体配额、去重/更新；超限返回 413/422。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

超大请求占用进程内存，重复保存膨胀数据库和响应，最终造成服务/磁盘不可用。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 边界/超限请求和连续超配额创建；绕过反向代理直连应用也必须受限。 修改前测试应失败。
2. **实施修复：** 设置全局和字段上限、每主体配额、去重/更新
3. **实施修复：** 超限返回 413/422。
4. **执行回归验证：** 边界/超限请求和连续超配额创建；绕过反向代理直连应用也必须受限。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 设置全局和字段上限、每主体配额、去重/更新；超限返回 413/422。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 安全改动未增加 charts/templates/drawings 的请求体、字段长度或用户配额限制。

**原报告采用的排查方法：** 沿布局/模板/绘图请求体进入 ORM Text/String 字段，检查 Flask MAX_CONTENT_LENGTH、字段长度、条目配额和清理策略。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`src/tradingview_zy/db.py（204-L230）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L204-L230)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：中 · 可信度：中

</details>

## 严重程度：中 · 可信度：中

</details>

## 严重程度：中 · 可信度：中

<a id="ME-15"></a>

### ME-15 · Futu 全局上下文缺少生命周期、并发和失败隔离

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_futu.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** Context manager + connection pool/lock；健康状态和重连状态机；显式 imports；进程退出钩子。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_futu.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_futu.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-15 · Futu 全局上下文缺少生命周期、并发和失败隔离

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 中
- **领域：** Futu
- **来源：** 此前审查
- **工作量：** M
- **标签：** 可靠性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_futu.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** Context manager + connection pool/lock；健康状态和重连状态机；显式 imports；进程退出钩子。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** 适配器使用模块/单例级 OpenQuoteContext；错误时可能留下 None 或失效上下文；订阅/反订阅和关闭缺乏锁与统一 finally；wildcard import 降低依赖可见性。

**正确行为应该是什么：** Context manager + connection pool/lock；健康状态和重连状态机；显式 imports；进程退出钩子。

**直观例子：** 直观地看，这项问题意味着：并发请求互相影响订阅，连接泄漏或失效后持续报错；

#### 2. 影响分析

并发请求互相影响订阅，连接泄漏或失效后持续报错；Web 进程退出不确定释放 OpenD 资源。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 并发订阅、OpenD 重启、权限失败、进程关闭和重复 close 测试。 修改前测试应失败。
2. **实施修复：** Context manager + connection pool/lock
3. **实施修复：** 健康状态和重连状态机
4. **实施修复：** 显式 imports
5. **实施修复：** 进程退出钩子。
6. **执行回归验证：** 并发订阅、OpenD 重启、权限失败、进程关闭和重复 close 测试。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** Context manager + connection pool/lock；健康状态和重连状态机；显式 imports；进程退出钩子。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_futu.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查全局 QuoteContext 的创建、订阅、并发访问、重连和关闭路径，区分静态生命周期缺口与 SDK 实际行为。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_futu.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 静态源码、签名、分支和调用图已核对；未连接对应第三方 SDK/网络，实际错误文本、回报时序和故障概率仍需沙箱验证。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_futu.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_futu.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：低 · 可信度：确定

</details>

## 严重程度：低 · 可信度：确定

</details>

## 严重程度：低 · 可信度：确定

<a id="NX-01"></a>

### NX-01 · CTP 空前置地址不会触发默认地址兜底；当前属于修复抽象类后的后续阻断

- **V7 状态：** 🛡️ 未完全修复（已阻断或缓解）
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** CTP 的空字符串前置地址兜底逻辑没有修改，底层问题仍在。最新工厂会在导入 CTP 前直接拒绝 EXCHANGE_FUTURES="ctp"，标准路径不会触发该后续错误；这是风险封堵，不是功能修复。
- **判定依据：** 当前只能证明危险路径 fail-closed/不可达，不能证明底层实现正确，因此不能标记已修复。
- **仍有什么问题 / 下一步：** 修复 CR-05 时仍必须把地址读取改为 getattr(..., "") or DEFAULT 或明确要求必填，并做地址 schema 校验。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/__init__.py) — 当前实现路径
- [`src/tradingview_zy/exchange/exchange_ctp.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_ctp.py) — 当前实现路径
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/config.py.demo) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-01 · CTP 空前置地址不会触发默认地址兜底；当前属于修复抽象类后的后续阻断

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🛡️ **未修复（已阻断/缓解）**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** CTP
- **来源：** 本次补充排查新发现
- **标签：** 正确性

#### 当前状态与最新验证

**最新 master 验证结论：** CTP 的空字符串前置地址兜底逻辑没有修改，底层问题仍在。最新工厂会在导入 CTP 前直接拒绝 EXCHANGE_FUTURES="ctp"，标准路径不会触发该后续错误；这是风险封堵，不是功能修复。

**剩余工作：** 修复 CR-05 时仍必须把地址读取改为 getattr(..., "") or DEFAULT 或明确要求必填，并做地址 schema 校验。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** config.py.demo 把 CTP_MD_FRONT/CTP_TD_FRONT 定义为空字符串；MarketCTP 仅在属性不存在时采用内置默认地址，因此 `hasattr(config, ...)` 为真时会保留空字符串。该缺陷真实存在，但当前类会先因抽象方法缺失而无法实例化，标准 get_exchange() 也没有 CTP 分支。

**正确行为应该是什么：** 与 CR-05 一并修复。使用 `getattr(config, key, "") or DEFAULT`，并在创建 API 前对 `tcp://host:port` 做 schema 校验；若不支持 CTP，则删除该默认兜底和能力声明。

**直观例子：** 直观地看，这项问题意味着：在补齐 CR-05 的抽象方法、并由外部代码直接启用 CTP 后，默认 demo 配置仍会把空地址传给 RegisterFront，导致连接失败。

#### 2. 影响分析

在补齐 CR-05 的抽象方法、并由外部代码直接启用 CTP 后，默认 demo 配置仍会把空地址传给 RegisterFront，导致连接失败。它不是当前默认 Web 或标准工厂的独立高风险入口。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 底层功能仍未修好，只是标准入口已经拒绝或风险已降低。必须保留当前阻断，禁止绕过标准入口启用该功能。

1. **先写失败测试：** 缺失属性、空字符串、空白字符串、合法 tcp 地址和非法地址参数化测试；确认抽象类修复后空配置仍能得到明确配置错误或受控默认值。 修改前测试应失败。
2. **实施修复：** 与 CR-05 一并修复。
3. **实施修复：** 使用 `getattr(config, key, "") or DEFAULT`，并在创建 API 前对 `tcp://host:port` 做 schema 校验
4. **实施修复：** 若不支持 CTP，则删除该默认兜底和能力声明。
5. **执行回归验证：** 缺失属性、空字符串、空白字符串、合法 tcp 地址和非法地址参数化测试；确认抽象类修复后空配置仍能得到明确配置错误或受控默认值。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 修复 CR-05 时仍必须把地址读取改为 getattr(..., "") or DEFAULT 或明确要求必填，并做地址 schema 校验。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** CTP 的空字符串前置地址兜底逻辑没有修改，底层问题仍在。最新工厂会在导入 CTP 前直接拒绝 EXCHANGE_FUTURES="ctp"，标准路径不会触发该后续错误；这是风险封堵，不是功能修复。

**原报告采用的排查方法：** 比较 config.py.demo 的实际属性值与 MarketCTP 的 `hasattr` 分支，并沿 ABC 实例化顺序、get_exchange() 工厂和内置启动脚本检查前置阻断与可达性。

**可自行执行的复核命令：** `pytest -q tests/test_ctp_unavailable.py`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 没有连接 CTP 前置；地址传递事实确定，实际 SDK 错误文本需仿真环境确认。

**最新证据：**

- [`CTP 标准入口已阻断`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py#L66-L85) — 风险缓解
- [`底层空地址逻辑仍在`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_ctp.py#L30-L53) — 功能问题未修复
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo)
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py) — 标准期货工厂无 CTP 分支
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-25"></a>

### NX-25 · 孤立 ExchangeZB 显式关闭 TLS 证书校验

- **V7 状态：** 🛡️ 未完全修复（已阻断或缓解）
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 标准工厂不注册 ZB，降低默认可达性；但 ExchangeZB 仍在运行源码树并显式 params["verify"]=False，可被直接导入使用。
- **判定依据：** 当前只能证明危险路径 fail-closed/不可达，不能证明底层实现正确，因此不能标记已修复。
- **仍有什么问题 / 下一步：** 删除/归档该适配器，或恢复 TLS 验证、证书配置与测试；保持标准入口不支持。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_zb.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_zb.py) — 显式关闭 TLS 验证
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 标准工厂未注册 ZB

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-25 · 孤立 ExchangeZB 显式关闭 TLS 证书校验

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Legacy Exchange Security
- **来源：** 本次补充排查新发现
- **标签：** 安全

#### 当前状态与最新验证

**最新 master 验证结论：** 最新工厂增加 CTP 分支但仍没有 ZB 分支；exchange_zb.py 的 verify=False 仍存在于直接调用路径。

**剩余工作：** 不再支持则删除适配器和配置声明；继续支持则恢复 TLS 验证、移除重复赋值、加入证书失败测试，并通过正规工厂和 capability 声明接入。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分是外部行情或交易适配器。适配器要把第三方 SDK 的返回值转换成项目统一的数据和订单语义；连接失败、部分成交、时区或分页边界都不能被当成正常成功。

**当前/原始错误行为：** ExchangeZB 构造参数显式设置 `verify=False`，并重复写入 API key/secret。当前 get_exchange() 不包含 ZB 分支，config.py.demo 虽在注释中声称支持 zb，实际标准路径不可达；风险只在外部直接 import/实例化时触发。

**正确行为应该是什么：** 不再支持则删除适配器和配置声明；继续支持则恢复 TLS 验证、移除重复赋值、加入证书失败测试，并通过正规工厂和 capability 声明接入。

**直观例子：** 直观地看，这项问题意味着：直接使用该遗留适配器时会关闭 TLS 证书校验，代理或中间人可篡改行情/订单请求；

#### 2. 影响分析

直接使用该遗留适配器时会关闭 TLS 证书校验，代理或中间人可篡改行情/订单请求；当前默认产品路径不会选中它。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 确认无 verify=False；错误证书必须失败；工厂支持矩阵和文档一致；仓库调用图不存在旁路构造。 修改前测试应失败。
2. **实施修复：** 不再支持则删除适配器和配置声明
3. **实施修复：** 继续支持则恢复 TLS 验证、移除重复赋值、加入证书失败测试，并通过正规工厂和 capability 声明接入。
4. **执行回归验证：** 确认无 verify=False；错误证书必须失败；工厂支持矩阵和文档一致；仓库调用图不存在旁路构造。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 不再支持则删除适配器和配置声明；继续支持则恢复 TLS 验证、移除重复赋值、加入证书失败测试，并通过正规工厂和 capability 声明接入。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新工厂增加 CTP 分支但仍没有 ZB 分支；exchange_zb.py 的 verify=False 仍存在于直接调用路径。

**原报告采用的排查方法：** 检查 ccxt 构造参数、工厂分支和全仓类引用。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_zb.py' 'src/tradingview_zy/exchange/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未连接 ZB；中间人影响是直接使用该类时的条件性风险。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_zb.py（14-L38）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_zb.py#L14-L38)
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/__init__.py) — 数字货币工厂无 ZB 分支
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-29"></a>

### ME-29 · 当前提交无可见 CI 状态，测试集中在少数协议单元，核心风险无门禁

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** 仓库已有持久化 GitHub Actions：Python 3.11 使用 uv sync --locked 运行完整 pytest 且 warnings-as-errors，Python 3.13 单独验证依赖 warning 基线。PR #15 最终合并检查为 172 passed。浏览器、MySQL 和真实外部 SDK 仍不在门禁内。
- **判定依据：** 相较 V6，CI 可见性和覆盖面显著提升，但高风险集成域仍缺门禁，因此保持部分修复而不是关闭。
- **仍有什么问题 / 下一步：** 增加 MySQL、浏览器/DOM、核心 provider mock/沙箱矩阵；在仓库分支保护中把 checks 设为 required，并验证合并提交 push 检查。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`.github/workflows/tests.yml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/.github/workflows/tests.yml) — 只读、锁文件、严格 warnings 和双 job CI
- [`tests`](https://github.com/zhangyu-ch/tradingview/tree/3488462529c6ec052192eb41d1a6b74c5718c58f/tests) — 当前 172 项测试集合

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-29 · 当前提交无可见 CI 状态，测试集中在少数协议单元，核心风险无门禁

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 测试数量和覆盖面显著增加，本地完整回归通过；但仓库仍缺少稳定的 required CI checks。
- **仍有什么问题 / 下一步：** 提交长期 workflow，并在仓库设置中将 compileall、pytest、JS、依赖审计和 Secret 扫描设为必需检查。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 中
- **可信度：** 确定
- **领域：** Quality Gates
- **来源：** 双方
- **工作量：** L
- **标签：** 规范、需求、外部 O-39

#### 当前状态与最新验证

**最新 master 验证结论：** 最新仓库新增策略安全、Web 安全、年化和 CTP 不可用测试，覆盖面比基线明显扩大；但是仓库仍没有持久化 GitHub Actions workflow/required checks，数据库约束、聚合、实盘订单、浏览器安全等核心域仍没有门禁。因此只能标记部分修复。

**剩余工作：** 提交正式 CI workflow，并把 compileall、pytest、静态扫描、依赖审计和关键 contract tests 设为合并必需检查。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 固定提交没有可见组合状态或 workflow run。现有测试覆盖策略加载、payload、选股/监控、回测基类和旧 import 边界，但未覆盖认证/RCE/CSRF、数据库约束、频率聚合、绩效数学、实盘订单和适配器实例化。

**正确行为应该是什么：** 最小 CI：ruff/format、compileall、mypy/pyright（渐进）、pytest、Bandit/Semgrep、依赖审计；外部 SDK 用 fake/contract tests，夜间跑 sandbox 集成。

**直观例子：** 请求带有合法登录 Cookie，并不代表用户主动点击了本系统中的按钮。

#### 2. 影响分析

多个确定性错误可在主分支长期存在；依赖或 SDK 更新没有自动回归信号。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 把本报告 P0/P1 回归用例固化为 required checks；禁止无绿灯合并。 修改前测试应失败。
2. **实施修复：** 最小 CI：ruff/format、compileall、mypy/pyright（渐进）、pytest、Bandit/Semgrep、依赖审计
3. **实施修复：** 外部 SDK 用 fake/contract tests，夜间跑 sandbox 集成。
4. **执行回归验证：** 把本报告 P0/P1 回归用例固化为 required checks；禁止无绿灯合并。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 提交正式 CI workflow，并把 compileall、pytest、静态扫描、依赖审计和关键 contract tests 设为合并必需检查。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新仓库新增策略安全、Web 安全、年化和 CTP 不可用测试，覆盖面比基线明显扩大；但是仓库仍没有持久化 GitHub Actions workflow/required checks，数据库约束、聚合、实盘订单、浏览器安全等核心域仍没有门禁。因此只能标记部分修复。

**原报告采用的排查方法：** 检查仓库 .github/workflows、提交状态、tests 覆盖域和 required checks，并把问题清单与现有测试逐项映射。

**可自行执行的复核命令：** `find .github/workflows -maxdepth 1 -type f -print 2>/dev/null; pytest -q`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 仓库文件和本地测试环境已核对；未执行所有平台原生安装、在线漏洞数据库或托管 CI 服务。

**最新证据：**

- [`新增策略安全测试`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_strategy_loader.py) — 安全边界覆盖增加
- [`新增 Web 安全测试`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_web_security.py) — 认证和 Cookie 覆盖增加
- [`新增年化测试`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_backtest_annualization.py) — 绩效映射覆盖增加
- [`仓库 Actions 页面`](https://github.com/zhangyu-ch/tradingview/actions) — 仍无持久化 required workflow
- [`tests/test_web_payloads.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_web_payloads.py)
- [`tests/test_selection_monitoring.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_selection_monitoring.py)
- [`tests/test_backtesting_base_generic.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/tests/test_backtesting_base_generic.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-10"></a>

### ME-10 · 统一 Exchange 接口没有能力声明和统一错误模型

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** 新增 Capability、统一领域错误、MarketRegistry 和 require_capability；未知市场/provider fail-closed，构造失败前不缓存。但旧 Exchange 大接口及部分 provider 的声明/实现一致性尚未完全解决。
- **判定依据：** 能力发现和错误模型已有实质改进，原始架构根因只关闭一部分；V7 新列 NEW-06 说明 DB provider 仍存在能力过报。
- **仍有什么问题 / 下一步：** 拆分细粒度 Protocol；对每个 provider 做“声明能力必须有真实实现”的契约测试；修正 DB provider 的 security_master/plates 声明。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/domain.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/domain.py) — Capability 与统一错误类型
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — provider 能力注册
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/__init__.py) — 注册表驱动工厂
- [`tests/test_v6_market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_market_registry.py) — 市场/能力契约测试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-10 · 统一 Exchange 接口没有能力声明和统一错误模型

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 能力注册表和统一 Unsupported/Unavailable 错误已引入，但旧的宽 Exchange 基类与部分适配器的 None/空表/异常差异仍未完全收敛。
- **仍有什么问题 / 下一步：** 继续拆分 MarketData/Trading/Calendar 协议，并让所有适配器运行同一 contract suite。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Adapter Architecture
- **来源：** 双方
- **工作量：** XL
- **标签：** 规范、正确性、外部 O-14

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 拆分 MarketDataProvider、InstrumentCatalog、TradingExecution、CalendarProvider 协议；定义 Unsupported/Unavailable/InvalidRequest/Empty/RateLimited 错误类型。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 同一方法在不同适配器中返回 None、空 DataFrame、False、字典或抛通用 Exception；“未配置、暂时不可用、不支持、无数据”没有可区分类型。大量非交易行情类被迫实现 balance/order 并抛异常。

**正确行为应该是什么：** 拆分 MarketDataProvider、InstrumentCatalog、TradingExecution、CalendarProvider 协议；定义 Unsupported/Unavailable/InvalidRequest/Empty/RateLimited 错误类型。

**直观例子：** 直观地看，这项问题意味着：上层只能用宽泛 try/except 或长度判断，错误容易被误当成无数据；

#### 2. 影响分析

上层只能用宽泛 try/except 或长度判断，错误容易被误当成无数据；UI 无法准确展示可用性，测试难以复用。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 跨适配器 contract suite：相同输入产生相同 schema 和错误类型；capabilities 与实际方法一致。 修改前测试应失败。
2. **实施修复：** 拆分 MarketDataProvider、InstrumentCatalog、TradingExecution、CalendarProvider 协议
3. **实施修复：** 定义 Unsupported/Unavailable/InvalidRequest/Empty/RateLimited 错误类型。
4. **执行回归验证：** 跨适配器 contract suite：相同输入产生相同 schema 和错误类型；capabilities 与实际方法一致。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 拆分 MarketDataProvider、InstrumentCatalog、TradingExecution、CalendarProvider 协议；定义 Unsupported/Unavailable/InvalidRequest/Empty/RateLimited 错误类型。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 比较 Exchange 抽象方法、各实现的能力和错误返回，统计被迫拒绝的继承方法，并检查上层如何区分 Unsupported、Unavailable 与 Empty。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange.py（37-L150）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange.py#L37-L150)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-20"></a>

### ME-20 · 策略输出只有形状约定，没有边界校验和领域类型

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 策略加载器现在会验证目标是类、具有 run()、构造参数签名和参数类型，这修复了“构造前无边界”的一部分。可是 StrategySignal 返回值的 action、score、时间、code/frequency 和有限数值仍未在 runner 边界统一校验。
- **判定依据：** V6 已记录部分缓解；最新 master 未出现足以关闭全部根因的新增证据，状态保持部分修复。
- **仍有什么问题 / 下一步：** 为策略输出建立版本化 schema/validated dataclass，并在 SelectionRunner/MonitoringRunner 接受结果时逐项验证。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/strategies/loader.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/strategies/loader.py) — 当前实现路径
- [`src/tradingview_zy/strategies/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/strategies/base.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-20 · 策略输出只有形状约定，没有边界校验和领域类型

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Strategy Protocol
- **来源：** 双方
- **工作量：** M
- **标签：** 需求、规范、外部 O-32

#### 当前状态与最新验证

**最新 master 验证结论：** 策略加载器现在会验证目标是类、具有 run()、构造参数签名和参数类型，这修复了“构造前无边界”的一部分。可是 StrategySignal 返回值的 action、score、时间、code/frequency 和有限数值仍未在 runner 边界统一校验。

**剩余工作：** 为策略输出建立版本化 schema/validated dataclass，并在 SelectionRunner/MonitoringRunner 接受结果时逐项验证。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责定时运行选股或监控策略。任务配置必须可验证、调度周期必须准确、重复运行要幂等，单个标的失败也不能悄悄伪装成整批成功。

**当前/原始错误行为：** StrategySignal/Context 使用字符串 action、普通 dict 和 DataFrame；frozen dataclass 内仍含可变对象。加载器仅检查 run 可调用，不验证返回项字段、有限 score、合法 action、事件时间和 code/frequency 一致性。

**正确行为应该是什么：** 定义 Enum/validated dataclass 或 Pydantic schema；策略边界一次性校验；不可变上下文使用只读视图/复制；版本化协议。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

错误策略可写入非法信号、NaN 分数或错标的事件；监控/交易层再以不同规则解释字符串。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 缺字段、错类型、非法 action、NaN/Inf、naive 时间、错误 code/frequency 均被拒绝并给出清晰错误。 修改前测试应失败。
2. **实施修复：** 定义 Enum/validated dataclass 或 Pydantic schema
3. **实施修复：** 策略边界一次性校验
4. **实施修复：** 不可变上下文使用只读视图/复制
5. **实施修复：** 版本化协议。
6. **执行回归验证：** 缺字段、错类型、非法 action、NaN/Inf、naive 时间、错误 code/frequency 均被拒绝并给出清晰错误。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 为策略输出建立版本化 schema/validated dataclass，并在 SelectionRunner/MonitoringRunner 接受结果时逐项验证。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 策略加载器现在会验证目标是类、具有 run()、构造参数签名和参数类型，这修复了“构造前无边界”的一部分。可是 StrategySignal 返回值的 action、score、时间、code/frequency 和有限数值仍未在 runner 边界统一校验。

**原报告采用的排查方法：** 检查 StrategyContext/StrategySignal 的运行时类型约束、normalize 边界和字段级合法性（action、score、时间、code/frequency）。

**可自行执行的复核命令：** `pytest -q tests/test_strategy_loader.py tests/test_selection_monitoring.py`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 完整固定提交已静态核对；若需量化实际影响，仍应增加针对该路径的动态回归测试。

**最新证据：**

- [`当前策略加载校验`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/strategies/loader.py#L206-L268) — 类、签名、kwargs 已校验
- [`策略信号模型`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/strategies/base.py) — 输出字段仍缺少统一运行时校验
- [`src/tradingview_zy/strategies/loader.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/strategies/loader.py)
- [`docs/superpowers/specs/2026-05-03-remove-chanlun-design.md（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-25"></a>

### ME-25 · 依赖范围宽、旧 setup.py 与 pyproject 不一致，缺少可验证供应链清单

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 旧 setup.py 和 MANIFEST.in 已删除，Apache-2.0 与 setup.py 中 MIT 的许可证冲突、重复打包入口以及 PyArmor 依赖均已消除。仍存在大量仅设下界的依赖、本地 wheel 缺少显式哈希/来源说明、SBOM/漏洞审计门禁缺失等问题。
- **判定依据：** 相关路径在 PR #15 中有实质变化，但静态复核仍能定位到原问题的一部分，因此标记部分修复。
- **仍有什么问题 / 下一步：** 以 uv.lock 为唯一受支持安装路径并在 CI 校验；记录本地 wheel SHA-256/来源并生成 SBOM、许可证和漏洞报告。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`pyproject.toml`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/pyproject.toml) — 包元数据与依赖策略
- [`uv.lock`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/uv.lock) — 锁定依赖图

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-25 · 依赖范围宽、旧 setup.py 与 pyproject 不一致，缺少可验证供应链清单

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 旧 setup.py、PyArmor 和部分许可证冲突已清理，也保留 uv.lock；但正式 SBOM、依赖漏洞/许可证门禁和本地 wheel 来源哈希尚未进入持久 CI。
- **仍有什么问题 / 下一步：** 提交正式 CI，生成并校验 SBOM，记录本地 wheel 来源与 SHA-256。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Supply Chain
- **来源：** 双方
- **工作量：** L
- **标签：** 安全、治理、外部 O-35、外部 O-44、外部 O-57

#### 当前状态与最新验证

**最新 master 验证结论：** 旧 setup.py 和 MANIFEST.in 已删除，Apache-2.0 与 setup.py 中 MIT 的许可证冲突、重复打包入口以及 PyArmor 依赖均已消除。仍存在大量仅设下界的依赖、本地 wheel 缺少显式哈希/来源说明、SBOM/漏洞审计门禁缺失等问题。

**剩余工作：** 以 uv.lock 为唯一受支持安装路径并在 CI 校验；记录本地 wheel SHA-256/来源并生成 SBOM、许可证和漏洞报告。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 仓库存在 uv.lock，因此“完全没有锁文件”不成立；但 pyproject 多数依赖只设下界，setup.py 不声明完整依赖，本地 wheel 缺少来源/hash/SBOM/自动漏洞门禁。另一个确定问题是根 LICENSE 为 Apache-2.0，而 setup.py 的 `license="MIT"` 与之冲突；pyarmor 仍在依赖中。

**正确行为应该是什么：** 以 uv.lock 为唯一可复现安装入口并在 CI 校验；退役 setup.py 或从 pyproject 单一生成；把包许可证元数据改成 Apache-2.0/SPDX；记录本地 wheel 来源和 SHA-256，生成 SBOM/许可证和漏洞报告。

**直观例子：** 直观地看，这项问题意味着：绕过 uv.lock 使用 setup.py 会得到不完整环境；

#### 2. 影响分析

绕过 uv.lock 使用 setup.py 会得到不完整环境；本地二进制来源难以审计；许可证元数据冲突会使发布包、合规扫描和下游用户收到错误许可信息。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 干净 Python 3.11 按锁安装；构建 wheel 后检查 Metadata License-Expression；运行 SBOM/license/vulnerability scanner，并验证本地 wheel 哈希。 修改前测试应失败。
2. **实施修复：** 以 uv.lock 为唯一可复现安装入口并在 CI 校验
3. **实施修复：** 退役 setup.py 或从 pyproject 单一生成
4. **实施修复：** 把包许可证元数据改成 Apache-2.0/SPDX
5. **实施修复：** 记录本地 wheel 来源和 SHA-256，生成 SBOM/许可证和漏洞报告。
6. **执行回归验证：** 干净 Python 3.11 按锁安装；构建 wheel 后检查 Metadata License-Expression；运行 SBOM/license/vulnerability scanner，并验证本地 wheel 哈希。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 以 uv.lock 为唯一受支持安装路径并在 CI 校验；记录本地 wheel SHA-256/来源并生成 SBOM、许可证和漏洞报告。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 旧 setup.py 和 MANIFEST.in 已删除，Apache-2.0 与 setup.py 中 MIT 的许可证冲突、重复打包入口以及 PyArmor 依赖均已消除。仍存在大量仅设下界的依赖、本地 wheel 缺少显式哈希/来源说明、SBOM/漏洞审计门禁缺失等问题。

**原报告采用的排查方法：** 比较 pyproject.toml、uv.lock、setup.py、LICENSE、MANIFEST 和本地 wheel source，检查依赖完整性、版本锁定、许可证和完整性元数据是否单一一致。

**可自行执行的复核命令：** `test ! -e setup.py && test ! -e MANIFEST.in && uv lock --check`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 本次未运行完整依赖漏洞数据库和许可证扫描；元数据冲突本身确定。

**最新证据：**

- [`当前 pyproject`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/pyproject.toml#L3-L66) — 仍有宽范围和本地 wheel
- [`当前锁文件`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/uv.lock) — 可复现入口保留
- [`删除旧打包入口提交`](https://github.com/zhangyu-ch/tradingview/commit/e4c2363dd05ceacf0436067e4f164c9499e05111) — setup.py/MANIFEST.in 已删除
- [`pyproject.toml`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/pyproject.toml)
- [`LICENSE`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/LICENSE)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-27"></a>

### ME-27 · 交易/API 密钥设计为明文 Python 配置，缺少分级与轮换机制

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** Web 登录密码和 Flask 会话密钥现在支持环境变量/随机持久化，且默认远程免密访问被阻止，降低了配置泄露后的直接利用面。但是数据库、交易所、券商、AI 和飞书等业务密钥仍集中在明文 Python 配置/通用缓存中，设置页仍回显飞书 Secret。
- **判定依据：** 相关路径在 PR #15 中有实质变化，但静态复核仍能定位到原问题的一部分，因此标记部分修复。
- **仍有什么问题 / 下一步：** 将业务密钥迁移到环境变量、系统 keyring 或 Vault；设置 API 只接受新值而不返回旧值，统一日志脱敏与轮换。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/config.py.demo) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/templates/setting.html`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/templates/setting.html) — 当前实现路径
- [`src/tradingview_zy/web_security.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_security.py) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-27 · 交易/API 密钥设计为明文 Python 配置，缺少分级与轮换机制

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** Web 会话密钥和飞书 Secret 已迁移到专用安全存储；其他数据库、交易所、券商和 AI 密钥仍主要依赖明文 Python 配置。
- **仍有什么问题 / 下一步：** 逐类迁移到环境变量/keyring/Vault，增加统一 Secret 类型、脱敏日志和轮换流程。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Secrets
- **来源：** 此前审查
- **工作量：** L
- **标签：** 安全、治理、CWE-522

#### 当前状态与最新验证

**最新 master 验证结论：** Web 登录密码和 Flask 会话密钥现在支持环境变量/随机持久化，且默认远程免密访问被阻止，降低了配置泄露后的直接利用面。但是数据库、交易所、券商、AI 和飞书等业务密钥仍集中在明文 Python 配置/通用缓存中，设置页仍回显飞书 Secret。

**剩余工作：** 将业务密钥迁移到环境变量、系统 keyring 或 Vault；设置 API 只接受新值而不返回旧值，统一日志脱敏与轮换。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 数据库、券商、交易所、AI、飞书等秘密集中在明文 Python 配置或通用 DB cache。设置页直接回显飞书 Secret，提交前还 console.log 全部字段；没有 Secret 类型、脱敏、分级授权或轮换状态。

**正确行为应该是什么：** 使用环境变量/keyring/Vault；最小权限注入；设置 API 只接收新 secret 不返回旧值；统一脱敏和轮换/撤销。

**直观例子：** 秘密一旦进入 HTML、日志或配置备份，就可能被无关人员或工具读取。

#### 2. 影响分析

配置、页面、控制台、扩展或日志都可能泄露凭据；默认空密码使回显尤其危险。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** secret 不得出现在 HTML、DOM、控制台、日志、错误或导出；CI secret scan 和轮换测试。 修改前测试应失败。
2. **实施修复：** 使用环境变量/keyring/Vault
3. **实施修复：** 最小权限注入
4. **实施修复：** 设置 API 只接收新 secret 不返回旧值
5. **实施修复：** 统一脱敏和轮换/撤销。
6. **执行回归验证：** secret 不得出现在 HTML、DOM、控制台、日志、错误或导出；CI secret scan 和轮换测试。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 将业务密钥迁移到环境变量、系统 keyring 或 Vault；设置 API 只接受新值而不返回旧值，统一日志脱敏与轮换。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** Web 登录密码和 Flask 会话密钥现在支持环境变量/随机持久化，且默认远程免密访问被阻止，降低了配置泄露后的直接利用面。但是数据库、交易所、券商、AI 和飞书等业务密钥仍集中在明文 Python 配置/通用缓存中，设置页仍回显飞书 Secret。

**原报告采用的排查方法：** 列出配置和数据库缓存中的秘密字段，沿日志/模板/导出路径检查脱敏、最小权限和轮换机制。

**可自行执行的复核命令：** `rg -n "APIKEY|SECRET|TOKEN|APP_SECRET|fs_app_secret" src/tradingview_zy/config.py.demo web/tradingview_zy_chart/cl_app`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 配置和数据流可静态确认；实际暴露范围取决于部署访问控制、日志和外部服务。

**最新证据：**

- [`明文业务密钥模板`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo#L36-L174) — DB/券商/API/飞书字段
- [`仍回显飞书 Secret`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L29-L34) — 业务 secret 未迁移
- [`Web 安全辅助模块`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/web_security.py) — 只覆盖登录与会话密钥
- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo)
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`web/tradingview_zy_chart/cl_app/templates/setting.html（125-L132）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/setting.html#L125-L132)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-04"></a>

### ME-04 · K 线 payload 对时区、schema、排序和重复值缺少边界校验

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** K 线进入 TradingView 前已有 required columns、有限数、OHLC、volume、code/frequency、严格排序、重复时间和市场时区校验；但 /tv/history 在时区本地化之前先执行时间范围过滤，naive 市场本地时间会按服务器时区解释。
- **判定依据：** PR #15 关闭了大部分 schema 根因，但筛选顺序留下独立时区边界（V7 新列 NEW-04），因此只能标记部分修复。
- **仍有什么问题 / 下一步：** 先补全 code/市场时区并规范化，再按 Unix 秒过滤；增加服务器 UTC、A 股 naive 时间的路由级测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/kline_schema.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/kline_schema.py) — 严格 KlineFrame 协议
- [`src/tradingview_zy/web_payloads.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_payloads.py) — 时区补全与范围过滤函数
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前先过滤、后规范化的调用顺序
- [`tests/test_v6_kline_schema.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_kline_schema.py) — schema 回归测试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-04 · K 线 payload 对时区、schema、排序和重复值缺少边界校验

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 策略运行前的 K 线 schema 已校验，但 Web UDF payload 仍没有统一处理 naive/aware datetime、有限数值、OHLC 不变量和重复排序。
- **仍有什么问题 / 下一步：** 在 web_payloads 边界增加 KlineFrame schema、UTC 规则、排序去重和 NaN/Inf 检查。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Web Payload
- **来源：** 此前审查
- **工作量：** M
- **标签：** 正确性、规范

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/web_payloads.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 定义 KlineFrame schema；date 必须是 timezone-aware 并统一到 UTC/明确交易所时区；序列化前排序、去重并验证 finite 与 OHLC invariant。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** web_payloads 对每个 date 直接调用 timestamp()，未要求 timezone-aware 类型。对于 Python naive datetime，结果依赖宿主 TZ；对于本次 pandas 版本的 naive Timestamp，本地复算不随 TZ 变化，但这种混合输入契约没有声明。函数也没有验证必需列、时间单调、重复时间、NaN/Inf 或 OHLC 关系。

**正确行为应该是什么：** 定义 KlineFrame schema；date 必须是 timezone-aware 并统一到 UTC/明确交易所时区；序列化前排序、去重并验证 finite 与 OHLC invariant。

**直观例子：** 同一个 09:30 在上海、纽约和 UTC 代表不同绝对时刻；naive datetime 会让结果依赖服务器时区。

#### 2. 影响分析

只要适配器返回 Python naive datetime，同一数据会因主机时区产生不同 epoch；混合类型还可能掩盖这种差异。乱序、重复或非有限值可进入 UDF payload，导致图表缓存、序列和 JSON 行为异常。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 分别输入 Python naive datetime、pandas naive/aware Timestamp、DST 边界、乱序、重复、缺列、NaN/Inf 和 high<low；跨 TZ 环境断言 epoch 一致或非法输入被拒绝。 修改前测试应失败。
2. **实施修复：** 定义 KlineFrame schema
3. **实施修复：** date 必须是 timezone-aware 并统一到 UTC/明确交易所时区
4. **实施修复：** 序列化前排序、去重并验证 finite 与 OHLC invariant。
5. **执行回归验证：** 分别输入 Python naive datetime、pandas naive/aware Timestamp、DST 边界、乱序、重复、缺列、NaN/Inf 和 high<low；跨 TZ 环境断言 epoch 一致或非法输入被拒绝。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 定义 KlineFrame schema；date 必须是 timezone-aware 并统一到 UTC/明确交易所时区；序列化前排序、去重并验证 finite 与 OHLC invariant。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/web_payloads.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查类型注解和 timestamp 调用，并在 UTC、America/New_York、Asia/Shanghai 下分别计算 Python datetime 与 pandas Timestamp。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/web_payloads.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** pandas 对 naive Timestamp 的具体语义可能随版本变化，正因如此应在应用边界禁止模糊输入。

**最新证据：**

- [`src/tradingview_zy/web_payloads.py（1-L33）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/web_payloads.py#L1-L33)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="ME-01"></a>

### ME-01 · TradingView 存储接口信任请求中的 client/user 作为授权边界

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 登录、会话和远程免密边界已加强，匿名攻击面下降；但 TradingView chart/template/drawing 存储仍信任请求中的 client/user 作为数据分区，没有绑定已认证主体。
- **判定依据：** 认证改进属于实质缓解，但授权主键根因仍在，因此保持部分修复。
- **仍有什么问题 / 下一步：** 服务端从会话派生主体；忽略或校验客户端 user/client；为跨用户读写增加授权测试和迁移方案。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 存储路由仍读取请求 client/user
- [`src/tradingview_zy/web_security.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/web_security.py) — 已完成的认证边界

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-01 · TradingView 存储接口信任请求中的 client/user 作为授权边界

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 中
- **可信度：** 高
- **领域：** Web Storage
- **来源：** 此前审查
- **工作量：** M
- **标签：** 安全、正确性、CWE-639

#### 当前状态与最新验证

**最新 master 验证结论：** 认证加强降低了匿名访问面，但存储接口仍从请求读取 client/user 并用作数据分区，未绑定认证主体。

**剩余工作：** user_id 来自认证主体；client_id 服务器登记；更新/删除校验 owner；统一类型并对非法值返回 400/404。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** charts、study_templates、drawings 从 query string 读取 client/user 并用于查询、更新和删除，未绑定认证主体。前端固定发送 user_id="999"，所以 Integer 列与数值字符串不会导致当前必然失败；真正问题是登录会话可切换逻辑分区，缺失/非数字值也未统一校验。

**正确行为应该是什么：** user_id 来自认证主体；client_id 服务器登记；更新/删除校验 owner；统一类型并对非法值返回 400/404。

**直观例子：** 直观地看，这项问题意味着：同一部署内不同客户端命名空间可被猜测后读取、覆盖或删除；

#### 2. 影响分析

同一部署内不同客户端命名空间可被猜测后读取、覆盖或删除；未来多用户会成为越权。畸形 user 值在数据库后端间行为不一致。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议纳入近期迭代；如果对应功能正在生产环境使用，应提高优先级。

1. **先写失败测试：** 两个主体/客户端 CRUD 隔离；伪造 user/client 不得跨区；数字/UUID/缺失值双后端一致。 修改前测试应失败。
2. **实施修复：** user_id 来自认证主体
3. **实施修复：** client_id 服务器登记
4. **实施修复：** 更新/删除校验 owner
5. **实施修复：** 统一类型并对非法值返回 400/404。
6. **执行回归验证：** 两个主体/客户端 CRUD 隔离；伪造 user/client 不得跨区；数字/UUID/缺失值双后端一致。 同时运行相邻模块测试。
7. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** user_id 来自认证主体；client_id 服务器登记；更新/删除校验 owner；统一类型并对非法值返回 400/404。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 认证加强降低了匿名访问面，但存储接口仍从请求读取 client/user 并用作数据分区，未绑定认证主体。

**原报告采用的排查方法：** 沿 client/user/resource ID 从请求进入 ORM 查询、更新和删除，检查认证主体绑定、None 处理、错误返回和所有权约束。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/static/js/charts.js' 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`web/tradingview_zy_chart/cl_app/static/js/charts.js（50-L59）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/static/js/charts.js#L50-L59)
- [`src/tradingview_zy/db.py（204-L230）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L204-L230)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

## 严重程度：低（19 条）

<a id="ME-03"></a>

### ME-03 · /tv/config 的周期并集遗漏 ny_futures；当前默认适配器无独有周期，属于潜在能力漂移

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** market_frequencys 已包含 ny_futures，但 /tv/config 构造全局 supported_resolutions 时仍没有把该市场加入并集。
- **判定依据：** 原始能力漂移仍可直接定位；新增 MarketRegistry 尚未被该 Web 路由消费，因此判为未修复。
- **仍有什么问题 / 下一步：** 由 MarketRegistry 生成 UDF 配置，或至少把 ny_futures 纳入并集并增加“任一市场独有周期”回归测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — UDF 周期并集与 per-market 配置
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 尚未被 Web UDF 完整消费的注册表

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### ME-03 · /tv/config 的周期并集遗漏 ny_futures；当前默认适配器无独有周期，属于潜在能力漂移

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Web UDF
- **来源：** 双方
- **工作量：** S
- **标签：** 正确性、规范、外部 O-11

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 /tv/config 的周期并集仍没有 market_frequencys["ny_futures"]。

**剩余工作：** 仍建议修复：把 ny_futures 纳入并集，最好由 MarketDescriptor 自动生成而非手写集合。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** market_frequencys 和 exchanges 列表都包含 ny_futures，但 `/tv/config` 构造全局 frequencys 集合时漏掉它。完整仓库对默认适配器的频率 key 做 AST 复算后，ny_futures 的 key 集合目前完全被其他市场覆盖，因此当前默认配置没有实际缺失 resolution；一旦纽约期货新增独有周期，遗漏就会显现。

**正确行为应该是什么：** 仍建议修复：把 ny_futures 纳入并集，最好由 MarketDescriptor 自动生成而非手写集合。

**直观例子：** 系统已经有 ny_futures 市场，但生成前端支持周期时忘记把它并入集合。

#### 2. 影响分析

当前默认配置主要是代码与能力声明不一致，而非已发生的前端缺项；未来新增 NY 期货独有秒线/周期时，TradingView 全局 supported_resolutions 会遗漏它。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 参数化所有 Market，断言每个市场 support key 都包含于全局 UDF resolution；增加一个只属于 ny_futures 的测试周期以防回归。 修改前测试应失败。
2. **实施修复：** 仍建议修复：把 ny_futures 纳入并集，最好由 MarketDescriptor 自动生成而非手写集合。
3. **执行回归验证：** 参数化所有 Market，断言每个市场 support key 都包含于全局 UDF resolution；增加一个只属于 ny_futures 的测试周期以防回归。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 仍建议修复：把 ny_futures 纳入并集，最好由 MarketDescriptor 自动生成而非手写集合。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 /tv/config 的周期并集仍没有 market_frequencys["ny_futures"]。

**原报告采用的排查方法：** 比较 market_frequencys、exchanges 和 tv_config union，并静态提取默认八个适配器的 support_frequencys keys 求集合差。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/__init__.py' 'src/tradingview_zy/exchange/exchange_tdx_ny_futures.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 结论基于 config.py.demo 默认适配器；用户自定义适配器可能已有独有周期。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`src/tradingview_zy/exchange/exchange_tdx_ny_futures.py（84-L98）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_tdx_ny_futures.py#L84-L98)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-11"></a>

### MX-11 · 配置模板暴露具体 IB 账户标识

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 最新 config.py.demo 仍包含具体 IB_ACCOUNT = 'DU6941075'。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 改为明显占位符/空值，并在启动时拒绝示例值。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/config.py.demo) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-11 · 配置模板暴露具体 IB 账户标识

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** IB 示例账号仍属于配置治理问题；当前 PR 没有证明示例值已移除或启动时被拒绝。
- **仍有什么问题 / 下一步：** 删除具体账号示例，使用明显占位符并增加示例值启动检查。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Configuration
- **来源：** 外部审查新增
- **标签：** 配置、外部 O-26

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 config.py.demo 仍包含具体 IB_ACCOUNT = 'DU6941075'。

**剩余工作：** 改为明显占位符/空值，并在启动时拒绝示例值。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** 示例中写死 `IB_ACCOUNT='DU6941075'`，不是通用占位符。

**正确行为应该是什么：** 改为明显占位符/空值，并在启动时拒绝示例值。

**直观例子：** 直观地看，这项问题意味着：可能泄露账户标识并诱导用户误用默认值；

#### 2. 影响分析

可能泄露账户标识并诱导用户误用默认值；但不能据此认定密钥或资金账户泄露。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** secret/config scanner 检测真实格式账号和默认凭据。 修改前测试应失败。
2. **实施修复：** 改为明显占位符/空值，并在启动时拒绝示例值。
3. **执行回归验证：** secret/config scanner 检测真实格式账号和默认凭据。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 改为明显占位符/空值，并在启动时拒绝示例值。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 config.py.demo 仍包含具体 IB_ACCOUNT = 'DU6941075'。

**原报告采用的排查方法：** 检查配置模板是否包含具体账户/环境标识，并区分秘密、示例值和可识别元数据。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/config.py.demo'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 配置和数据流可静态确认；实际暴露范围取决于部署访问控制、日志和外部服务。

**最新证据：**

- [`src/tradingview_zy/config.py.demo`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/config.py.demo) — IB 配置
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-07"></a>

### MX-07 · alert.js 七个列定义把 field 拼成 filed，字段元数据和排序绑定失效

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** alert.js 仅修改策略列标题等少量文本，七处 filed: 拼写仍存在。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 统一改为 field，并增加前端 lint/schema 测试；对可排序列在浏览器中验证排序请求/本地排序键。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/static/js/alert.js`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/static/js/alert.js) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-07 · alert.js 七个列定义把 field 拼成 filed，字段元数据和排序绑定失效

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 本轮没有系统修复 Layui 列配置中的 `filed` 拼写；相关页面仍可能忽略列字段。
- **仍有什么问题 / 下一步：** 改为 `field`，运行前端 lint，并为表格列渲染增加浏览器测试。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Frontend
- **来源：** 外部审查新增
- **标签：** 前端、外部 O-22

#### 当前状态与最新验证

**最新 master 验证结论：** alert.js 仅修改策略列标题等少量文本，七处 filed: 拼写仍存在。

**剩余工作：** 统一改为 field，并增加前端 lint/schema 测试；对可排序列在浏览器中验证排序请求/本地排序键。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** Layui table 的七个列配置使用 `filed` 而不是 `field`。由于每列 templet 直接读取 `d.frequency`、`d.interval_minutes` 等，常规渲染仍可能显示内容；错误主要破坏列字段元数据、默认数据绑定以及启用 sort 时的排序键。

**正确行为应该是什么：** 统一改为 field，并增加前端 lint/schema 测试；对可排序列在浏览器中验证排序请求/本地排序键。

**直观例子：** 字段名、长度或类型是模块间契约；一侧写错后，另一侧可能静默忽略或截断。

#### 2. 影响分析

任务列表未必为空，但排序、字段识别、导出或未来去掉 templet 后会失效，前端行为依赖实现细节。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 用真实 Layui 或浏览器测试渲染所有列并点击排序；静态测试禁止 `filed:`。 修改前测试应失败。
2. **实施修复：** 统一改为 field，并增加前端 lint/schema 测试
3. **实施修复：** 对可排序列在浏览器中验证排序请求/本地排序键。
4. **执行回归验证：** 用真实 Layui 或浏览器测试渲染所有列并点击排序；静态测试禁止 `filed:`。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 统一改为 field，并增加前端 lint/schema 测试；对可排序列在浏览器中验证排序请求/本地排序键。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** alert.js 仅修改策略列标题等少量文本，七处 filed: 拼写仍存在。

**原报告采用的排查方法：** 逐列检查配置键和 templet，区分字段元数据与自定义渲染路径。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/static/js/alert.js'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未加载真实 Layui 浏览器运行时；确切排序表现仍需 UI 测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/static/js/alert.js`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/static/js/alert.js)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-10"></a>

### MX-10 · 图表显示函数参数契约漂移

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（web/tradingview_zy_chart/cl_app/static/js/charts.js、web/tradingview_zy_chart/cl_app/templates/index.html）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 删除无效参数或让函数显式应用高度；用 TypeScript/JSDoc 固化签名。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/static/js/charts.js`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/static/js/charts.js) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/templates/index.html`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/templates/index.html) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-10 · 图表显示函数参数契约漂移

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 原问题涉及的具体旧接口/数据契约没有出现在当前 PR 的修复清单中，也没有新增直接回归测试。
- **仍有什么问题 / 下一步：** 按照原始证据重新建立最小复现后再修复；在完成前保持未修复。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Frontend
- **来源：** 外部审查新增
- **标签：** 前端、规范、外部 O-25

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/static/js/charts.js、web/tradingview_zy_chart/cl_app/templates/index.html）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 删除无效参数或让函数显式应用高度；用 TypeScript/JSDoc 固化签名。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** `show_tv_chart(id)` 只接收一个参数，模板多处传入 height，第二参数被静默丢弃。

**正确行为应该是什么：** 删除无效参数或让函数显式应用高度；用 TypeScript/JSDoc 固化签名。

**直观例子：** 直观地看，这项问题意味着：当前 CSS 可能掩盖问题，但调用方误以为高度可配置，后续重构易产生布局回归。

#### 2. 影响分析

当前 CSS 可能掩盖问题，但调用方误以为高度可配置，后续重构易产生布局回归。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 多布局截图测试验证实际高度。 修改前测试应失败。
2. **实施修复：** 删除无效参数或让函数显式应用高度
3. **实施修复：** 用 TypeScript/JSDoc 固化签名。
4. **执行回归验证：** 多布局截图测试验证实际高度。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 删除无效参数或让函数显式应用高度；用 TypeScript/JSDoc 固化签名。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/static/js/charts.js、web/tradingview_zy_chart/cl_app/templates/index.html）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 JavaScript 作用域、事件初始化顺序、定时器回调、Layui 字段配置、DOM 拼接和函数实参与签名；需要时用 node 语法检查和浏览器契约推演。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/static/js/charts.js' 'web/tradingview_zy_chart/cl_app/templates/index.html'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/static/js/charts.js（207-L213）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/static/js/charts.js#L207-L213) — 函数签名
- [`web/tradingview_zy_chart/cl_app/templates/index.html（604-L649）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/index.html#L604-L649) — 调用
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-09"></a>

### NX-09 · 未实现的 fee_us() 作为公开函数残留，但仓库内未发现调用方

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/backtesting/base.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 无兼容需求则删除；否则抛 NotImplementedError 或实现数据驱动费率。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/backtesting/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/base.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-09 · 未实现的 fee_us() 作为公开函数残留，但仓库内未发现调用方

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Backtesting Fees
- **来源：** 本次补充排查新发现
- **标签：** 正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/base.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 无兼容需求则删除；否则抛 NotImplementedError 或实现数据驱动费率。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分属于回测引擎。回测会按照历史 K 线模拟下单、持仓、现金和绩效指标；任何日期、数量、成本、手续费或年化公式错误都会沿后续计算持续放大。

**当前/原始错误行为：** `fee_us()` 直接 pass，参数名还拼成 amlunt。固定分支搜索未发现仓库内调用方，因此更像误导性的死 API，而不是当前主路径确定故障；外部私有调用方仍可能使用。

**正确行为应该是什么：** 无兼容需求则删除；否则抛 NotImplementedError 或实现数据驱动费率。

**直观例子：** 直观地看，这项问题意味着：外部调用得到 None；

#### 2. 影响分析

外部调用得到 None；维护者误以为费用模型已实现。当前仓库主路径影响有限。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 确认外部消费者后删除；若保留，调用必须返回费用或明确 Unsupported。 修改前测试应失败。
2. **实施修复：** 无兼容需求则删除
3. **实施修复：** 否则抛 NotImplementedError 或实现数据驱动费率。
4. **执行回归验证：** 确认外部消费者后删除；若保留，调用必须返回费用或明确 Unsupported。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 无兼容需求则删除；否则抛 NotImplementedError 或实现数据驱动费率。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/backtesting/base.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查公开费用函数实现和全仓调用图，区分未实现 API 与当前可达路径。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/base.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 公式和状态更新位置可静态/最小算例确认；未用真实历史数据做大样本回归，影响规模需黄金基准测试。

**最新证据：**

- [`src/tradingview_zy/backtesting/base.py（315-L334）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/base.py#L315-L334)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-18"></a>

### NX-18 · zixuan.js 的 templet 未声明，泄漏为全局变量

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（web/tradingview_zy_chart/cl_app/static/js/zixuan.js）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 块级 `const templet` 或表达式返回。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/static/js/zixuan.js`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/static/js/zixuan.js) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-18 · zixuan.js 的 templet 未声明，泄漏为全局变量

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 当前 PR 没有提供该条原始问题的直接关闭证明。
- **仍有什么问题 / 下一步：** 重新核对原证据和当前调用图，完成实现与动态测试后再关闭。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Frontend
- **来源：** 本次补充排查新发现
- **标签：** 规范

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/static/js/zixuan.js）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 块级 `const templet` 或表达式返回。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分位于 Web 管理端。浏览器提交的参数、Cookie、页面文本和上传文件都属于不可信输入，服务端必须先校验、授权和限流，再调用数据库、策略或行情接口。

**当前/原始错误行为：** 分支中直接赋值 `templet = ...`，没有 let/const/var。

**正确行为应该是什么：** 块级 `const templet` 或表达式返回。

**直观例子：** 直观地看，这项问题意味着：多个异步渲染可能互相覆盖，全局命名污染；

#### 2. 影响分析

多个异步渲染可能互相覆盖，全局命名污染；严格模式下直接 ReferenceError。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 启用 ESLint no-undef/strict mode。 修改前测试应失败。
2. **实施修复：** 块级 `const templet` 或表达式返回。
3. **执行回归验证：** 启用 ESLint no-undef/strict mode。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 块级 `const templet` 或表达式返回。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/static/js/zixuan.js）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查 JavaScript 作用域、事件初始化顺序、定时器回调、Layui 字段配置、DOM 拼接和函数实参与签名；需要时用 node 语法检查和浏览器契约推演。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/static/js/zixuan.js'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 请求/DOM/JavaScript 路径可静态确认；未运行真实 TradingView/Layui 浏览器和反向代理，具体 UI、CSP、并发及代理限额需动态测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/static/js/zixuan.js（17-L35）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/static/js/zixuan.js#L17-L35) — 隐式全局
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-17"></a>

### NX-17 · TradingView UDF 把所有市场 session 声明为 24x7，并把 FX 类型标成 stock

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 最新 Web 文件仍把所有市场 session 写为 24x7，FX 类型仍为 stock。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type；FX 使用符合 UDF 的 forex 类型。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-17 · TradingView UDF 把所有市场 session 声明为 24x7，并把 FX 类型标成 stock

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 确定
- **领域：** Web UDF
- **来源：** 本次补充排查新发现
- **标签：** 正确性

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 Web 文件仍把所有市场 session 写为 24x7，FX 类型仍为 stock。

**剩余工作：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type；FX 使用符合 UDF 的 forex 类型。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这项问题涉及项目中的一个运行或维护边界。理解它时，需要同时看当前代码做了什么、调用方期待什么，以及失败后系统会如何反馈。

**当前/原始错误行为：** market_session 对 A/HK/US/期货等全部返回 24x7，market_types 把 fx 标成 stock；这些值进入 /tv/search 和 /tv/symbols 的元数据。

**正确行为应该是什么：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type；FX 使用符合 UDF 的 forex 类型。

**直观例子：** 直观地看，这项问题意味着：图表可能错误处理交易时段空白、日界线、倒计时或品种分类；

#### 2. 影响分析

图表可能错误处理交易时段空白、日界线、倒计时或品种分类；K 线数据本身仍由后端返回，不能据此推断交易执行按 24x7。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 逐市场快照测试 /tv/search 和 /tv/symbols；用浏览器验证闭市空白区、日界线和品种分类。 修改前测试应失败。
2. **实施修复：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type
3. **实施修复：** FX 使用符合 UDF 的 forex 类型。
4. **执行回归验证：** 逐市场快照测试 /tv/search 和 /tv/symbols；用浏览器验证闭市空白区、日界线和品种分类。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 由市场描述符/交易日历生成 TradingView session、timezone 和 type；FX 使用符合 UDF 的 forex 类型。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 Web 文件仍把所有市场 session 写为 24x7，FX 类型仍为 stock。

**原报告采用的排查方法：** 沿 market_session/market_types 映射进入 /tv/search 与 symbol info 响应，和各交易所真实会话及 UDF 类型约定比较。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未运行真实 TradingView 浏览器组件；后端返回值确定，具体视觉影响待 UI 测试。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

## 严重程度：低 · 可信度：高

</details>

## 严重程度：低 · 可信度：高

</details>

## 严重程度：低 · 可信度：高

<a id="LO-02"></a>

### LO-02 · TDX/US/同步适配器存在大段复制（Duplicated Code）

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** TDX、US 历史适配器和同步脚本仍包含重复的分页、日期解析、缓存与重试代码；PR #15 只新增注册表/领域边界，没有提取这些重复实现。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 提取共享分页器、日期解析、Kline normalizer、缓存与 deadline 策略，用 provider contract tests 固定差异点。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_tdx.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx.py) — TDX 适配器实现
- [`src/tradingview_zy/exchange/exchange_tdx_hk.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_hk.py) — 港股 TDX 复制路径
- [`src/tradingview_zy/exchange/exchange_tdx_us.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_tdx_us.py) — 美股 TDX 复制路径
- [`src/tradingview_zy/exchange/exchange_alpaca.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_alpaca.py) — US 历史适配器重复逻辑

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-02 · TDX/US/同步适配器存在大段复制（Duplicated Code）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 日期解析、分页和部分缓存逻辑已复用，但 TDX/Binance/US 多个适配器仍有重复代码。
- **仍有什么问题 / 下一步：** 提取共享分页器、标准化器和 adapter contract，避免同类缺陷成组回归。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Maintainability
- **来源：** 双方
- **工作量：** XL
- **标签：** 规范、外部 O-13

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（相关实现文件）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 提取分页器、缓存策略、Kline normalizer、calendar 和 provider-specific 小适配层；用 contract tests 约束。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** TDX HK/US/FX/Futures/NY、Alpaca/Polygon、币安合约/现货和多份同步脚本重复分页、时间、缓存和 Tick 映射，缺陷因此成组出现。

**正确行为应该是什么：** 提取分页器、缓存策略、Kline normalizer、calendar 和 provider-specific 小适配层；用 contract tests 约束。

**直观例子：** 分页游标必须严格向前移动；若下一页仍从同一边界开始，就可能重复、停滞或漏数据。

#### 2. 影响分析

修复一个市场容易遗漏其他市场，形成行为漂移。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 共享测试套件在所有实现上运行。 修改前测试应失败。
2. **实施修复：** 提取分页器、缓存策略、Kline normalizer、calendar 和 provider-specific 小适配层
3. **实施修复：** 用 contract tests 约束。
4. **执行回归验证：** 共享测试套件在所有实现上运行。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 提取分页器、缓存策略、Kline normalizer、calendar 和 provider-specific 小适配层；用 contract tests 约束。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（相关实现文件）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 按文件职责、重复代码和修改原因检查 Fowler 坏味道；这是工程判断，不作为确定性运行失败。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-06"></a>

### LO-06 · 大量短变量、宽泛异常和 wildcard import 降低可审计性（Mysterious Name）

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ❌ 未修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 当前 master 的相关实现路径（src/tradingview_zy/exchange/exchange_alpaca.py）仍保留 V6 已确认的错误模式；PR #15 未提供能够消除根因的实现或专项测试。
- **判定依据：** 从 V6 快照到当前 master 未发现消除根因的实现或专项测试，状态保持未修复。
- **仍有什么问题 / 下一步：** 显式 import；领域命名；窄异常；结构化日志包含 market/code/request_id；启用 lint 规则 F403/F405/BLE001。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/exchange/exchange_alpaca.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/exchange_alpaca.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-06 · 大量短变量、宽泛异常和 wildcard import 降低可审计性（Mysterious Name）

- **最新状态：** ❌ **未修复**
- **为什么这样判断：** 当前修改没有系统清理 wildcard import、短变量和宽泛 Exception；静态类型/lint 门禁也未完整启用。
- **仍有什么问题 / 下一步：** 启用 ruff/pyright 渐进门禁，显式 import 并收窄异常。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Readability
- **来源：** 此前审查
- **工作量：** M
- **标签：** 规范

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_alpaca.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 显式 import；领域命名；窄异常；结构化日志包含 market/code/request_id；启用 lint 规则 F403/F405/BLE001。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** _t/_d/_mmd/_ks 等跨长函数使用；except Exception 后 print/continue 很常见；部分适配器 import * 隐式带入 datetime/pytz 等名称。

**正确行为应该是什么：** 显式 import；领域命名；窄异常；结构化日志包含 market/code/request_id；启用 lint 规则 F403/F405/BLE001。

**直观例子：** 直观地看，这项问题意味着：隐藏依赖、误用变量和异常吞噬更难被代码审查发现。

#### 2. 影响分析

隐藏依赖、误用变量和异常吞噬更难被代码审查发现。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** ruff/pyright 门禁。 修改前测试应失败。
2. **实施修复：** 显式 import
3. **实施修复：** 领域命名
4. **实施修复：** 窄异常
5. **实施修复：** 结构化日志包含 market/code/request_id
6. **实施修复：** 启用 lint 规则 F403/F405/BLE001。
7. **执行回归验证：** ruff/pyright 门禁。 同时运行相邻模块测试。
8. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 显式 import；领域命名；窄异常；结构化日志包含 market/code/request_id；启用 lint 规则 F403/F405/BLE001。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（src/tradingview_zy/exchange/exchange_alpaca.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 统计 wildcard import、宽泛异常、短变量和隐式名称来源，并结合静态检查可发现性评估。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/exchange/exchange_alpaca.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`src/tradingview_zy/exchange/exchange_alpaca.py（1-L14）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/exchange/exchange_alpaca.py#L1-L14)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-16"></a>

### MX-16 · 存在未加载的 ai.js 和完全 no-op 的 OtherTasks

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复（通过移除不支持/失效能力）
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** ai.js 仍是未加载/不可用桩，OtherTasks.run_task() 仍为 pass；能力边界没有删除或实现。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 删除无效资产和任务壳，或实现后显式注册、展示与测试。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/static/js/ai.js`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/static/js/ai.js) — AI 前端桩
- [`web/tradingview_zy_chart/cl_app/other_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/other_tasks.py) — no-op 任务实现

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-16 · 存在未加载的 ai.js 和完全 no-op 的 OtherTasks

- **最新状态：** ✅ **已修复（通过移除不支持/失效能力）**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Dead Code
- **来源：** 外部审查新增
- **标签：** 死代码、外部 O-47、外部 O-52

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/templates/index.html、web/tradingview_zy_chart/cl_app/other_tasks.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** 确认无外部模板后删除 ai.js；移除 OtherTasks 或恢复真实职责和测试。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 主模板未加载 ai.js；OtherTasks.run_task 的全部逻辑被注释，只剩 pass，app 仍创建懒加载代理。

**正确行为应该是什么：** 确认无外部模板后删除 ai.js；移除 OtherTasks 或恢复真实职责和测试。

**直观例子：** 直观地看，这项问题意味着：增加静态体积和错误认知，维护者可能误以为功能存在。

#### 2. 影响分析

增加静态体积和错误认知，维护者可能误以为功能存在。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 静态资源引用图和 app factory smoke test。 修改前测试应失败。
2. **实施修复：** 确认无外部模板后删除 ai.js
3. **实施修复：** 移除 OtherTasks 或恢复真实职责和测试。
4. **执行回归验证：** 静态资源引用图和 app factory smoke test。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 确认无外部模板后删除 ai.js；移除 OtherTasks 或恢复真实职责和测试。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（web/tradingview_zy_chart/cl_app/templates/index.html、web/tradingview_zy_chart/cl_app/other_tasks.py）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 结合全仓静态引用、模板加载、工厂分支和入口脚本检查 pass/墓碑/未加载资源；零内部引用不等于无外部消费者。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/templates/index.html' 'web/tradingview_zy_chart/cl_app/other_tasks.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/templates/index.html（300-L315）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/templates/index.html#L300-L315) — 实际 JS 列表
- [`web/tradingview_zy_chart/cl_app/other_tasks.py（1-L42）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/other_tasks.py#L1-L42) — no-op
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-18"></a>

### MX-18 · StrategySignal 与 Operation 是两套独立协议，跨选股/监控/回测复用需要手工转换（架构债务）

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 删除架构文档没有合并协议；StrategySignal 与 Operation 两套模型仍独立存在。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议；没有该需求时，应在文档中明确边界而不是强行统一。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/strategies/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/strategies/base.py) — 当前实现路径
- [`src/tradingview_zy/backtesting/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/backtesting/base.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-18 · StrategySignal 与 Operation 是两套独立协议，跨选股/监控/回测复用需要手工转换（架构债务）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** StrategySignal 校验已加强，但回测 Operation 与监控 StrategySignal 仍是两套协议，尚无正式双向转换。
- **仍有什么问题 / 下一步：** 定义明确转换器或明确禁止跨域复用，并用 contract tests 固定。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Strategy Architecture
- **来源：** 外部审查新增
- **标签：** 需求、架构、外部 O-32

#### 当前状态与最新验证

**最新 master 验证结论：** 删除架构文档没有合并协议；StrategySignal 与 Operation 两套模型仍独立存在。

**剩余工作：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议；没有该需求时，应在文档中明确边界而不是强行统一。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责定时运行选股或监控策略。任务配置必须可验证、调度周期必须准确、重复运行要幂等，单个标的失败也不能悄悄伪装成整批成功。

**当前/原始错误行为：** Selection/Monitoring 消费 StrategySignal，BackTest/Trader 消费 Operation，仓库没有正式版本化转换层。代码事实明确，但是否必须统一属于产品和架构选择；现有手册已经提示调用者自行编写转换。

**正确行为应该是什么：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议；没有该需求时，应在文档中明确边界而不是强行统一。

**直观例子：** 直观地看，这项问题意味着：复用同一策略时，调用方需要自行解释方向、仓位、时间和风控，增加行为漂移概率；

#### 2. 影响分析

复用同一策略时，调用方需要自行解释方向、仓位、时间和风控，增加行为漂移概率；但不意味着当前各自场景必然运行错误。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 用同一业务规则分别走选股、监控、纸交易和回测，验证转换后的事件、方向和仓位可追溯；同时允许只实现单一场景的策略。 修改前测试应失败。
2. **实施修复：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议
3. **实施修复：** 没有该需求时，应在文档中明确边界而不是强行统一。
4. **执行回归验证：** 用同一业务规则分别走选股、监控、纸交易和回测，验证转换后的事件、方向和仓位可追溯；同时允许只实现单一场景的策略。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 在确有跨场景复用需求时修复：定义 Signal→Decision→Order 管线和版本化转换协议；没有该需求时，应在文档中明确边界而不是强行统一。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 删除架构文档没有合并协议；StrategySignal 与 Operation 两套模型仍独立存在。

**原报告采用的排查方法：** 比较 strategies/base.py 的 StrategySignal、backtesting/base.py 的 Operation 及两类 runner/交易器调用点，再对照架构手册对当前边界的明确说明。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/strategies/base.py' 'src/tradingview_zy/backtesting/base.py' 'docs/architecture-and-development-guide.md'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 属于架构权衡；修复优先级取决于是否计划让同一策略跨场景复用。

**最新证据：**

- [`src/tradingview_zy/strategies/base.py（11-L42）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/strategies/base.py#L11-L42)
- [`src/tradingview_zy/backtesting/base.py（113-L156）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/base.py#L113-L156)
- [`docs/architecture-and-development-guide.md（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="NX-11"></a>

### NX-11 · 通用监控事件继续复用旧短字符串列，当前值可容纳但扩展空间受限

- **V7 状态：** ❌ 未修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 策略加载改为注册表不改变监控事件数据库列长度；event_type/action/score 仍复用旧短字符串列。
- **判定依据：** V6 顶层状态与其展开历史证据或当前源码不一致；V7 按实际代码纠正为未修复。这是报告误标纠正，不是代码回归。
- **仍有什么问题 / 下一步：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/strategies/base.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/strategies/base.py) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/alert_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/alert_tasks.py) — 当前实现路径
- [`src/tradingview_zy/db.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/db.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### NX-11 · 通用监控事件继续复用旧短字符串列，当前值可容纳但扩展空间受限

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Database Schema
- **来源：** 本次补充排查新发现
- **标签：** 数据完整性

#### 当前状态与最新验证

**最新 master 验证结论：** 策略加载改为注册表不改变监控事件数据库列长度；event_type/action/score 仍复用旧短字符串列。

**剩余工作：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这部分负责把任务、行情、图表和自选数据持久化。ORM 模型、唯一约束、过滤条件和事务边界必须与业务主键一致，否则数据可能重复、误删或只写入一半。

**当前/原始错误行为：** event_type 映射 String(5)，action/score 映射 String(10)。当前 event_type 固定为 "sig"，StrategyAction 最长值和截到 10 字符的 score 均可容纳，所以“当前必然截断”不成立；未来扩展仍会遇到后端差异。

**正确行为应该是什么：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。

**直观例子：** 直观地看，这项问题意味着：当前风险低；

#### 2. 影响分析

当前风险低；未来更长事件类型或外部策略值可能在 MySQL 被拒绝/截断，旧字段名也混淆语义。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 当前动作全部往返；超长非法值在应用边界被拒绝。 修改前测试应失败。
2. **实施修复：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。
3. **执行回归验证：** 当前动作全部往返；超长非法值在应用边界被拒绝。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 迁移为独立 event_type/action Enum 和数值 score，并在策略边界验证。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 策略加载改为注册表不改变监控事件数据库列长度；event_type/action/score 仍复用旧短字符串列。

**原报告采用的排查方法：** 沿业务对象到兼容 property 和物理列类型检查长度、枚举范围、唯一键及 SQLite/MySQL 差异。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/strategies/base.py' 'web/tradingview_zy_chart/cl_app/alert_tasks.py' 'src/tradingview_zy/db.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 模型、过滤条件和事务位置已核对，并对可隔离部分使用 SQLite 最小复现；真实 MySQL SQL mode、迁移和并发仍需双后端测试。

**最新证据：**

- [`src/tradingview_zy/strategies/base.py（11-L34）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/strategies/base.py#L11-L34)
- [`web/tradingview_zy_chart/cl_app/alert_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/alert_tasks.py)
- [`src/tradingview_zy/db.py（113-L147）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/db.py#L113-L147)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

## 新发现问题

</details>

## 严重程度：中 · 可信度：高

<a id="LO-05"></a>

### LO-05 · 新增市场需要跨枚举、配置、工厂、DB、UDF、模板和脚本散改（Shotgun Surgery）

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** MarketRegistry 已集中配置属性、时区、TradingView 类型/session、默认代码、provider、能力和 DB 分区；Exchange 工厂与 DB 路由已接入。Web UDF、模板和若干脚本仍有独立市场映射。
- **判定依据：** Shotgun Surgery 的核心市场工厂/DB 部分显著收敛，但未成为全栈唯一来源，故部分修复。
- **仍有什么问题 / 下一步：** 让 UDF/config、页面和脚本消费注册表，并删除重复映射；新增市场用单一注册+穷尽测试验收。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 市场单一注册表
- [`src/tradingview_zy/exchange/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/exchange/__init__.py) — 注册表驱动工厂
- [`tests/test_v6_market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_market_registry.py) — 穷尽性测试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-05 · 新增市场需要跨枚举、配置、工厂、DB、UDF、模板和脚本散改（Shotgun Surgery）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** MarketRegistry 已成为主要能力来源，但少数配置、DB 表和模板仍有市场分支。
- **仍有什么问题 / 下一步：** 新增“添加测试市场只改 descriptor”的架构测试，消除剩余重复 switch。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Architecture
- **来源：** 双方
- **工作量：** XL
- **标签：** 规范、外部 O-15

#### 当前状态与最新验证

**最新 master 验证结论：** HI-07 在一个局部使用 Market 显式映射，但市场能力仍散布在配置、工厂、DB、UDF 和模板。

**剩余工作：** 单一 MarketDescriptor 注册表生成配置校验、工厂、UDF、时区、类型和 DB 路由。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 仓库规范明确提醒新增市场需同步检查多处；当前 ny_futures 遗漏正是该结构的结果。

**正确行为应该是什么：** 单一 MarketDescriptor 注册表生成配置校验、工厂、UDF、时区、类型和 DB 路由。

**直观例子：** 直观地看，这项问题意味着：能力映射持续漂移，新增适配器风险高。

#### 2. 影响分析

能力映射持续漂移，新增适配器风险高。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 新增测试市场只改一个 descriptor，所有映射自动可见。 修改前测试应失败。
2. **实施修复：** 单一 MarketDescriptor 注册表生成配置校验、工厂、UDF、时区、类型和 DB 路由。
3. **执行回归验证：** 新增测试市场只改一个 descriptor，所有映射自动可见。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 单一 MarketDescriptor 注册表生成配置校验、工厂、UDF、时区、类型和 DB 路由。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** HI-07 在一个局部使用 Market 显式映射，但市场能力仍散布在配置、工厂、DB、UDF 和模板。

**原报告采用的排查方法：** 统计新增市场需要修改的枚举、配置、工厂、DB、Web 和模板位置，并用现有漏项验证散改风险。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'CLAUDE.md' 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`CLAUDE.md（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-07"></a>

### LO-07 · 保留多处 pass/旧桩/历史任务壳，能力边界不清（Speculative Generality）

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** 清理提交删除了 cl_myquant/cl_vnpy/cl_wtpy 和旧 trader 墓碑脚本，减少了一批历史桩。但 tradingview_zy.monitor、other_tasks.py、部分 Exchange 不支持方法和其他 pass/RuntimeError 桩仍在，能力边界仍不清楚。
- **判定依据：** V6 已记录部分缓解；最新 master 未出现足以关闭全部根因的新增证据，状态保持部分修复。
- **仍有什么问题 / 下一步：** 从能力注册表移除未实现能力；真正需要兼容的入口使用单一、可测试的 Unsupported 错误，不再散布空桩。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/other_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/other_tasks.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-07 · 保留多处 pass/旧桩/历史任务壳，能力边界不清（Speculative Generality）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 旧 trader、CTP、ZB、OtherTasks 和未加载 JS 已清理，但部分 pass/RuntimeError 桩仍存在。
- **仍有什么问题 / 下一步：** 删除无调用方桩，保留的能力统一返回 UnsupportedCapabilityError。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Dead Code
- **来源：** 双方
- **工作量：** M
- **标签：** 规范、需求、外部 O-38、外部 O-45、外部 O-52

#### 当前状态与最新验证

**最新 master 验证结论：** 清理提交删除了 cl_myquant/cl_vnpy/cl_wtpy 和旧 trader 墓碑脚本，减少了一批历史桩。但 tradingview_zy.monitor、other_tasks.py、部分 Exchange 不支持方法和其他 pass/RuntimeError 桩仍在，能力边界仍不清楚。

**剩余工作：** 从能力注册表移除未实现能力；真正需要兼容的入口使用单一、可测试的 Unsupported 错误，不再散布空桩。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** other_tasks、monitor 旧桩、部分交易所抽象方法、旧 trader/crontab 提示脚本与仍可执行旧目录并存。

**正确行为应该是什么：** 未实现能力从注册表删除；需要保留的桩返回结构化 Unsupported；历史代码全部 archive。

**直观例子：** 直观地看，这项问题意味着：UI/文档难判断“未实现”还是“暂不可用”，维护者可能误接入。

#### 2. 影响分析

UI/文档难判断“未实现”还是“暂不可用”，维护者可能误接入。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 能力声明与可调用实现一一对应。 修改前测试应失败。
2. **实施修复：** 未实现能力从注册表删除
3. **实施修复：** 需要保留的桩返回结构化 Unsupported
4. **实施修复：** 历史代码全部 archive。
5. **执行回归验证：** 能力声明与可调用实现一一对应。 同时运行相邻模块测试。
6. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 从能力注册表移除未实现能力；真正需要兼容的入口使用单一、可测试的 Unsupported 错误，不再散布空桩。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 清理提交删除了 cl_myquant/cl_vnpy/cl_wtpy 和旧 trader 墓碑脚本，减少了一批历史桩。但 tradingview_zy.monitor、other_tasks.py、部分 Exchange 不支持方法和其他 pass/RuntimeError 桩仍在，能力边界仍不清楚。

**原报告采用的排查方法：** 结合全仓静态引用、模板加载、工厂分支和入口脚本检查 pass/墓碑/未加载资源；零内部引用不等于无外部消费者。

**可自行执行的复核命令：** `rg -n "\bpass\b|Legacy Chanlun runtime module removed|RuntimeError" src/tradingview_zy web/tradingview_zy_chart/cl_app`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`遗留清理提交`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 删除一批历史适配与墓碑
- [`仍存在的 monitor 桩`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/monitor.py) — RuntimeError shim
- [`仍存在的 OtherTasks`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/other_tasks.py) — no-op/pass
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-08"></a>

### LO-08 · 文档、测试现状和遗留授权描述存在漂移

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** CLAUDE.md、旧架构/迁移文档、PyArmor 授权说明、setup.py 许可证冲突和三个旧适配目录已清理，文档漂移明显减少。但 check_env.py 的 Python 版本/环境结论仍与 pyproject 不一致，joinquant/ 仍是活跃根目录遗留，README 对部分能力的支持边界仍需校准。
- **判定依据：** V6 已记录部分缓解；最新 master 未出现足以关闭全部根因的新增证据，状态保持部分修复。
- **仍有什么问题 / 下一步：** 修复 check_env 契约；处理 joinquant；建立由能力注册表和 CI 自动生成/校验的支持矩阵。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`check_env.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/check_env.py) — 环境检查实现

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-08 · 文档、测试现状和遗留授权描述存在漂移

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** 文档和不支持能力已清理，支持矩阵更一致；但尚未由能力注册表自动生成，仍有漂移可能。
- **仍有什么问题 / 下一步：** 从 MarketRegistry/CapabilityRegistry 生成 README 支持矩阵并在 CI 校验。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** 🟡 **部分修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Documentation
- **来源：** 双方
- **工作量：** S
- **标签：** 规范、需求、外部 O-31、外部 O-35、外部 O-36

#### 当前状态与最新验证

**最新 master 验证结论：** CLAUDE.md、旧架构/迁移文档、PyArmor 授权说明、setup.py 许可证冲突和三个旧适配目录已清理，文档漂移明显减少。但 check_env.py 的 Python 版本/环境结论仍与 pyproject 不一致，joinquant/ 仍是活跃根目录遗留，README 对部分能力的支持边界仍需校准。

**剩余工作：** 修复 check_env 契约；处理 joinquant；建立由能力注册表和 CI 自动生成/校验的支持矩阵。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 文档称历史运行源码已归档，但运行树仍有旧目录；CLAUDE.md 称没有集中测试目录，而根目录实际存在 tests；check_env/依赖仍保留 pyarmor。旧版“未确认独立 LICENSE”是错误的：仓库根目录存在 LICENSE，GitHub 识别为 Apache-2.0。

**正确行为应该是什么：** 修正文档、移除或标注旧目录/pyarmor，让 README、架构手册和运行树一致。

**直观例子：** 直观地看，这项问题意味着：用户对支持范围、测试入口和授权要求形成错误预期；

#### 2. 影响分析

用户对支持范围、测试入口和授权要求形成错误预期；许可文件本身不存在缺失问题。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 当前只完成了部分修复，不能关闭该问题。应继续处理“剩余工作”，并在完成对应验证后再改为“已修复”。

1. **先写失败测试：** 文档链接、示例命令、运行树/支持矩阵自动比对；LICENSE 纳入打包。 修改前测试应失败。
2. **实施修复：** 修正文档、移除或标注旧目录/pyarmor，让 README、架构手册和运行树一致。
3. **执行回归验证：** 文档链接、示例命令、运行树/支持矩阵自动比对；LICENSE 纳入打包。 同时运行相邻模块测试。
4. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 修复 check_env 契约；处理 joinquant；建立由能力注册表和 CI 自动生成/校验的支持矩阵。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** CLAUDE.md、旧架构/迁移文档、PyArmor 授权说明、setup.py 许可证冲突和三个旧适配目录已清理，文档漂移明显减少。但 check_env.py 的 Python 版本/环境结论仍与 pyproject 不一致，joinquant/ 仍是活跃根目录遗留，README 对部分能力的支持边界仍需校准。

**原报告采用的排查方法：** 对照文档文本、仓库根树、实际测试/许可证/授权代码，确认现状描述是否一致。

**可自行执行的复核命令：** `rg -n "joinquant|环境OK|allow_version" README.md check_env.py joinquant`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`遗留清理提交`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 删除旧文档、PyArmor 和三套适配
- [`当前 check_env`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/check_env.py) — 版本与结论仍漂移
- [`当前 joinquant 遗留`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/joinquant/fun.py) — 仍在根目录
- [`LICENSE`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/LICENSE)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-03"></a>

### LO-03 · 市场、周期、订单状态和方向广泛使用裸字符串（Primitive Obsession）

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** 新增 Market、OrderSide、PositionSide、OrderStatus、Capability 等枚举/领域对象，市场解析和部分订单边界不再依赖裸字符串；大量旧模块仍使用 market/frequency/order 字符串。
- **判定依据：** PR #15 对核心边界有实质收敛，但全仓迁移未完成，因此保持部分修复。
- **仍有什么问题 / 下一步：** 逐步迁移旧适配器、Web 路由和数据库字段；在序列化边界统一转换。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/domain.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/domain.py) — 订单/能力领域类型
- [`src/tradingview_zy/market_registry.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/market_registry.py) — 统一 Market 解析
- [`tests/test_v6_domain_contracts.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_domain_contracts.py) — 领域不变量测试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-03 · 市场、周期、订单状态和方向广泛使用裸字符串（Primitive Obsession）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** Market 元数据集中化后减少了部分裸字符串，但订单方向、offset、频率和状态仍广泛使用字符串。
- **仍有什么问题 / 下一步：** 逐步引入 OrderSide/Offset/OrderStatus/Frequency 值对象并启用类型检查。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Domain Model
- **来源：** 双方
- **工作量：** L
- **标签：** 规范、外部 O-15、外部 O-16

#### 当前状态与最新验证

**最新 master 验证结论：** HI-07 消除了一个裸字符串列表错误，但全栈大量 market/frequency/order 字符串仍存在。

**剩余工作：** 使用 Market/Frequency/OrderSide/Offset/OrderStatus 值对象与解析器；DB 层保存稳定 code。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** "a"、"hk"、"open_long"、"5m" 等字符串在 Web、DB、回测、交易和脚本重复比较；拼写错误只能在运行时暴露。

**正确行为应该是什么：** 使用 Market/Frequency/OrderSide/Offset/OrderStatus 值对象与解析器；DB 层保存稳定 code。

**直观例子：** 直观地看，这项问题意味着：已出现 hk/futures 字符串拼接、close_long 落成 open_long 等错误。

#### 2. 影响分析

已出现 hk/futures 字符串拼接、close_long 落成 open_long 等错误。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 类型检查和非法值构造测试。 修改前测试应失败。
2. **实施修复：** 使用 Market/Frequency/OrderSide/Offset/OrderStatus 值对象与解析器
3. **实施修复：** DB 层保存稳定 code。
4. **执行回归验证：** 类型检查和非法值构造测试。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 使用 Market/Frequency/OrderSide/Offset/OrderStatus 值对象与解析器；DB 层保存稳定 code。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** HI-07 消除了一个裸字符串列表错误，但全栈大量 market/frequency/order 字符串仍存在。

**原报告采用的排查方法：** 检查重复裸字符串/字典参数及其已经导致的拼写、映射和字段漂移；作为设计债务评估。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'src/tradingview_zy/backtesting/backtest.py' 'src/tradingview_zy/trader/trader_futures.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`src/tradingview_zy/backtesting/backtest.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/backtesting/backtest.py)
- [`src/tradingview_zy/trader/trader_futures.py（52-L140）`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/src/tradingview_zy/trader/trader_futures.py#L52-L140)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-04"></a>

### LO-04 · OHLCV、订单和策略参数以重复 dict 传递（Data Clumps）

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 代码进展/完成修复
- **回归判定：** 否
- **最新结论：** 新增不可变 OrderRequest、Fill、OrderState 和严格 KlineFrame 边界，部分核心 dict 已被领域对象替代；旧适配器和策略参数仍广泛传 dict。
- **判定依据：** 数据团块问题得到实质但不完整的重构，标记部分修复。
- **仍有什么问题 / 下一步：** 按模块边界渐进迁移，不要求内部 DataFrame 全部对象化；优先交易/成交和外部 provider payload。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`src/tradingview_zy/domain.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/domain.py) — 订单/成交 dataclass
- [`src/tradingview_zy/kline_schema.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/src/tradingview_zy/kline_schema.py) — KlineFrame 协议
- [`tests/test_v6_domain_contracts.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/tests/test_v6_domain_contracts.py) — 领域对象测试

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-04 · OHLCV、订单和策略参数以重复 dict 传递（Data Clumps）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** StrategySignal、BatchRunResult 等已类型化，但 OHLCV、订单和适配器返回仍有大量 dict/DataFrame 隐式契约。
- **仍有什么问题 / 下一步：** 继续用 Kline/Fill/OrderRequest/InstrumentId schema 固定模块边界。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Domain Model
- **来源：** 双方
- **工作量：** L
- **标签：** 规范、外部 O-16

#### 当前状态与最新验证

**最新 master 验证结论：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（相关实现文件）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**剩余工作：** Kline、Fill、OrderRequest、InstrumentId、StrategyParams 使用 typed dataclass/schema；DataFrame 仅在批量边界使用。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** code/date/open/close/high/low/volume、price/amount/type/info、market/code/frequency 在多层以未验证 dict 反复出现。

**正确行为应该是什么：** Kline、Fill、OrderRequest、InstrumentId、StrategyParams 使用 typed dataclass/schema；DataFrame 仅在批量边界使用。

**直观例子：** 直观地看，这项问题意味着：字段名漂移、缺列和语义混淆只能在运行时发现。

#### 2. 影响分析

字段名漂移、缺列和语义混淆只能在运行时发现。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** schema round-trip 与静态类型检查。 修改前测试应失败。
2. **实施修复：** Kline、Fill、OrderRequest、InstrumentId、StrategyParams 使用 typed dataclass/schema
3. **实施修复：** DataFrame 仅在批量边界使用。
4. **执行回归验证：** schema round-trip 与静态类型检查。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** Kline、Fill、OrderRequest、InstrumentId、StrategyParams 使用 typed dataclass/schema；DataFrame 仅在批量边界使用。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 对比 306bde5f 与最新 e514d66e 后，本问题直接涉及的实现路径（相关实现文件）没有出现能够消除根因的修改；基线中确认的代码模式在最新 master 仍然成立，因此标记为未修复。

**原报告采用的排查方法：** 检查重复裸字符串/字典参数及其已经导致的拼写、映射和字段漂移；作为设计债务评估。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="LO-01"></a>

### LO-01 · Flask app factory 承担过多职责（Divergent Change）

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** 🟡 部分修复
- **状态变化：** 状态保持
- **回归判定：** 否
- **最新结论：** cl_app/__init__.py 继续集中认证、调度、UDF、存储、自选、监控和选股；文件职责没有拆分。
- **判定依据：** 相关路径在 PR #15 中有实质变化，但静态复核仍能定位到原问题的一部分，因此标记部分修复。
- **仍有什么问题 / 下一步：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分；依赖通过 app extensions 注入。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### LO-01 · Flask app factory 承担过多职责（Divergent Change）

- **最新状态：** 🟡 **部分修复**
- **为什么这样判断：** Web runtime 与安全模块已经拆出，但 cl_app/__init__.py 仍承担大量路由和领域职责。
- **仍有什么问题 / 下一步：** 继续按 auth/udf/storage/watchlist/tasks/health 拆分 Blueprint，并保持应用工厂无后台副作用。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Maintainability
- **来源：** 双方
- **工作量：** L
- **标签：** 规范、外部 O-17

#### 当前状态与最新验证

**最新 master 验证结论：** cl_app/__init__.py 继续集中认证、调度、UDF、存储、自选、监控和选股；文件职责没有拆分。

**剩余工作：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分；依赖通过 app extensions 注入。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** 单文件同时负责 scheduler、登录、市场能力、UDF、图表存储、自选、导入、监控、选股和错误降级，任何一个领域变化都修改同一模块。

**正确行为应该是什么：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分；依赖通过 app extensions 注入。

**直观例子：** 直观地看，这项问题意味着：审查困难、导入副作用多、测试隔离差、冲突率高。

#### 2. 影响分析

审查困难、导入副作用多、测试隔离差、冲突率高。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 每个 blueprint 可独立创建 test app，无网络和后台线程副作用。 修改前测试应失败。
2. **实施修复：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分
3. **实施修复：** 依赖通过 app extensions 注入。
4. **执行回归验证：** 每个 blueprint 可独立创建 test app，无网络和后台线程副作用。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 按 auth/udf/storage/watchlist/tasks/health 蓝图拆分；依赖通过 app extensions 注入。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** cl_app/__init__.py 继续集中认证、调度、UDF、存储、自选、监控和选股；文件职责没有拆分。

**原报告采用的排查方法：** 按文件职责、重复代码和修改原因检查 Fowler 坏味道；这是工程判断，不作为确定性运行失败。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 相关代码/文档结构真实存在；严重性和重构优先级属于工程或产品判断，外部私有消费者也需人工确认。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

<a id="MX-12"></a>

### MX-12 · Web app factory 保留旧模块专用降级分支，当前成为无覆盖的迁移残留

- **V7 状态：** 🟡 部分修复
- **V6 顶层状态：** ✅ 已修复
- **状态变化：** V6 误标纠正（非代码回归）
- **回归判定：** 否
- **最新结论：** 最新 create_app() 仍完整保留 _REMOVED_LEGACY_*、_UnavailableTasks 和 _LazyTasks。
- **判定依据：** 相关路径在 PR #15 中有实质变化，但静态复核仍能定位到原问题的一部分，因此标记部分修复。
- **仍有什么问题 / 下一步：** 清理旧模块专用判断；保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。
- **V7 固定点：** [`34884625`](https://github.com/zhangyu-ch/tradingview/commit/3488462529c6ec052192eb41d1a6b74c5718c58f)

#### 当前证据

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/__init__.py) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/alert_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/alert_tasks.py) — 当前实现路径
- [`web/tradingview_zy_chart/cl_app/xuangu_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/3488462529c6ec052192eb41d1a6b74c5718c58f/web/tradingview_zy_chart/cl_app/xuangu_tasks.py) — 当前实现路径

<details>
<summary><strong>展开 V6 原始记录（完整保留）</strong></summary>

### MX-12 · Web app factory 保留旧模块专用降级分支，当前成为无覆盖的迁移残留

- **最新状态：** ✅ **已修复**
- **为什么这样判断：** 当前 PR 已移除原根因，并由相关测试、删除证明或统一契约固定。
- **仍有什么问题 / 下一步：** 无需再次修改同一根因；保留现有回归测试和 fail-closed 边界，防止后续回退。
- **当前复核固定点：** [PR #11](https://github.com/zhangyu-ch/tradingview/pull/11)，基线 `e16418d1`。

#### 当前证据

- [当前综合 PR](https://github.com/zhangyu-ch/tradingview/pull/11) — 阶段性综合修复代码与讨论
- [基线到当前分支对比](https://github.com/zhangyu-ch/tradingview/compare/e16418d158a0d02688ad8e3a8dd36f09daca7605...agent/current-comprehensive-remediation) — 核对本条是否有直接代码变化

<details>
<summary><strong>展开 v5 原始问题信息（完整保留）</strong></summary>

- **当前修复状态：** ❌ **未修复**
- **历史严重程度：** 低
- **可信度：** 高
- **领域：** Architecture / Spec
- **来源：** 外部审查新增
- **标签：** 需求、规范、外部 O-34

#### 当前状态与最新验证

**最新 master 验证结论：** 最新 create_app() 仍完整保留 _REMOVED_LEGACY_*、_UnavailableTasks 和 _LazyTasks。

**剩余工作：** 清理旧模块专用判断；保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。

#### 1. 问题描述（面向刚接手项目的维护者）

**这部分代码负责什么：** 这属于工程治理和维护边界。它不一定立刻导致某一次请求报错，但会影响安装、升级、测试可信度、代码所有权和新成员判断哪些能力真的可用。

**当前/原始错误行为：** create_app 定义旧 import 前缀识别、_UnavailableTasks 和 _LazyTasks；当前三个任务模块均不依赖被删除的旧模块，因此专用旧模块判断在正常代码中没有触发源。它更接近迁移残留，而不是仍在工作的包兼容层。

**正确行为应该是什么：** 清理旧模块专用判断；保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。

**直观例子：** 直观地看，这项问题意味着：增加 app factory 复杂度，并可能在未来恰好匹配某些 ImportError 文本时把真实故障包装成笼统“旧模块已移除”；

#### 2. 影响分析

增加 app factory 复杂度，并可能在未来恰好匹配某些 ImportError 文本时把真实故障包装成笼统“旧模块已移除”；当前未证明它正在隐藏错误。

这不是单纯的代码风格问题：它会改变安全边界、业务数据、资金账本、绩效指标、运行可用性或维护者对能力状态的判断。

#### 3. 修复方式（按可执行步骤展开）

**是否建议修复：** 建议在重构或维护周期处理，并通过测试、静态检查或文档约束防止继续扩散。

1. **先写失败测试：** 对当前三类任务做 import failure 测试，错误原因原样可见；删除旧判断后现有 36 项测试仍通过。 修改前测试应失败。
2. **实施修复：** 清理旧模块专用判断
3. **实施修复：** 保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。
4. **执行回归验证：** 对当前三类任务做 import failure 测试，错误原因原样可见；删除旧判断后现有 36 项测试仍通过。 同时运行相邻模块测试。
5. **关闭条件：** 根因消失；错误路径可解释；正常、边界和异常值均被自动测试覆盖；必要时完成真实 SDK、数据库或浏览器集成测试。

**本轮之后仍需做什么：** 清理旧模块专用判断；保留通用 lazy loading 时，错误应携带真实模块、异常链和健康状态。

#### 4. 修复证明与自行复核方法

**验证固定点：** 最新 master `e514d66eb0c993d25d10286f001621d20c5b22ff`；原报告基线 `306bde5fcd43c21546e7ebba68c0ce1b722c9d64`。

**本轮判定规则：** 先比较两个提交的文件差异，再读取最新文件中的控制流、数据结构和测试。相关实现没有改变时，不能因为提交说明写了“修复”就标记已修复；只有根因被删除、替换或被自动测试明确覆盖时，才标记“已修复”。

**最新仓库检查结果：** 最新 create_app() 仍完整保留 _REMOVED_LEGACY_*、_UnavailableTasks 和 _LazyTasks。

**原报告采用的排查方法：** 检查 _REMOVED_LEGACY_* 匹配条件、三个任务模块的 import 图和 _LazyTasks 的异常分支，并对照一次性迁移设计。

**可自行执行的复核命令：** `git diff 306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff -- 'web/tradingview_zy_chart/cl_app/__init__.py' 'web/tradingview_zy_chart/cl_app/alert_tasks.py' 'web/tradingview_zy_chart/cl_app/xuangu_tasks.py'`

**如何判断命令结果：** 已修复问题应看到测试通过、旧文件不存在或旧错误模式不再出现；未修复问题应仍能在最新代码中找到相同控制流、字段、公式或缺失保护。

**证据限制：** 未来私有任务模块是否仍依赖旧模块无法从公开工作树判断。

**最新证据：**

- [`web/tradingview_zy_chart/cl_app/__init__.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/__init__.py)
- [`web/tradingview_zy_chart/cl_app/alert_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/alert_tasks.py)
- [`web/tradingview_zy_chart/cl_app/xuangu_tasks.py`](https://github.com/zhangyu-ch/tradingview/blob/e514d66eb0c993d25d10286f001621d20c5b22ff/web/tradingview_zy_chart/cl_app/xuangu_tasks.py)
- [`docs/superpowers/specs/2026-05-03-remove-chanlun-design.md（最新 master 已删除）`](https://github.com/zhangyu-ch/tradingview/commit/1ba12e935ec3c66dc119a934c12cea8b047bff7d) — 通过删除失效文件/文档处理
- [`306bde5f → e514d66e 代码对比`](https://github.com/zhangyu-ch/tradingview/compare/306bde5fcd43c21546e7ebba68c0ce1b722c9d64...e514d66eb0c993d25d10286f001621d20c5b22ff) — 本轮修复状态判定基线

</details>

</details>

## V1 维护规则

1. 修复某条问题时，不删除原记录；在后续版本更新状态、修复内容、测试结果和复查证据。
2. “已阻断或缓解”不能等同于“底层功能已修复”；只有根因消失并通过相应测试后才能关闭。
3. 真实外部系统相关问题必须保留集成验证边界，不能仅凭单元测试推断券商、交易所、数据库或浏览器行为。
4. 新发现问题继续使用 `NEW-xx` 编号；既有问题保持原编号，避免历史追踪断裂。

## 来源与验证边界

- 完整 V7 固定点：`3488462529c6ec052192eb41d1a6b74c5718c58f`。
- V7 记录的动态验证：PR #15 最终合并检查全部通过，项目测试 `172 passed`；依赖 warning baseline 通过。
- V7 记录的静态验证：Python compileall 通过；24 个第一方 JavaScript 文件 `node --check` 通过；并完成 3 个确定性最小复现。
- 未覆盖的真实环境仍包括 MySQL、真实浏览器与反向代理、多 worker、Redis 故障注入以及 IB/QMT/CTP/Futu/交易所沙箱。
