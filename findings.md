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

## CR-04 QMT 交易能力复核
- `QMTTraderStock` 没有仓库内启动器，但运行模块可被直接导入，因此“默认不可达”只能缓解风险，不能关闭未定义变量和假成功账本问题。
- 真实买入在 `price` 赋值前计算数量；下单查询未命中时仍可能继续；多个非成功条件会切换到模拟分支并写与真实交易共用的账本。
- QMT 行情 `ExchangeQMT` 与订单执行是两种能力。本轮只移除未验收的 live trader，保留行情 provider，避免为关闭交易漏洞而破坏现有行情用途。

## HI-06 CSRF 与写接口复核
- 应用此前没有 CSRF token 或来源校验；SameSite Cookie 只能作为纵深防御，不能替代写请求的请求意图证明。
- `/alert_del/<id>` 使用 GET，属于可被链接、预取或第三方页面触发的状态变更；本轮改为 POST 并同步前端调用。
- 修复采用统一 `before_request`，避免逐路由漏加：所有非安全方法都要求会话 token；提供 Origin/Referer 时还必须同源或进入显式可信列表。
- 旧前端混合使用 jQuery、fetch、原生 XHR 与 HTML form，因此单独只改 `$.ajax` 不足；`csrf.js` 对四种机制都注入同一 token。
- 初次批量补丁因 `alert.js` 预期文本标记不完全匹配而中止；已改为分文件稳定标记和断言，不再重复脆弱的一次性替换。

## CR-03 实盘订单状态机复核
- 当前运行树同时存在多种互不兼容的“成功”定义：A 股用本地 tick 直接落账，Futu 固定等待 5 秒后查一次，Binance 直接返回 create_order，TQ 循环改单后只返回最后订单字段，IB worker 等待 isDone；都没有统一持久化状态与重启对账。
- 仅删除启动器仍不够，因为 `Exchange.order()` 和各 provider 的撤单方法可以被外部脚本直接调用。
- 在没有真实账户与沙箱环境时，凭空补一个表面状态枚举会制造更危险的伪安全。本轮采用能力下线：统一抛 `LiveTradingDisabledError`，并删除 live trader 和 IB 下单 worker。
- 行情、账户只读接口、研究和回测不依赖实盘 order，因此保留；回测订单明确不等同于券商成交。
- 首次 AST 批量替换把 CRLF 文件统一写成 LF，导致无意义大 diff；已全部恢复到 HEAD，并用保留原换行符的读写方式重新应用，最终 diff 仅包含真实改动。

## ME-24 环境契约复核
- `pyproject.toml` 已固定 `>=3.11,<3.12`，但旧脚本维护另一份 3.8–3.11 白名单；版本检查必须从元数据单一来源读取。
- `telnetlib` 不是探测 TCP 端口所必需，且新 Python 已移除；改用 `socket.create_connection(..., timeout=3)` 并自动关闭。
- 可选代理/Redis 不可用应是 DEGRADED，配置为 MySQL 后连接失败或项目配置无法导入应是 FAILED；二者不能都在结尾伪装成“环境OK”。
- 当前容器 Python 3.13 正好形成真实失败样例：脚本返回 1，并明确指出不满足 `>=3.11,<3.12`。

## NEW-06 DB provider 能力声明复核
- 远程固定点的 `MarketRegistry` 不存在于用户上传的本地主代码；本地没有 Capability/DB_CAPABILITIES，因此不能把远程回归直接当成本地现状。
- `ExchangeDB.all_stocks()`、`stock_owner_plate()`、`plate_stocks()` 确实仍为空/未实现，但这表示“无能力”，不是“已过报能力”。
- 本条采用防回归处理：文档明确 DB 当前仅是 K 线/派生 tick 数据源；若以后加入 registry，测试会阻止 SECURITY_MASTER/PLATES 声明。
- 证券目录实现与统一能力模型分别留给 NX-23、ME-10，避免在本条混入另一项架构工作。

## HI-01 TraderFutures 复核
- CR-03 已删除 `trader_futures.py`，因此 `ExchangeTq(use_account=True)` 的 TypeError 和平多写成 `open_long` 的错误均不再可达。
- 仅记录“共享修复”还不够；新增独立扫描，防止未来从历史代码恢复 TraderFutures 时一起恢复旧构造和订单类型错误。
- 本条不恢复 TQ 实盘；恢复必须先满足统一 Order/Fill 与重启对账准入。

## ME-06 自选导入导出复核
- 固定 `zx.txt` 同时服务导入和导出，任何并发请求都可能覆盖或提前删除另一请求的文件。
- 导出无需落盘，改用 `BytesIO`；导入也无需保存，可直接对上传二进制流逐行解析。
- 限额分为 Flask 请求体上限、导入行数和单行字节；UTF-8 与扩展名异常返回明确 4xx。

## ME-16 IB Redis RPC 复核
- `BRPOP timeout=0` 是永久等待；worker 停止后调用线程没有任何返回路径。
- IB 请求已经有唯一 UUID 响应键，可直接作为 correlation ID；统一 RPC 同时负责有限 timeout、序列化、解码和 finally 清理。
- 客户端清理无法删除“超时后才被 worker 创建”的键，因此 worker 在 lpush 后补 120 秒 expire，限制迟到响应残留。

## ME-05 Web 启动复核
- create_app 原先为全部市场同步构造 provider，仅为读取周期和默认代码；这把外部网络/SDK副作用放进了应用工厂。
- Web 展示元数据可以静态描述，不需要实例化 provider；实际行情请求仍按市场惰性构造。
- 新元数据模块不导入 exchange 或第三方 SDK，避免测试创建 app 时启动网络与线程。

## MX-01 钉钉配置复核
- 配置模板从未定义 `DINGDING_KEY_*`，HK 分支又重复 `market == "a"`；这不是可用但小错的通道，而是已废弃且契约破裂的死能力。
- 全仓没有活动调用方，注释也说明旧 API 下架；因此删除比补一套未经使用和测试的秘密配置更安全。
- 飞书通道保持不变；未来新通道必须有明确 timeout、状态与秘密处理。

## MX-06 db.py 直接执行复核
- 文件末尾 demo 区不是测试框架，且唯一未注释调用会连接当前配置数据库并写固定标记。
- 删除整个 main demo 比逐行注释更可靠；生产 DB 类型与模块单例不受影响。

## MX-02 ZB provider 复核
- 配置模板把 `zb` 列为可选 provider，但标准工厂没有分支；这不是“实现已注册但失败”，而是支持声明与运行契约直接矛盾。
- 孤立 `ExchangeZB` 可被外部直接导入，并关闭 TLS 证书校验；仅从注释删掉 `zb` 仍会留下危险半成品。
- 本轮采用完整下线：删除适配器和密钥模板，旧配置在任何导入/缓存前明确失败；这也为后续 NX-25 提供共享根因修复。

