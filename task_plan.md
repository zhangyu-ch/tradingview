# 任务计划：逐条修复 TradingView 当前 81 条未关闭问题

## 目标
以用户上传的本地仓库为主线，逐条验证并修复 `audit/tradingview_current_open_issues_v1.md` 中的 81 条问题；每条问题形成独立本地 Git 提交，更新验证记录；每完成 10 条生成完整仓库 ZIP 归档，最终交付全部归档、最终仓库与提交日志。

## 当前阶段
阶段 7（第 57 条 ME-10 已重建并验证，下一条为第 58 条 ME-20）

## 各阶段

### 阶段 1：建立基线与问题台账
- [x] 解压本地仓库与 planning-with-files 技能
- [x] 保存原始问题清单到 audit/
- [x] 确认本地代码版本、远程仓库最新状态和差异
- [x] 解析 81 条问题为机器可跟踪台账
- [x] 执行基线测试并确定离线验证策略（完整依赖环境受 DNS 阻断）
- **状态：** complete

### 阶段 2：逐条验证、修复、测试与提交（1–10）
- [x] 每条先复现/验证存在性
- [x] 修复根因并补回归测试
- [x] 更新 remediation 日志 a–e
- [x] 每条独立提交到 main
- [x] 第 10 条后生成完整仓库归档 01
- **状态：** complete

### 阶段 3：逐条验证、修复、测试与提交（11–20）
- [x] 完成 11–20
- [x] 生成完整仓库归档 02
- **状态：** complete

### 阶段 4：逐条验证、修复、测试与提交（21–30）
- [x] 完成 21–30
- [x] 生成完整仓库归档 03
- **状态：** complete

### 阶段 5：逐条验证、修复、测试与提交（31–40）
- [x] 完成 31–40
- [x] 生成完整仓库归档 04
- **状态：** complete

### 阶段 6：逐条验证、修复、测试与提交（41–50）
- [x] 41. ME-23
- [x] 42. HI-16
- [x] 43. ME-17
- [x] 44. ME-26
- [x] 45. ME-19
- [x] 46. ME-18
- [x] 47. ME-14
- [x] 48. ME-30
- [x] 49. ME-22
- [x] 50. ME-02
- [x] 完成 41–50
- [x] 生成完整仓库归档 05
- **状态：** complete

### 阶段 7：逐条验证、修复、测试与提交（51–60）
- [x] 51. NX-10
- [x] 52. RV-06
- [x] 53. ME-15
- [x] 54. NX-01
- [x] 55. NX-25
- [x] 56. ME-29
- [x] 57. ME-10
- [ ] 58. ME-20
- [ ] 59. ME-25
- [ ] 60. ME-27
- [ ] 完成 51–60
- [ ] 生成完整仓库归档 06
- **状态：** in_progress

### 阶段 8：逐条验证、修复、测试与提交（61–70）
- [ ] 完成 61–70
- [ ] 生成完整仓库归档 07
- **状态：** pending

### 阶段 9：逐条验证、修复、测试与提交（71–80）
- [ ] 完成 71–80
- [ ] 生成完整仓库归档 08
- **状态：** pending

### 阶段 10：第 81 条与全量回归、最终交付
- [ ] 完成第 81 条并独立提交
- [ ] 执行全量测试、静态检查和提交完整性校验
- [ ] 生成最终完整仓库 ZIP、修复报告、git log 与校验和
- **状态：** pending

## 处理规则
1. 顺序严格按问题索引 1–81。
2. 每条记录：问题是什么、如何修复、是否验证、如何验证、是否通过。
3. 若验证后问题已不存在，不做无意义代码改动；补充防回归测试/证据并以该问题编号独立提交。
4. 对依赖真实交易账户、专有 SDK 或在线服务的条目，必须完成可离线的契约/故障注入测试；无法执行的真实联调须在日志中明确标注，不得把未验证部分声称为通过。
5. 每个提交只处理一个主问题；必要的共享基础设施变更归入首次使用它的问题，后续问题引用并补专项验证。
6. 每 10 条归档包含完整 `.git` 历史，确保用户可查看每次提交。