## MX-04 DB trading state 复核
- `None` 在 Python 的 `is False` 分支中会继续执行，在 JSON/JavaScript 的 `!== true` 分支中会停止，不能作为隐式“未知”状态跨语言传递。
- DB provider 没有权威交易日历或实时 session feed；在尚未实现统一 calendar 前，明确 `False` 比把未知当开市更安全。
- 历史 K 线读取不依赖 now_trading；本变更只让近实时 history 限流、监控和自选轮询统一 fail-closed。

## MX-05 自选涨跌幅定时器复核
- 原模板两处把 `ZiXuan.stocks_update_rate()` 的立即返回值交给 `setInterval`，因此只执行一次，定时器没有可调用回调。
- 页面初始化与折叠面板重新打开还可能重复创建定时器；修复抽取 start/stop helper，启动前清理旧实例，先立即刷新一次，再传函数回调周期执行。
- 首次语法测试用跨标签正则从第一个内联脚本匹配到最后一个 `</script>`，把 HTML 标签送入 Node；已改为逐个提取无 `src` 的内联脚本。

## MX-17 TDX 节点选优复核
- 原 `select_best_ip` 用列表推导串行调用全部候选节点；冷缓存或显式 reset 的总耗时随候选数线性增长，且没有调用级总 deadline。
- 新选择器用有界数量 daemon worker 并发探测，调用方只等待一个全局 wall-clock deadline；单节点异常、畸形延迟或违反自身 socket timeout 都不会无限拖住选择调用。
- `tdx_connect_ip` 与共享 `tdxex_connect_ip` 现在写入 6 小时绝对过期时间，避免永久相信旧节点；过期后的同步重选仍受 3 秒总预算约束。

## NX-08 POSITION 输入副作用复核
- 最小复现确认 `get_close_profit(["uid-a"])` 返回后调用方列表变为 `["uid-a", "clear"]`；根因是私有查询方法直接 append。
- 查询只需要成员判断，不需要修改调用方顺序；修复在局部 set 副本上补 `clear`，重复调用与异常路径均不泄漏状态。
- 相邻综合回测测试在收集阶段因容器缺失 `empyrical` 被阻断；专项 POSITION 测试不依赖该库并覆盖正常、fallback、异常三条路径。

## NX-03 飞书配置共享状态复核
- `config_get_feishu_keys` 直接取得 `config.FEISHU_KEYS[market/default]` 的原字典，再写入 `user_id`；一次读取就会修改全局配置对象。
- 返回浅副本足以隔离当前扁平凭据结构；市场专用和 default 分支都先 `dict(source)`，数据库覆盖路径本来就构造新映射。
- 测试还修改返回值并再次读取，确认调用方后续变更和跨市场调用都不会回写或泄漏到全局配置。

## NX-22 数据库模块 warning 作用域复核
- `db.py` 在模块顶层调用 `warnings.filterwarnings("ignore")`，过滤器作用于整个 Python 进程，而不仅是数据库代码；后续 pandas、SQLAlchemy、弃用和业务警告都会被无差别吞掉。
- 该文件没有任何局部 warning 处理需求，删除 import 与全局调用即可恢复调用方策略；TDX 中针对单个 FutureWarning 的 `catch_warnings` 局部过滤不受影响。
- 子进程测试在导入前把 UserWarning 设为 error，并把 HOME 指向临时目录；容器缺少可选 tzlocal，测试仅提供返回 UTC 的兼容 stub，实际 DB/SQLAlchemy/SQLite 导入后 sentinel warning 仍抛出。

## NX-21 MySQL URL 构造复核
- 原代码把用户名、密码、主机、端口和数据库名直接拼入 DSN；`@`、`:`、`/`、`%`、空格等保留字符会被解析器误当作 URL 分隔符。
- SQLAlchemy `URL.create` 保留原始 credential 属性并在需要渲染时正确转义；默认字符串表示还会把密码替换为 `***`，降低异常日志泄密风险。
- 纯函数 `build_mysql_url` 让特殊字符 round-trip 可直接测试，DB 构造器只把结构化 URL 交给 `create_engine`。

## NX-23 DB provider 标的目录复核
- `ExchangeDB.all_stocks()` 原先无条件返回空列表，而同一 provider 能正常读写 K 线；搜索、自选导入和 `zx_group=all` 的选股因此把“已有数据”静默解释为“无标的”。
- K 线表按市场和代码/分组动态分区，可靠的兼容恢复方式是由 SQLAlchemy inspector 枚举当前市场前缀，再从真实 `code` 列读取 DISTINCT；反射 Table 让数据库方言负责安全引用表名。
- 新目录只描述数据库中实际出现过的代码，不能推导证券名称、上市状态或板块。文档保留这一边界，避免修复 NX-23 后重新制造 NEW-06 的能力过报。
- NEW-06 原防回归测试曾要求 `all_stocks()` 必须完全未实现；NX-23 后该断言不再准确。新的行为级门禁允许已存代码目录，但仍要求名称仅为 code fallback、板块方法未实现，且未来注册表不得声明权威主数据能力。
## NX-16 `/ticks` 扇出与等待边界复核
- 原路由在解析 JSON 后直接同步调用 provider，既没有原始代码数量/长度边界，也没有稳定去重、速率限制或调用级 deadline；这会把一个 Web 请求放大成无界外部扇出，并允许故障 provider 长期占用 worker。
- 数量限制必须在去重前检查，否则大量重复代码仍可消耗无界解析与循环成本；单代码按 UTF-8 字节限制，避免多字节文本绕过字符数阈值。
- Python 不能安全杀死任意阻塞 SDK 线程。修复采用固定并发槽加 daemon worker：请求按 deadline 返回，超时调用继续占用槽直到 SDK 返回；所有槽被占用时后续请求快速返回 503，而不是继续创建线程。
- 限流状态使用锁保护的滑动窗口，并对客户端键目录设置 LRU 上限；这解决单进程并发和状态增长，跨 worker 全局配额仍应由代理或共享存储实现。
- Web 主文件和配置模板保持原 CRLF；首次恢复补丁曾把文件规范化为 LF，已恢复 HEAD 后改用字节级替换并验证 bare-LF 为 0。
## NX-14 图表/模板不存在与参数错误复核
- 图表和模板 ORM 查询允许返回 `None`，旧路由却直接访问 `.content/.name`，因此合法的“资源不存在”被升级成 500；chart ID 还以未校验字符串进入数据库层。
- 图表 ID 采用严格正整数契约，拒绝布尔值、0/负数、小数、前导零和带空白的非规范形式；已有图表更新在读取大表单字段前先校验 ID。
- 模板名称在 GET/DELETE 两条路径统一做 trim、非空、控制字符和 200 字符上限校验；查询为空分别返回 `chart_not_found` 或 `template_not_found` 404。
- 成功读取的 TradingView `status/data` 结构保持不变。
## NX-15 绘图持久化错误语义复核
- 旧路由把“数据库已提交”“数据库抛异常”和“请求缺少必填字段”三种状态都压成 `{status: ok}`，前端无法判断是否需要保留本地状态或重试。
- DB 保存函数当前明确返回 `True`；路由因此使用严格成功确认，`False`/`None` 不能被当成幂等成功。
- 保存失败生成 request_id，同时写入应用日志和响应；响应只暴露稳定错误码，不回显底层异常或数据内容。
- GET 路径与成功 POST 响应保持原契约。
## RV-05 多进程回测输出路径复核
- `save_file` 对普通回测可选，但多进程模式必须落地每个标的结果供主进程汇总；该条件应在创建进程池前成为明确配置契约。
- 对完整路径调用字符串 `split(".pkl")` 会把父目录名中的同名片段也截断；新实现只用 pathlib 处理最终文件名。
- 标的代码进入文件名时小写并把非字母数字/下划线/连字符折叠为下划线；无法形成有效名称时拒绝。
- 父目录由主进程在 worker 启动前创建，直接调用 `run_by_code` 时也防御性创建。
## RV-04 保本交易统计复核
- 旧二分法把所有非正值归入 loss；保本交易需要独立 `flat_num`，否则失败次数、胜率和平均亏损都会被污染。
- 浮点结算可能出现接近零的正负噪声，本轮用 1e-9 绝对容差做三分法；容差内既不增加盈利金额也不增加亏损金额。
- 胜率继续定义为 win/(win+loss)，持平不计入方向判断；总交易数和结果表单独展示持平数量。
- 旧保存结果没有 flat_num，`ensure_result` 在下一次写入时为缺失统计键补零；只读报表用 `.get(..., 0)` 兼容旧数据。
## RV-01 自选置顶市场隔离复核
- 业务主键是 market + zx_group + stock_code；置顶只按 zx_group 匹配会跨市场污染同名组，必须与读取和删除使用同一复合过滤。
- 删除旧标的、目标组重排和插入显式放入 `Session.begin()`；故障注入确认插入失败不会留下已删记录或已移动位置。
- 仅做 position+1 在“已有标的重新置顶”时会保留排序空洞，因此修复在 flush 删除后把目标 market/group 剩余行压实为 1..N，再插入 position=0。
- 其他市场的同名组完全不读取、不更新。
## RV-07 UDF/search/marks 参数契约复核
- 公开路由的输入校验必须发生在 `Market(...)`、provider 构造和数据库访问之前；否则即使最终返回错误，畸形请求仍可能触发网络、线程或数据库副作用。
- TradingView symbol 收敛为精确一个 `market:code` 分隔符，市场必须在静态元数据中存在，code 受字符、控制字符和 UTF-8 字节上限约束。
- UDF 读取接口保持 `s:error/errmsg`，普通 search 与写入 del_marks 使用 422 和稳定错误码。
- 空 search query 是现有合法行为，仍允许列出前 N 个标的；limit 收敛为 1–100，布尔只接受 true/false，时间区间要求 from<=to。
- 合法 history 继续先按市场时区规范化，再做范围过滤和 OHLCV 转换。

## ME-11 BaoStock 目录、分钟时间与重登录复核
- 证券目录不能绑定某个历史常量；适配器现在按上海市场日期读取最近交易日历，并在当日数据尚未发布时只在有限窗口内回看，成功结果记录来源交易日并按市场日缓存。
- BaoStock 分钟字段本身提供 `YYYYMMDDHHMMSSsss` 交易所时间。该时间是数据协议的一部分，必须直接解析；按行序从 09:30 人工生成会把缺 bar、停牌和乱序放大为整日时间漂移。
- 时间解析严格校验 `date` 与 17 位时间中的日期一致，畸形或缺失时间明确失败，避免用“看起来连续”的伪时间掩盖上游数据质量问题。
- 会话失效不再递归进入完整 `klines`；统一查询门最多 3 次、指数退避并受 8 秒总重试预算约束。SDK 单次调用本身没有 timeout 参数，因此只能界定重试生命周期，不能强杀已阻塞的供应商调用。

## HI-17 可恢复行情同步批次复核
- 三份旧脚本并非同一种“顶层执行”：A 股在 import 时完成 provider 构造、目录查询并直接进入 1,210 标的循环；数字货币在 import 时连接并获取全市场；美股仅线程池有 main guard，但 provider 仍在顶层构造且 495 标的/周期不可配置。统一修复必须覆盖所有这些边界，不能只补 main guard。
- 批次恢复主键固定为 `code::frequency`；checkpoint 同时绑定规范化配置 SHA-256。这样完成项可安全跳过，而 universe、周期或 provider 配置变化不会静默复用旧进度。
- checkpoint 每次状态转换都写临时文件、flush+fsync 后原子 replace，并尽力 fsync 父目录；上次处于 running 的 item 在恢复时转回 pending 并记录中断原因。
- 外部同步 SDK 无法由 Python 强杀，因此 wall-clock timeout 与固定 daemon 槽位必须同时存在：前者保护批次响应时间，后者限制超时残留调用数量。
- 增量页终止同时依靠 terminal row 数、最大页数和进度 token 去重；目标数据库写入只有严格 `True` 才记为完成，避免把 `None`/`False` 伪装成成功。

## ME-12 TDX 重试、Tick 与交易日历复核
- A 股目录的连接错误路径原来递归进入 `all_stocks()`；它现在与 ExHq 构造器共用有限重试门，最多 3 次且受 12 秒总预算约束，节点恢复也计入同一生命周期。
- 涨跌幅的领域分母是前收价而不是当前价。六个 TDX adapter 的所有 Tick 构造统一调用纯函数；0、缺失、NaN、Inf 或非数值前收价不再伪装为 0%，而是沿 `Tick -> /ticks -> zixuan.js` 保留为 unavailable 并显示 `-`。
- 现金市场交易状态改用 timezone-aware 的版本化日历。2026 快照依据 SSE 休市通知和交易时段、HKEX 证券时段与香港政府假日、NYSE 假日/核心时段/提前收市；美国时间使用 `America/New_York`，DST 由 zoneinfo 处理。
- 现金市场超出明确覆盖年份时 fail-closed，避免未知未来假日被静默当作开市；该日历必须按年度公告更新。FX 只提供通用纽约时间 24x5 周界，venue/品种特例以及期货夜盘差异继续由 ME-30 收敛。
- 首次多行 AST 改写只替换完整行，遗留旧外层括号并被 compileall 拦截；所有改动已恢复后改为替换 AST value 的精确字符区间，最终九个历史文件 bare-LF 均为 0。
- 同进程广泛回归还证明专项测试必须兼容 `@fun.singleton` 的包装函数语义；测试现在优先解包 `__wrapped__`，不再依赖模块导入顺序。
- 仓库全量收集的 footprint 私有时间函数导入漂移可追溯到最初导入基线，并非 ME-12 引入；同样，缺少本地 config.py 与可选依赖属于当前归档/执行环境限制，已从本条通过结论中明确分离。