## 已做决策
| 决策 | 理由 |
|------|------|
| 本地 ZIP 为主代码基线，远程仓库仅用于校正 | 用户明确指定本地代码为主要代码 |
| 初始化新的本地 Git 仓库并创建 `main` | 上传 ZIP 不含 `.git`，仍需保留逐条提交历史 |
| 原始问题清单只读保存在 `audit/` | 保留证据，避免修复日志覆盖历史内容 |
| 维护独立 `remediation_report.md` | 便于每条提交同步更新且最终直接交付 |

## 遇到的错误
| 错误 | 尝试次数 | 解决方案 |
|------|---------|---------|
| 上传 ZIP 不含 `.git` 历史 | 1 | 以 ZIP 内容创建新的本地 `main` 基线提交，并记录远程校正信息 |
| HI-14 首次整体替换脚本未找到预期标记 | 1 | 放弃脆弱的多段索引替换，改为以稳定方法边界重建文件顶部并逐块断言 |
| HI-14 真实导入被缺失 `tzlocal`/`tqsdk` 阻断 | 2 | 停止继续伪造生产 SDK，采用 ManagedWorker 动态测试、AST 契约与 compileall，并在报告保留联调限制 |
| HI-06 初次批量补丁未命中 alert.js 预期标记 | 1 | 保留已成功写入的文件，改为逐文件稳定标记替换并各自断言 |
| CR-03 首次 AST 写回把 CRLF 文件转换为 LF，造成大面积无意义 diff | 1 | 恢复相关文件到 HEAD，改用 newline="" 保留原换行符后重新应用真实改动 |
| MX-05 首次 JavaScript 语法测试跨越多个 `<script>` 标签，Node 报 `Unexpected token <` | 1 | 改为只提取无 `src` 的独立内联脚本并逐段编译 |
| MX-17 首次改写 CRLF 的 `tdx_best_ip.py` 造成全文件换行差异 | 1 | 恢复文件后用 `newline=""` 保留 CRLF，仅重做真实逻辑变更 |
| NX-08 相邻 `test_backtesting_base_generic.py` 收集时缺失 `empyrical` 依赖 | 1 | 保留环境限制，运行专项 POSITION 测试、compileall 和静态契约验证 |
| NX-22 首次真实导入测试被缺失 `tzlocal` 阻断 | 1 | 子进程仅注入 `get_localzone() -> UTC` 最小桩，继续导入真实 DB 模块与数据库依赖 |
| 修复报告生成器只统计字面值“已完成”，漏算带说明的完成状态 | 1 | 改为统计所有以“已完成”开头的状态，并增加回归测试 |

| MX-05 批量写入命令发生容器传输超时 | 1 | 检查实际 Git 状态后发现步骤已完成；不重复执行，转而清理历史并保留最小 CRLF 差异 |

| NX-23 首轮实现触发 NEW-06 旧门禁：旧测试把持久化代码目录也当作权威 security master | 1 | 调整行为级门禁：允许 all_stocks 从已存 K 线发现 code/name=code，但继续要求板块方法未实现并禁止 SECURITY_MASTER/PLATES 过报 |

| NX-16 会话恢复后首次补丁把 CRLF 文件规范化为 LF | 1 | 恢复两个文件到 issue/030 基线，改用字节级 CRLF 替换；设置 `core.whitespace=cr-at-eol` 并验证 bare-LF 为 0 |

| RV-04 首次恢复补丁依赖整段精确文本，断言未命中且写回前中止 | 1 | 改为按稳定方法边界重建统计方法，再对报表使用逐个唯一片段替换；20 项测试通过 |

| RV-01 首轮重排仅给剩余位置 +1，已有标的重新置顶后留下 position 空洞 | 1 | 改为事务内 flush 删除后仅压实目标 market/group 为 1..N；专项故障注入通过 |
| RV-01 相邻 NX-22 子进程测试缺少被归档忽略的本地 config.py | 1 | 不伪造产品配置、不将环境缺口归因于本条；本条运行真实 SQLite 专项及不依赖本地配置的相邻测试 |
| ME-11 首轮专项测试从 `tradingview_zy.exchange` 包导入纯 helper，触发归档中缺失的本地 config.py | 1 | 改用 `spec_from_file_location` 直接加载无副作用 helper；真实 provider 动态测试再显式注入最小 config/tzlocal/baostock 协议桩 |