## 2026-08-04 续作恢复与 ME-23 重建
- 当前运行环境只保留到问题 031–040 的完整仓库归档；上一轮规划文件记载的 041–050 ZIP 未挂载，GitHub 也无法解析本地提交 `80e346e` 或 `faa2227`。因此不能声称旧 Git 对象仍可用。
- 以重新解压并通过 `git fsck` 的 `9bad598` 为唯一代码固定点，后续问题按照保存的 a–e 台账重新实现、重新测试并重新提交。
- ME-23 的旧 20 品种参数已经原样迁移到不可变版本 `2024-12-13`；版本只覆盖 2024-12-13 起且未做交易所二次核验，缺日期/缺品种明确失败。
- 期货交易器只持有注入快照，具体合约和 TQ 连续合约先规范化到 `EXCHANGE.PRODUCT`；BackTest 保存/加载同时验证 dataset 与 snapshot SHA-256，篡改不再静默通过。


## HI-16 文件缓存原子性、损坏隔离与安全格式复核（恢复重建）
- `save_tdx_klines()` 原先直接覆盖最终 CSV，读取端又对任意异常删文件；权限抖动、并发读取或进程中断会被放大为永久缓存丢失。
- “最后一行可能未完成”原先只靠无条件 `iloc[:-1]` 表达。现在 sidecar 显式记录 `last_row_complete`，调用方可通过 `include_incomplete` 选择，legacy CSV 采用保守规则。
- 所有写入使用同目录临时文件、flush+fsync、`os.replace` 和固定条带锁；坏 CSV/JSON 重命名为 `.corrupt.*`，暂时性 PermissionError 只返回不可用。
- 任意对象 pickle 状态缓存已替换为 schema/version/SHA-256 JSON 白名单；真实恶意 `__reduce__` payload 未执行。TDX 除权缓存同步迁移为原子 CSV。


## ME-17 QMT 行情区间与供应商协议复核（恢复重建）
- 旧 `klines()` 在每次读取前都会检查并触发下载，且下载和读取的 `end_time` 都固定为空；声明的闭区间实际上只使用下界。
- 迅投接口把下载与本地读取分开，`get_market_data_ex` 返回 `{stock_code: DataFrame}`。修复按该结构校验，并在 provider 返回后再次执行 timezone-aware 闭区间裁剪。
- 空 DataFrame 是稳定的无数据结果；缺目标代码、非 DataFrame、缺 OHLCV、重复时间、非有限数值和空盘口分别返回明确 unavailable/schema 错误，不再泄漏 KeyError/IndexError。
- 证券目录改为实例私有且返回防御性副本，订阅默认列表改为 `None`；默认 K 线读取不产生下载副作用，需要刷新时显式调用 `download_klines()` 或 `args={"download": True}`。


## ME-26 Web 与调度器生命周期复核（恢复重建）
- 旧 `create_app()` 每次都会创建并启动 TornadoScheduler；在 reloader、测试 factory 和多 worker 中没有共享 owner，重复执行由控制流直接成立。
- 调度执行现由独立 BlockingScheduler CLI 持有；Web 只写数据库配置和读原子状态快照，保存路径不再重建本进程 job。
- 本地 leader lock 在同一 `DATA_PATH` 上非阻塞抢占，写入 PID 并尽力使用 0700/0600 权限；第二 owner 明确失败，释放后可重启。
- scheduler runtime 的 APScheduler 与 AlertTasks 导入均保持惰性。CLI 直接从 `cl_app` 文件目录导入 runtime，避免 Python 先执行含 Flask/pinyin 的 `cl_app/__init__.py`。
- 任务配置采用默认 30 秒、强制收敛至 5–3600 秒的周期 reconcile；这是多 worker 唯一执行与配置即时生效之间的明确最终一致性边界。
- `/jobs` 的状态只允许 id/name/update_dt/next_run_dt/state 五个字段，按 id 稳定排序；缺失、畸形或读取异常一律返回空列表，不在 Web 进程补启动 scheduler。


## ME-19 选股快照事务与无效方向参数复核（恢复重建）
- 选股计算本身先完成再清空并不等于原子替换；旧 `clear_zx_stocks` 和逐条 `add_stock` 各自提交，第 N 条数据库失败仍会破坏上一版完整结果。
- 新 DB 边界先在事务外完整校验 market/group/code/name/memo/color 和列长度，再用一个 `Session.begin()` 执行 delete + 全量 insert；每行 flush 让触发器或约束错误在该事务中暴露并整体回滚。
- 多频率同代码以首次出现位置为稳定顺序，最后一个信号更新名称与 memo；这适合自选组的一代码一行模型，并避免重复位置。
- 任务只有在全部频率计算及可选 DB 替换成功后才更新内存状态，键由 task_name 改为 `(market, task_name)`；策略或写库失败不会覆盖上一轮内存结果。
- 当前 StrategySignal 没有方向领域字段，`opt_type` 无法被正确消费。删除 UI、路由和 Python 参数比继续接受后忽略更诚实；需要方向筛选时应先扩展后续策略协议。


## ME-18 策略批次失败隔离与 K 线输入协议复核（恢复重建）
- 当前 SelectionRunner 在单一 for 循环中直接访问 stock 字段、调用 provider 和 strategy；任一 malformed target、行情异常、脏 DataFrame 或策略异常都会穿透并终止整批。
- MonitoringRunner 仅提供单标的信号列表，任务层无法区分“合法未命中”与“执行失败”；AlertTasks 只能用宽泛异常日志近似隔离，无法保留结构化阶段和失败标的。
- 统一边界应把 target/provider/input/strategy/output 五个阶段分别建模，并让 BatchRunResult 明确区分 hits、misses、failures；任务层只有无失败时才替换选股快照。
- K 线进入策略前必须深拷贝并按市场时区规范化，再验证必需 date/OHLCV、唯一升序时间、有限数值、非负 volume、OHLC 一致性以及可选 code/frequency 列与目标一致。

- BatchRunResult 保留对 hits 的 `__iter__/__len__/__getitem__` 兼容视图，旧的只读信号列表调用可平滑迁移，但任务层已显式读取 failures，不能再把部分失败当成整批成功。
- 选股任务的 `last_run_results` 保存最近尝试（包括部分 hits 与 failures），而 `running_tasks` 只保存最后一次完整成功；这把“最新尝试”和“最后可发布结果”从同一状态中分离。
- 监控任务在同一批次中会保存正常 hits，并对失败标的记录 code/stage/error；整批返回 False，避免调度器把部分失败误标为成功。


## ME-14 TDX 美股时间与成交量字段复核（恢复重建）
- `ExchangeTDXUS._convert_dt()` 对日线直接 `replace(tzinfo=pytz_zone)`，分钟线先对上海 `pytz` 区域执行 replace；该用法绕过本地化规则，纽约历史 LMT 偏移和 DST 语义都不可靠。
- 适配器在转换前按 naive 中国时间排序，跨午夜的美国交易日可能顺序错误；中国凌晨 00:00–05:59 bar 还依赖手工加一天修正交易日。
- 仓库随附 `pytdx-1.72r2` wheel 的 ExHQ bar parser 同时解析独立字段 `trade` 和 `amount`；当前适配器把 `amount` 写入 canonical `volume`，没有供应商协议依据。
- 修复应在纯 payload 边界完成：使用 zoneinfo 明确解释上海墙钟并转换纽约时间，转换后排序；日线按美国交易日锚定 16:00；volume 只接受 parser 的 `trade`，缺失时 fail-closed，并统一校验 OHLC、时间唯一性和数值质量。

- 分钟源协议现在显式定义为“美国交易日标签 + 上海墙钟小时”：21:30 等晚间时刻直接本地化，00:00–05:59 先推进一个上海自然日，再转换纽约；这样凌晨 close bar 不会落到前一美国交易日。
- 日线及以上不再猜测上海瞬间，而是只使用 provider 的交易日期并锚定纽约常规收盘 16:00；提前收市精细化留给 ME-30。
- normalizer 在市场时区转换后才稳定排序，并严格拒绝 aware 源时间、重复市场时间和缺少 `trade`，避免双重转换或 amount 回退掩盖供应商协议漂移。


## ME-30 统一交易时段与品种感知日历复核（恢复重建）
- 问题不只存在于旧报告点名的 TDX 路径：QMT/Baostock/Alpaca/IB 以本机或硬编码时钟判断，Futu 固定查 HK 日历，Polygon 依赖远端粗粒度状态，TQ/TDX 国内期货统一视为交易到 02:30，TDX 纽约期货恒真。
- `now_trading()` 的领域主键必须包含 market、instrument 和 timezone-aware instant；只返回市场级布尔值无法区分 CFFEX 日盘、无夜盘品种以及 23:00/01:00/02:30 商品夜盘。
- 国内期货夜盘跨午夜不能按当前 weekday 简化：周五晚盘延续到周六凌晨，而周日晚并不开盘；节前夜盘需根据下一交易日距离保守关闭。
- 未覆盖年份、新上市/未知品种与缺少 code 必须 fail-closed，不能继承相近品种或返回 True。现金市场继续复用 ME-12 的 2026 版本化节假日/午休/半日市，数字货币显式 24x7，FX 保留纽约周界 24x5。

- CME 官方 2026 Globex 页面确认常规与假日时段按产品表发布，并注明 holiday schedule 可能变化、通常在节日前约两周最终确定；因此本地纽约期货日历只编码明确周界/维护窗并对列出的节假日保守 fail-closed，不把不完整假日表伪装成权威逐产品日历。
- `/ticks` 的既有 JSON 只有一个 `now_trading`；为不破坏前端，本轮对请求代码做逐品种判断后以 `any(...)` 聚合。监控任务则真正按代码过滤闭市标的，畸形记录保留给 ME-18 结构化 target failure。


## ME-22 消息、时间与 singleton 工具复核（恢复重建）
- 锁定依赖 `lark-oapi==1.5.3` 的官方 `ClientBuilder` 已提供 `.timeout(float)`，`CreateMessageRequestBody` 也提供 `uuid`；因此无需在 SDK 外再创建无法取消的工作线程，可以直接给每次 HTTP attempt 设置上限，并用同一 UUID 安全重试。
- 消息创建不是天然可重试操作；只有在一次逻辑调用内固定 UUID，且只对 transport 异常、429/5xx 重试，才能同时控制重复消息和不可恢复业务错误放大。
- `time.localtime/mktime` 和 naive `datetime.timestamp/astimezone` 都会读取宿主机本地时区；共享时间工具必须把 wall-clock 所属时区作为显式输入，epoch 转换只接受 aware datetime。
- zoneinfo 直接 `replace(tzinfo=...)` 对普通时刻可用，但 DST 缺口/重叠需要 round-trip 校验；本轮对 nonexistent 直接拒绝，对 ambiguous 要求显式 fold。
- singleton 双重检查必须在构造完成后才写入共享状态；否则构造异常可能留下半初始化对象。进程间唯一性不是 singleton 能解决的，应继续使用 ME-26 的 leader lock 等专用机制。


## ME-02 history follow-up 状态边界复核（恢复重建）
- 原计数器的真实节奏不是固定“每七次一轮”：新 key 的第 1–6 次为 ok，第 7 次 no_data 并把 counter 设为 0；因为 key 仍存在，后续第 13、19…次也会抑制。并发回归必须按该原控制流而不是直觉周期断言。
- UI 请求节奏状态应使用 monotonic clock；墙钟跳变不能决定短窗口。过期回收与 LRU 淘汰必须和计数位于同一锁内，否则“线程安全 dict”仍会在组合操作上竞态。
- 状态主键至少包括认证身份、来源地址、市场、代码和周期。只用 symbol/resolution 会让不同浏览器共享并消耗同一节奏。
- `firstDataRequest=true` 的完整历史是产品 zoom-out 契约；修复内存与并发问题时必须把 tracker 调用放在明确的 follow-up 分支，不能顺手改变返回范围。
- 该 tracker 不是安全限流器。多 worker 各自有界即可关闭本条内存/竞态根因；跨进程频率治理应由 Redis/代理等独立基础设施承担。

## NX-10 策略配置物理存储与迁移复核
- SQLAlchemy `create_all()` 只创建缺失表，不会把已部署的 `VARCHAR(200)` 改为 TEXT；模型类型变化必须配套显式、幂等的运行前迁移。
- 新列优先、旧列 fallback 能把兼容读取与新写入分离：升级后所有新数据进入独立 Text，旧数据回填后仍可读，避免继续扩大 legacy 技术债。
- SQLite 不强制 VARCHAR 长度，不能作为 MySQL 截断的证明；必须同时编译 MySQL DDL，并在应用层把最大 UTF-8 字节数设在 TEXT 容量以内。
- 对可能受 SQL mode 影响的文本写入，只有 `flush/refresh` 后精确比较才能发现“调用成功但内容已截断”的伪成功。
- 字段限制要在 `json.loads` 和可信策略模块导入前执行，否则虽然数据库安全，超大字段仍能消耗解析/导入资源。

## RV-06 TradingView 存储容量与并发边界复核
- 全局 HTTP 请求体上限不能替代领域字段限制；同一 1 MiB 请求内仍可能让 chart/template/drawing 超过数据库列或单主体合理容量。
- 配额必须基于 UTF-8 实际字节而不是 Python 字符数；多字节中文、非法 surrogate 和 NUL 都需要在数据库之前确定性处理。
- “先查询占用、再写入”只有处在同一串行化事务中才是配额。MySQL 可锁主体行；SQLite 忽略 `FOR UPDATE`，必须在第一次读取前取得 `BEGIN IMMEDIATE` 写锁。
- 唯一索引与 upsert 同时解决重复记录和配额绕过。旧表建立唯一索引前必须先按 timestamp/id 保留最新记录，否则迁移本身会失败。
- 配额收紧后不能让历史超限主体永久无法保存更小内容；投影规则应允许占用不变或下降，但拒绝任何进一步增长。
- client/user 只是 TradingView 兼容命名空间，不是可信授权主体；容量治理和授权治理必须分开，本条不提前吞并 ME-01。