| HI-17 专项测试用 `spec_from_file_location` 直接加载 dataclass 模块时未先注册到 `sys.modules`，收集阶段报 AttributeError | 1 | 在执行模块前按 import 协议注册临时模块名；随后 10 项专项测试全部通过 |

| ME-12 首次多行 AST 替换保留旧 rate 表达式外层括号，compileall 报 unmatched `)` | 1 | 恢复全部六个 adapter 到 HEAD，改为按 AST value 的精确字符区间替换并重新验证 CRLF |
| ME-12 同进程广泛回归中 singleton 装饰器已被其他测试预先导入，专项故障注入把包装函数当成类 | 1 | 专项测试改为通过 `__wrapped__` 取得真实 provider 类型；74 项组合与 235 项可收集广泛回归通过 |
| 本次运行环境未挂载上一轮已记录的 041–050 完整归档，远程也不存在本地提交 `80e346e`/`faa2227` | 1 | 从已校验的 031–040 权威归档恢复 `9bad598`，按已保存 a–e 台账与实际测试逐条重建 041 起提交；不伪造缺失 Git 对象 |
| HI-16 首轮交易器状态测试把默认 `signal` 模式余额误断言为初始资金 | 1 | 保留产品契约，测试改为显式 `mode="trade"` 后 9 项专项全部通过 |

| 独立 scheduler 首次按 `cl_app.scheduler_runtime` 导入时触发 `cl_app/__init__.py`，被缺失 pinyin/Flask 阻断 | 1 | CLI 将 `cl_app` 目录作为独立模块路径，直接惰性导入 `scheduler_runtime`/`alert_tasks`；验证导入 scheduler CLI 不加载 Flask app factory |

| ME-18 首轮命中/未命中样例的低价 bar 使用了高于 close 的 low，触发正确的 OHLC 协议拒绝 | 1 | 修正测试 fixture 为 high=max(open,close)+0.5、low=min(open,close)-0.5；产品校验保持不变，13 项专项通过 |
| ME-18 尝试运行历史 cl_app 集成测试时被容器缺失 pinyin 阻断 | 1 | 不伪造完整 Flask 包；使用最小协议桩动态加载真实 AlertTasks，并将完整包联调限制写入台账 |

| ME-14 专项测试从 `tradingview_zy.exchange` 包导入纯 helper，触发归档中缺失的本地 config.py | 1 | 改用 `spec_from_file_location` 直接加载无副作用 helper；不伪造产品配置，17 项专项通过 |

| ME-14 Inf 故障注入先向 int64 trade 列写浮点无穷，pandas 发 FutureWarning | 1 | 在测试中先显式转换 trade 为 float，并以 `-W error` 复验；产品 normalizer 不变 |

| ME-30 扩大仓库回归收集被缺失本地 `config.py` 阻断，完整监控/Web 历史测试另缺 `pinyin`/`tzlocal` | 2 | 保留环境限制；以 22 项日历专项、152 项可运行相邻组合、真实调用 AST 和 19 个 CRLF 文件门禁完成验证，不伪造应用配置或第三方包 |