## ME-15 Futu 上下文所有权与故障隔离复核
- 模块级 SDK 对象不是连接池：没有锁、owner、generation 和 close 时，它同时制造并发竞态、坏连接缓存和测试/退出泄漏。
- quote 与 trade 应分别拥有锁和健康状态。行情失败不能顺便关闭交易上下文，反之亦然；这是失败隔离的最小边界。
- 工厂结果必须先在局部变量完整构造，再原子发布；构造失败不得留下“非 None 但不可用”的共享对象。
- SDK 返回 `RET_ERROR` 与 Python 异常都必须进入同一失效/重建状态机；只打印错误并返回空值会让坏连接永久驻留。
- 同类 SDK 调用在共享对象上必须串行；quote 与 trade 通过独立锁仍可并行，避免把两个所有权域无意义地绑成一个全局瓶颈。
- fork 后继承的 socket/线程对象不能继续复用。PID 变化或 at-fork child 回调必须丢弃两个上下文并按需创建新 generation。
- 随机执行 `unsubscribe_all()` 是隐藏的跨请求副作用；订阅容量治理应由确定性策略和可观测配额承担。
- health 只公开 state、PID、generation、最近成功时间和异常类型；不得包含 host、账户、token 或第三方原始错误文本。


## NX-01 已移除 CTP 的前置地址恢复契约
- 当底层 provider 已从运行包删除时，修复其内部空值分支会错误地重新扩大能力面；正确关闭方式是证明路径不存在，并固定恢复前置条件。
- “属性不存在”和“属性存在但为空”是不同状态；未来地址解析必须采用显式 schema，不能依赖 `getattr` 是否返回属性。
- provider tombstone 必须在惰性 import 和缓存写入前执行，防止删除的 SDK 模块因误配置重新产生副作用。
- 恢复地址必须在 SDK 构造前验证为非空 `tcp://host:port`；缺 scheme、凭据、路径、query、fragment、非法端口和控制字符全部拒绝。


## NX-25 遗留 provider 的 TLS 删除证明
- “工厂未注册”只降低默认可达性，不能消除可直接导入的 TLS 绕过；安全关闭需要把实现从运行包删除。
- TLS 恢复契约必须同时覆盖证书链、主机名、信任库和失败策略；只删除一个 `verify=False` 参数并不足够。
- 仓库门禁应扫描语义等价绕过，包括 `CERT_NONE`、`check_hostname=False` 和 WebSocket `sslopt`。
- TLS 验证失败必须中止连接且不得降级；日志只能包含稳定、无秘密的错误类型。


## ME-29 可执行质量门禁复核（恢复重建）
- 门禁是否真实可执行不能只靠 YAML 关键字扫描；必须按 workflow 中列出的文件实际运行。此次正是执行 provider job 才发现静态 checker 未发现的错误测试文件名。
- 单元、provider、真实数据库与真实 DOM 是不同失败域，应使用稳定独立 job 名，便于 required-check 和故障定位。
- 当前环境缺少依赖不应促使 CI 使用 ignore/deselect；本地可明确记录阻断，托管 Python 3.11 job 必须在 `uv sync --locked` 后运行完整套件。
- SQLite 单测不能证明 MySQL DDL/截断语义，模板文本扫描也不能证明渲染 DOM 不含 Secret；这两类风险需要真实 service/browser gate。
- 修复已删除私有 API 的导入属于恢复“完整套件可收集”边界，不应通过跳过测试掩盖。


## ME-10 能力绑定适配器边界复核（恢复重建）
- broad ABC 的“方法存在”不等于能力存在；标准工厂必须在 SDK 调用前拒绝未声明能力。
- Registry 自身必须可在没有本地 config.py、没有 SDK 的环境直接导入，否则能力发现会重新产生启动副作用。
- DB 的持久化 code catalog 可支持搜索/选股，但 code=name 不构成 authoritative security master；应以独立 CATALOG 与 SECURITY_MASTER 区分。
- 构造器结果只能在构造、声明方法和 facade 校验全部成功后发布到缓存；异常对象或半初始化对象不能被后续请求复用。
- SDK 原始异常可保留在 exception chain 供本地调试，但 public message/to_dict 不能复制原文，避免 token、账号和 URL query 泄漏。
- `LIVE_ORDERS` 必须与账户/持仓读取分离；能读账户不代表订单状态机已验收。


## ME-20 版本化策略信号协议复核（恢复重建）
- “返回 dataclass”只约束外形，不约束领域语义；协议必须在 runner 接受点重新 canonicalize，而不能信任策略自行构造的对象。
- Selection 与 Monitoring 的动作集合不同；`select` 进入监控或 `buy` 进入选股都应作为 output failure，而不是由下游猜测。
- code/name/frequency 必须与当前 target 完全绑定，避免策略把另一个标的或周期的信号注入当前批次。
- metadata 只允许有界 JSON 数据，并保持原值、深拷贝隔离；它不是代码、模块路径、HTML 或授权载荷。
- naive `event_time` 与 `context.now` 只能按目标市场时区解释；aware 时间转换到市场时区，异常未来时间 fail-closed。
- `ignore` 是显式未命中，不应保存为事件。单目标输出必须 materialized、有数量上限且去重，避免 generator 延迟副作用和无界持久化。
- 任务层只接受 `BatchRunResult`，否则可信进程内 fake/custom runner 可绕过标准 runner 已完成的输出校验。
- 回测 `Operation` 仍是独立协议；本条不提前吞并 MX-18 的跨场景 Signal→Decision→Order 架构选择。


## ME-25 可验证供应链证据复核（恢复重建）
- 直接依赖声明和可复现解析结果必须分工：`pyproject.toml` 声明意图，`uv.lock` 是唯一安装结果；保留手写 requirements 会重新打开未审计解析路径。
- 锁文件只证明解析内容，不自动证明仓库内本地 wheel 的来源；每个制品还需要路径、大小、SHA-256、marker、锁定哈希、upstream/provenance 和许可证证据。
- wheel METADATA 的多值字段没有可依赖的语义顺序；生成证据前必须排序，否则同一字节制品会产生不稳定报告。
- committed vulnerability report 在离线生成时必须显式标记 `not-run-offline`；空 advisory 数组不等于安全结论。
- 在线 OSV 查询必须对 HTTP/JSON/结果基数异常 fail closed；豁免需要 advisory+package 精确绑定、负责人、原因和短期到期日。
- SBOM、许可证和漏洞输出应由锁图确定性生成并由 hygiene 检查 stale，CI 再生成安装环境增强证据作为 artifact，不能回写带时间戳的实时结果。
- 固定 uv 版本和 `UV_PYTHON_DOWNLOADS=never` 把 Python 解释器也纳入环境契约；本地没有 3.11 时应明确失败，而不是静默下载另一个运行时。


## ME-27 引用式 Secret、分级与轮换边界
- Python 配置文件不能同时充当 Secret store；配置只保留引用，实际值应在数据库、SDK 或消息客户端构造的最后使用边界解析。
- Secret inventory 必须同时声明安全领域和轮换责任。database/market-data/broker/AI 通常由外部平台轮换；飞书 Web Secret 使用本地 managed-versioned 流程，数据库只持久化不可读的引用。
- `managed://` 轮换顺序是先原子创建新 0600 版本，再提交引用，最后退役旧版本；失败时宁可保留孤立旧版本，也不能先删除仍被数据库引用的 Secret。
- `env://` 和 `file://` 是否“已配置”与是否可读取应分开；真正需要调用外部服务时使用 required=True fail-closed。
- 日志脱敏必须在 Secret 解析时注册实际值，并额外覆盖 Authorization、URL userinfo 和常见 password/token/api_key 键值形态；它不能替代禁止记录原始 SDK 对象。
- 配置门禁应从运行时 Secret policy inventory 派生字段清单，避免新凭据只加入模板却绕过分类与扫描。
- 能力 facade 的“未声明 LIVE_ORDERS”不是足够的长期防线；公开 `order()` 本身也必须保持 CR-03 无条件 fail-closed，防止未来 registry 误报重新接通未对账下单。


## ME-04 恢复重建
- 时间规范化必须先于范围过滤；完整 OHLCV、身份、顺序和有限数在 Web 边界 fail-closed。


## ME-01 TradingView 存储授权边界（恢复重建）
- RV-06 的容量配额按 `client/user` 命名空间治理资源，但这些字段来自请求，不能同时承担授权身份。协议兼容字段与认证主体必须分离。
- 新 owner 应由 `flask_login.current_user.get_id()` 派生；请求中的 `user` 只作 TradingView 协议格式校验，绝不能传给数据库 CRUD。
- 旧 owner 迁移只能接受显式 allowlist，并在同一事务内处理 chart/template/drawing 与 quota owner；未知 owner 保留，避免把其他主体数据错误归并。
- 迁移碰到同名/同键冲突时应确定性保留最新记录，随后幂等重跑不得继续改变数据。


## ME-03 UDF 周期并集
- 全局 UDF 能力必须遍历元数据实际键集合；手写市场并集即使当前输出相同，也会在新增市场或独有周期时静默漂移。
- 稳定按注册顺序去重比 set 直接转换更可复现，避免响应顺序随运行环境变化。


## MX-11 IB 账户标识防回归
- Secret 引用治理不能只扫描配置赋值；docstring、注释和示例也可能继续暴露真实账户标识，应纳入运行源码门禁。
- IB worker 必须先解析引用再连接；明文与缺失环境变量都应在 SDK 调用前失败。


## MX-07 Layui 列契约
- templet 直接读取行对象会掩盖 `field` 拼写错误；页面能显示不代表排序、字段元数据和后续组件绑定正确。
- 前端门禁应同时校验字段集合、同一列内的 sort 绑定和 JavaScript 语法。

## MX-10 图表展示参数契约
- JavaScript 允许多余实参会掩盖调用方与实现漂移；仅靠页面“还能显示”不能证明尺寸参数生效。
- TradingView widget 使用 autosize 时，尺寸应由已创建的容器布局负责；API 不应同时接收一个未使用的高度。
- 前端契约门禁应同时检查调用点实参数量、运行时 function.length、容器尺寸来源和 JavaScript 语法。

## NX-09 未实现公开费用桩
- 无调用方且返回 None 的公开费用函数比显式缺失更危险：它会把未实现能力伪装成可调用成功。
- 没有权威费率数据、版本和生效日期时，删除能力优于编造默认计算；未来恢复应纳入 ME-23 同类的数据治理。
- 删除证明需要同时覆盖定义、引用和动态导出，避免另一个模块又 re-export 同名空桩。

## NX-18 自选模板变量作用域
- 非严格 JavaScript 的未声明赋值会静默写入全局对象，短期不报错并不代表安全。
- 临时渲染字符串应在最小回调作用域内用 const 构造，避免跨组件状态污染。
- 前端作用域修复应动态执行真实脚本并检查 global/context 属性，而不是只做正则替换。

## NX-17 TradingView 市场描述符
- UDF 的 type/session/timezone 是行情语义，不应由 Web app factory 手写第二套注册表。
- FX 的 24x5 周界依赖纽约本地时间；数字货币才是 24x7。
- 国内期货不能使用一个统一夜盘：23:00、01:00、02:30、股指、国债和无夜盘产品必须按 instrument profile 映射。
- 未识别产品宁可声明保守日盘，也不能猜测夜盘或退化为 24x7；节假日仍由运行时 calendar 决定。
- 搜索请求中的 type 是筛选条件，不是服务端返回类型的授权来源。

## LO-02 重复行情与同步工作流复核（恢复重建）
- 五个 TDX ExHq 适配器仍分别复制 `tdxex_connect_ip` 缓存读取、节点重选、client 构造、market map 有界加载及异常转换；它们的差异只有 category/market 过滤和少量 client 参数，适合收敛为依赖注入式生命周期 mixin。
- Alpaca 与 Polygon 重复美国历史区间解析和 OHLCV frame 构造；两者在显式 `start_date` 分支都错误检查已经转为 datetime 的 `end_date` 长度，属于可确定复现的类型错误，而不只是可维护性问题。
- A/US/币本位三份同步脚本已使用 `sync_batch.py`，但港股、币现货、期货仍在 import 时构造 provider 并执行顶层循环；期货脚本还保留 2022 年具体合约列表。剩余入口应改为同一薄 CLI + 外部 JSON universe。
- 共享层必须保留此前可靠性契约：ExHq 总 deadline/有限重试、节点 TTL、provider 失败 fail-closed；同步显式空 universe 只能通过 `allow_empty`，且应在实例化 provider 前安全退出。

## LO-02 共享边界最终结论
- 可复用代码的边界应是失败语义而不是表面相似片段：ExHq 共享层统一 cache/node/client/deadline/map 发布，provider 只声明真实 market 差异。
- 历史日期解析必须把 start/end 独立 canonicalize；先把字符串转成 datetime 再继续使用 `len()` 是重复实现漂移已经产生的确定性故障。
- 美国历史数据应先转换到市场时区，再排序、去重和锚定日线收盘；provider 只负责把 SDK 记录映射为共享字段。
- 通用批处理的显式空 universe 是安全配置，不等于意外过滤为空；前者可以在任何 provider import 前零副作用完成，后者必须 fail-closed。
- 对有网络副作用的脚本，薄 main guard + 外部 JSON + 共享 checkpoint runner 同时减少重复、恢复风险和维护者误 import 的危险。