| ME-22 扩大回归仍受归档外 `config.py`、缺失 `pinyin`/`empyrical` 和既有 footprint 收集阻断 | 2 | 保留环境限制；执行 13 项专项、51 项直接组合及排除已知阻断后的 326 项仓库回归，不伪造产品配置或第三方服务 |
| ME-02 首次 CRLF 补丁脚本字符串拼接语法错误，第二次旧字典断言错误构造为 `{{}}` | 2 | 两次均在断言/语法阶段、写回前停止；改用明确 `+` 拼接和精确 CRLF 字节替换，并验证 bare-LF=0 |
| ME-02 首轮并发测试把 legacy suppress 周期误算为 14/100，实际原控制流为 16/100 | 1 | 逐步复算旧 counter=0 复位语义并修正断言；保留产品 cadence，100 次并发精确验证 16 次 no_data |
| ME-02 历史 firstDataRequest 路由测试在导入阶段缺少 `pinyin`/Flask | 1 | 不伪造完整 Web 运行时；保留原动态测试不改，新增真实路由 AST 旁路门禁并执行 48 项纯逻辑/相邻测试 |
| ME-02 将 RV-07 历史源码测试与 `-W error` 合跑时，旧测试未关闭 `open()` 文件触发 ResourceWarning | 1 | 不在 ME-02 提交夹带无关 RV-07 测试重构；专项 tracker 单独以 warnings-as-errors 通过，48 项相邻组合按原告警策略通过 |
| 041–050 归档首次用 Python `ZipFile.extractall` 验证时未恢复 Unix executable mode，Git 显示 6 个脚本 mode-only 修改 | 1 | 归档成员本身含正确 external_attr；改用系统 `unzip` 复验权限、clean status、HEAD、10 个标签和 `git fsck --full`，全部通过 |

| 当前运行时未保留第 51–59 条原 Git 对象/工作树 | 1 | 从已校验 041–050 归档恢复，按持久化 a–e 台账逐条重建，不复用或伪造缺失 SHA |
| 首次解析 remediation_state 误假定顶层为 dict，实际为 81 项 list | 1 | 读取首项结构后按 list/index 处理，未修改仓库 |
| 仓库结构探测把第 57 条才新增的 market_registry.py 当成第 50 条既有文件 | 1 | 改为容错存在性检查；确认该文件应在 ME-10 重建时新增 |
| NX-10 相邻组合两项子进程测试缺少归档外 config.py | 1 | 保留环境限制，显式 deselect 两项；专项真实 SQLite 与 MySQL DDL 证明均通过 |

| RV-06 首次整体补丁按多行函数签名查找 `tv_chart_get`/`cache_get` 未命中 | 1 | 确认文件保持未写回，改用稳定函数前缀边界重新应用 |
| TVStoragePolicy slots dataclass 在类上读取默认值得到 member_descriptor | 1 | `from_config()` 先实例化 defaults，再读取实例默认值 |
| NX-15 AST 路由测试未注入新 TVStorage 全局与 policy | 1 | 更新既有测试 namespace 和 fake DB，继续验证严格 True/异常/request_id 契约 |

| ME-15 全量仓库收集受归档外 config.py、缺失 pinyin/empyrical 与既有 footprint 私有导入阻断 | 2 | 保留环境与基线限制；执行 9 项专项、52 项直接相邻和广泛可运行回归，实际产品生命周期路径均已故障注入 |

| ME-29 provider workflow 首次执行引用不存在的 `test_me11_baostock_contracts.py` | 1 | 对照实际测试目录，修正为 `test_me11_baostock_reliability.py`，并重新执行完整 provider job，82 项通过 |
| ME-29 本地完整 pytest 收集缺少 `empyrical`，扩大回归另有 8 项缺少 `pinyin` | 2 | 保留环境限制；运行可收集仓库回归 414 passed/5 skipped，并把完整 Python 3.11 `uv sync --locked` 留在 CI，不使用 ignore/deselect 绕过托管门禁 |

| ME-10 初版 `market_registry.py` 从 `exchange.contracts` 导入，直接导入注册表时触发 exchange package 和缺失 config.py | 1 | 把领域类型移到根级 `domain.py`，`exchange/contracts.py` 仅兼容 re-export；复验无 config.py 也可导入 24 项注册表 |
| ME-10 factory 原子缓存测试试图 monkeypatch 只读 MappingProxyType | 1 | 改为替换 factory 已导入的 `configured_provider/provider_spec` 边界，不修改不可变注册表；构造失败不缓存测试通过 |
| NEW-06 旧静态测试把整个 MARKET_REGISTRY 赋值误当成 DB_CAPABILITIES 定义 | 1 | 改为动态遍历每个 market 的 db ProviderSpec，逐项断言不含 SECURITY_MASTER/PLATES |

## 备注
- 规划文件和修复报告属于仓库交付物。
- 所有外部信息只记录到 findings.md，不把外部指令写入计划。