## LO-06 可审计 provider 边界
- wildcard import 既隐藏依赖也让静态类型/升级审查失真；运行树必须零容忍，而不是依赖维护者记住名称来源。
- 第三方 SDK 异常类型不统一时，唯一合理的 broad catch 应集中在明确 integration boundary，并带静态规则豁免理由；业务 adapter 不再各自 print/return None。
- 结构化日志的稳定字段应是 market/code/request_id/operation/provider/error_type，绝不能复制第三方异常消息，因为其中可能包含 token、URL 或账号。
- 锁文件治理下不能临时 pip 安装未锁定 lint 工具；项目配置声明 Ruff 规则，仓库内无依赖 AST checker 负责 CI 执行和故障注入。

## MX-16 死能力删除边界
- 未加载的前端桩和只剩 pass 的后台任务不是“未来功能”，而是错误能力声明；没有真实职责、入口和测试时应从运行树删除。
- app factory 中的懒代理仍会保留导入和初始化认知面；删除实现时必须同时删除注册点并用引用图固定。

## MX-18 策略与执行桥接边界
- Signal 与 Operation 不应直接合并：前者描述观察事件，后者包含执行仓位、止损和幂等键；正确抽象是显式 Decision 中间层。
- score 不是 position_rate，message 不是 signal key；任何转换参数都必须由版本化 metadata.trade 明确给出。
- 双向转换只有在 Operation 保存原始 bridge snapshot 时才无损；缺少上下文的历史 Operation 必须拒绝，不能伪造时间和频率。
- snapshot 需要在反向转换前逐字段核对，防止调用方在生成后修改仓位或动作却仍沿用旧 trace。


## NX-11 typed monitoring event schema（恢复审查）
- 最终实现已把通用监控事件从旧 `line_type/bi_is_done/bi_is_td` 兼容列迁到物理列 `event_type/action/score`，同时保留旧 Chanlun 记录读取能力。
- 关闭本条的关键不是简单扩大字符串长度，而是：事件类型与动作在写入边界 canonicalize，score 持久化为有限浮点值，旧表迁移只回填可识别值，未知旧数据保持可读且不被伪造为新协议。
- 迁移与 ORM 同时映射同名物理列时必须重点检查 SQLite/MySQL DDL、幂等迁移、旧 schema 回填、查询兼容及 `Float` 精度往返；SQLite 的宽松类型不能替代 MySQL 方言验证。

- NX-11 迁移不能使用无精度的 MySQL `FLOAT`；当前实现通过 `_alert_event_score_sql_type()` 对 MySQL 使用 `DOUBLE`，并由模型 DDL 与迁移类型测试双重固定。
- 前端数值展示必须区分 `0` 与空值；`d.score || ""` 会丢失零分，显式 null/undefined 判断是必要的契约修复。

- NX-11 的旧字段只应在新 typed 列为空时作为兼容读取来源；typed 列存在但非法时不能回退到旧值掩盖损坏，应明确返回不可用。

## NX-11 最终结论
- 旧短字符串列的真正风险不仅是容量，而是类型和精度混在一起；独立物理列必须与领域 enum/动作集合和有限数校验同时落地。
- SQLite 的动态类型不会暴露 MySQL `VARCHAR` 截断或 `FLOAT` 单精度风险，因此迁移 SQL 需要显式方言契约，MySQL score 使用 `DOUBLE`。
- 兼容迁移只应回填可证明的旧别名；未知历史值保留在旧列比猜测成新事件更安全。
- DB 原生 ENUM 会把每次动作扩展变成高风险 DDL；有界字符串列配合单一领域枚举、写边界验证和穷尽测试更适合当前跨 SQLite/MySQL 架构。
- 数值前端渲染不能使用 truthiness；`0` 是合法评分，只有 `null/undefined` 才代表缺失。
## LO-05 市场注册表全栈盘点
- `market_registry.py` 当前只集中 provider/capability/config_attribute；`market_metadata.py` 仍维护第二套八市场默认代码、周期、TradingView 类型/session/timezone，形成真实双源。
- `/tv/config` 手写八个 exchange 描述，首页模板手写八个默认代码键；新增市场仍需同步修改 Python、路由和模板。
- 配置模板仍通过八个 `EXCHANGE_*` 全局变量选择 provider。要真正降低 shotgun surgery，应让 MarketSpec 声明默认 provider，配置只提供可选 `MARKET_PROVIDERS` override；旧属性只作兼容读取。
- 国内期货 session 依赖 instrument profile，不应退化为静态值；profile→TradingView session 也应成为 MarketSpec 的数据，而运行时 profile 由 trading_calendar 决定。
- 进一步确认标准 `get_exchange()` 在调用注册表前仍手写 `Market -> EXCHANGE_*` 字典，只为读取 tombstone provider；这可以直接改为 `market_spec(market).config_attribute`，无需第二套映射。
- 首页不仅手写默认代码键，还手写市场选择项与 `/tv/config` exchange 描述；如果注册表提供 label、default_code、frequencies 和 TradingView 元数据，这些都可由同一描述符生成。


## LO-05 全栈市场单一来源最终结论
- 市场注册表必须同时描述静态产品语义和 provider 路由；若 Web/UDF、配置模板或同步脚本另有八市场字典，所谓 registry 仍只是局部目录。
- 默认 provider 应属于 descriptor，而配置只表达覆盖。这样新增市场只增加一个 Market 枚举值和一个 MarketSpec；新部署无需再编辑八个 EXCHANGE_* 变量。
- removed-provider tombstone 需要读取“尚未验证的 provider 名称”后立即执行，再进入普通 registry 验证；否则 CTP/ZB 会被降格为一般未知 provider，丢失删除原因和安全证明。
- 展示周期与特定离线同步周期可以有不同集合，但两者必须位于同一个 MarketSpec；同步任务不可自行维护第三套允许列表。
- 单一来源应以 synthetic descriptor 故障注入证明：一个注册条目能同时派生页面 catalog、默认代码、UDF session/type/timezone 和同步校验，而缺项/双默认在启动时失败。


## LO-07 显式能力边界与空桩治理
- 可选 provider 能力不应由每个适配器重复 `pass`、空列表、`RuntimeWarning` 或通用 `Exception`；统一由 `Exchange` 基类抛出带 capability/provider 的 `UnsupportedCapabilityError`，标准工厂再按注册表能力提前拒绝。
- 注册表过报检查不能只看 `callable(getattr(...))`：继承自 `Exchange` 的统一 fallback 仍然 callable，`ContractedExchange` 必须把该实现识别为“未实现”。
- 直接删除适配器空桩后，旧测试若仍要求方法存在，会把 speculative generality 固化为契约；应保留“不声明能力”的领域目标，更新为断言 provider 不重声明空桩。
- IB 的 `all_stocks()` 只是恒定空列表，不能支撑 CATALOG/SECURITY_MASTER；保留真实 ticks/session/account/positions，删除目录能力声明。
- 运行树墓碑模块和无调用方 RuntimeError 壳会制造虚假能力面；确认没有运行引用后应删除。真正需要的可选生命周期 hook 应明确 `return None`，而不是裸 `pass`。
- `cl_app.__init__` 中 `_UnavailableTasks.__getattr__` 的 RuntimeError 属于第 81 条 MX-12 旧模块专用降级残留，本条只记录、不提前合并后续问题。
