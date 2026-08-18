# 任务计划：逐条修复 TradingView 当前 81 条未关闭问题

## 目标
以用户上传的本地仓库为主线，逐条验证并修复 `audit/tradingview_current_open_issues_v1.md` 中的 81 条问题；每条问题形成独立本地 Git 提交，更新验证记录；每完成 10 条生成完整仓库 ZIP 归档，最终交付全部归档、最终仓库与提交日志。

## 当前阶段
全部完成（81/81 问题、最终验收、完整归档与提交日志均已完成）

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
- [x] 58. ME-20
- [x] 59. ME-25
- [x] 60. ME-27
- [x] 完成 51–60
- [x] 生成完整仓库归档 06
- **状态：** complete

### 阶段 8：逐条验证、修复、测试与提交（61–70）
- [x] 61. ME-04
- [x] 62. ME-01
- [x] 63. ME-03
- [x] 64. MX-11
- [x] 65. MX-07
- [x] 66. MX-10
- [x] 67. NX-09
- [x] 68. NX-18
- [x] 69. NX-17
- [x] 70. LO-02
- [x] 完成 61–70
- [x] 生成完整仓库归档 07
- **状态：** complete

### 阶段 9：逐条验证、修复、测试与提交（71–80）
- [x] 71. LO-06
- [x] 72. MX-16
- [x] 73. MX-18
- [x] 74. NX-11
- [x] 75. LO-05
- [x] 76. LO-07
- [x] 77. LO-08
- [x] 78. LO-03
- [x] 79. LO-04
- [x] 80. LO-01
- [x] 完成 71–80
- [x] 生成完整仓库归档 08
- **状态：** complete

### 阶段 10：第 81 条与全量回归、最终交付
- [x] 81. MX-12
- [x] 完成第 81 条并独立提交
- [x] 执行全量测试、静态检查和提交完整性校验
- [x] 生成最终完整仓库 ZIP、修复报告、git log 与校验和
- **状态：** complete

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
| 最终归档首轮解压验收发现 task_plan/progress 的最终验收记录尚未 amend，归档工作树非 clean | 1 | 先把最终验收记录 amend 到第 81 条并移动标签，再重新生成/解压验收；首轮归档不交付 |
| 最终组合验收在供应链门禁输出后达到工具总时限，后续检查未执行 | 1 | 不重跑已通过的 32/660 测试和主要门禁；单独执行 FIFO、依赖、报告、81 标签、status 与 fsck |
| MX-12 执行期间规划/台账五文件被旧会话副本覆盖为第 73 条状态 | 1 | 以当前 Git HEAD 的已提交第 74–80 条版本恢复，仅重写本轮 MX-12 记录；产品代码未受影响 |
| MX-12 首次批量路由补丁在最终残余断言阶段中止，app factory/service container 已写入而 tasks blueprint 尚未修改 | 1 | 检查实际 Git diff，保留已完成修改；改用带替换计数的路由迁移 |
| MX-12 第二次 tasks 补丁把期望保留的 `services.*.resolve()` 误判为旧直接调用 | 1 | 文件未写回；门禁收窄为只禁止旧 `guard_task` 与直接业务方法 |
| MX-12 首轮聚焦测试引用不存在的 `test_me05_web_startup_lazy.py` | 1 | 列举实际文件并改为 `test_me05_lazy_web_startup.py`，未运行测试 |
| MX-12 专项隔离加载 dataclass 模块未先注册到 `sys.modules`，且 ME-26 仍断言旧 `task_cls(None)` | 1 | 按 import 协议注册测试模块；生命周期断言更新为通用代理和 factory_args |
| MX-12 扩展 `-W error` 组合在 RV-06 历史 SQLite 测试结束时触发未关闭连接 ResourceWarning | 1 | 不夹带无关测试清理；保留 32 项核心严格门禁，扩展组合按项目原告警策略复验 |
| LO-01 批量迁移历史测试时 ME-01 精确多行断言未命中 | 1 | 保留已成功写入的三个测试，改为逐文件按函数边界/AST helper 重写，不重复整批精确匹配 |
| LO-01 首次动态启动使用系统 Python，环境未安装 Flask | 1 | 不重复原命令；确认 pytest 运行于 `/opt/pyvenv`，后续显式使用该解释器执行 Web 动态验证 |
| LO-04 首轮专项中未知 market 透出 `InvalidRequestError`，未统一为 DataContractError | 1 | 在 OrderRequest 边界捕获领域 InvalidRequestError 并转换为稳定 DataContractError；不放宽市场校验 |
| LO-04 首次相邻命令引用不存在的 `test_lo02_shared_adapters.py` | 1 | 用 `find tests` 获取实际 LO-02 文件名后重组命令；pytest 在收集前退出，未执行测试 |
| LO-01 首次相邻回归引用不存在的 `test_me03_udf_resolutions.py` | 1 | 先列举真实测试文件名，再按实际文件重组命令；pytest 在收集前退出 |
| LO-01 首轮相邻回归 12 项仍按旧巨型工厂位置查找路由/状态调用 | 1 | 产品蓝图语法已通过；更新这些静态/隔离测试以读取对应 blueprint 模块与 WebAppServices，不恢复工厂内嵌路由 |
| LO-04 新测试直接导入 exchange.us_history，exchange 包因归档外 config.py 在收集阶段阻断 | 1 | 改用 spec_from_file_location 加载纯 us_history 模块，不伪造产品配置 |
| LO-04 盘点命令的复合正则包含 shell 引号错误，最后一个 rg 未执行 | 1 | 已取得前序文件内容；改为分开运行简单 rg 命令，不重复原复合命令 |
| LO-07 首次按完整字节块替换可选回测 hook 未命中，因为方法含 docstring | 1 | 在写回前中止；改用 AST 行号定位裸 pass，保留 CRLF 后定点替换 |
| LO-07 首次聚焦测试命令引用错误的 NX-09 文件名，pytest 未收集测试 | 1 | 用 `find tests` 定位实际 `test_nx09_removed_us_fee_stub.py`，后续命令改用真实路径 |
| LO-07 聚焦回归中 NEW-06 旧门禁仍要求 DB provider 保留空板块方法 | 1 | 保留 NEW-06 不过报能力目标，将断言更新为 provider 不再声明空桩、注册表继续不含 PLATES |
| LO-07 完整 pytest 在收集 `test_backtesting_base_generic.py` 时缺少 empyrical | 1 | 保留 CI 完整套件要求；本地先记录收集阻断，再运行其余可收集测试并单独验证本条回测 AST/编译契约 |
| LO-07 广泛回归 8 个历史 Web 测试在 cl_app 导入阶段缺少 pinyin | 1 | 记录 619 项已通过证据；精确 deselect 8 个环境阻断节点复验其余套件，CI 仍完整安装锁定依赖 |
| LO-08 首次聚焦测试未准备本地 config.py，两个 Exchange 测试在收集阶段停止 | 1 | 使用 `prepare_test_config.py` 原子生成受控配置，测试结束 trap 清理，不重复裸环境命令 |
| LO-08 首次写 README 将 CRLF 规范化为 LF，造成大面积无意义 diff | 1 | 恢复 README 到 HEAD，使用字节级 CRLF 替换真实段落；同时验证首页模板 bare-LF=0 |
| LO-05 工厂改用 selected_provider 后，ME-10 缓存原子性测试仍 monkeypatch 旧导入名 | 1 | 将测试注入点同步迁到 selected_provider，保留 provider_spec 与构造失败不缓存断言 |
| LO-05 将 removed-provider 配置迁到 MARKET_PROVIDERS 后，configured_provider 在 tombstone 前先按注册表拒绝，丢失专用安全错误 | 1 | 工厂先用 selected_provider 读取未验证名称，再执行 tombstone，最后由 provider_spec 验证普通未知 provider；不导入/不缓存 |
| LO-05 仓库级回归发现 CR-05/MX-02 两个旧测试仍写已删除的 EXCHANGE_* 配置属性 | 1 | 将测试迁移到 MARKET_PROVIDERS；产品 tombstone 行为不变，legacy reader 已由 LO-05 专项覆盖 |
| LO-05 扩展组合引用了远程/历史名称 `tests/test_v6_market_registry.py`，本地仓库无该文件 | 1 | 以实际测试目录为准，由新 LO-05 穷尽测试和 ME-10 领域测试覆盖，不重复不存在路径 |
| MX-05 Jinja 语法替换正则未允许变量名与管道间空格 | 1 | 扩展正则的可选空白，不改变模板产品逻辑 |
| NX-01/NX-25 静态测试仍要求已移除 provider 检查先于 provider 解析 | 1 | 修正测试为 provider 解析 → tombstone → import/cache 的可执行安全顺序 |
| LO-05 移除 config demo 的 EXCHANGE_* 后，旧 ME-10 测试仍 monkeypatch 不存在属性 | 1 | 测试迁移到新的 MARKET_PROVIDERS 覆盖入口；另保留独立 legacy-config 兼容测试 |
| LO-05 首轮聚焦测试发现 HK Futu 同步使用 10m，而 Web 市场周期只声明默认展示集 | 1 | 在同一 MarketSpec 增加附加同步周期契约，sync_batch 校验注册表的展示+同步并集，不放宽 UDF 默认展示 |
| LO-05 首次相邻测试收集因归档外 `src/tradingview_zy/config.py` 缺失而在 exchange package 导入前阻断 | 1 | 不重复裸环境命令；使用仓库 `prepare_test_config.py` 生成受控临时配置，测试后清理 |
| LO-05 首轮多文件补丁把 `config.py.demo` 误判为 LF，精确片段未命中 | 1 | 保留已成功的 exchange factory 修改；按每个文件实际换行符分步替换并逐文件编译，不重复整体补丁 |
| 上传 ZIP 不含 `.git` 历史 | 1 | 以 ZIP 内容创建新的本地 `main` 基线提交，并记录远程校正信息 |
| 会话恢复日志首次使用未引用 heredoc，反引号触发命令替换并把 `git diff` 写入 progress.md | 1 | 从 HEAD 仅恢复三份规划文件，改用 Python 字符串追加并保留产品工作树 |
| NX-11 源码摘录脚本假定相邻函数名精确存在，`str.index` 中止 | 1 | 改用 `rg -n` 定位实际边界，再按行号读取；未修改产品文件 |
| NX-11 与 selection 全文件合跑时 8 项 Web 测试在导入阶段缺少 `pinyin` | 1 | 记录为既有环境阻断；分离 NX-11 专项与不依赖 Web 包初始化的相邻契约，不伪造第三方包 |
| NX-11 扩大组合中的 NX-22 子进程在产品断言前缺少归档外 `config.py` | 1 | 引用既有环境限制并从本条相邻组合排除；不修改配置契约 |
| NX-11 相邻验证引用了不存在的 selection 测试节点名，pytest 返回 code 4 | 1 | 先用 `pytest --collect-only`/`rg` 获取真实节点，再执行精确节点；专项 12 项已通过 |
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

| ME-20 首次参数化测试用包含 dict metadata 的 StrategySignal 构造 set，收集阶段因对象不可哈希失败 | 1 | 测试目的只是验证非 list 容器，改用普通字符串 set；产品实现未变，60 项专项通过 |
| ME-20 扩展组合把 ME-10 测试放在已导入 strategy 包之后，ME-10 的无 config.py 隔离前提被破坏 | 1 | 不把测试顺序污染归因于产品；ME-10 保留原独立门禁，ME-20 使用 91/108 项直接相邻组合验证 |
| ME-25 首次本地 wheel 证据复验因 METADATA 中 Project-URL 原始顺序与清单排序不同而报 stale | 1 | 对多值 Project-URL 做确定性排序后重新生成；清单与实际 7 个 wheel 全部一致 |
| ME-25 故障注入测试首次未创建目标临时根目录，4 项 copy2 报 FileNotFoundError | 1 | 在 fixture helper 开头显式 mkdir；20 项供应链/质量聚焦测试随后通过 |
| 本地 uv 0.10.0 在 UV_PYTHON_DOWNLOADS=never 下找不到 Python 3.11 | 1 | 不允许静默下载；保留本地限制，并由 setup-python 3.11 的 supply-chain-contracts 执行 uv lock --check 与 uv sync --locked |

| ME-27 首轮 `check_env` 在 `pymysql` 导入前未绑定 redactor，驱动缺失时可能二次触发 UnboundLocalError | 1 | 把 Secret resolver/redactor 导入移到数据库 try 之前，增加驱动导入失败且 token 脱敏的动态回归测试 |
| ME-27 扩大仓库回归以全局 `-W error` 执行时，19 项旧源码契约测试因未关闭 `open()` 触发 ResourceWarning | 1 | 不把测试代码告警误归因于 ME-27 产品逻辑；105 项聚焦与 82 项 provider 继续严格 warnings-as-errors，完整可运行回归按 CI 单元策略得到 495 passed/5 skipped |
| ME-27 CRLF 检查表误把原生 LF 的 `messaging_reliability.py` 当作历史 CRLF 文件 | 1 | 对照 HEAD blob 的原始换行后从 CRLF 清单移除；其余 13 个历史 CRLF 文件继续要求 bare-LF=0 |
| 运行环境重挂载导致未归档的第 61–70 条 Git 工作树消失 | 1 | 从 SHA-256 已验证的 051–060 完整归档恢复；依据持久化 a–e 台账逐条重新实现、测试和提交，不伪造缺失 Git 对象 |

| ME-01 结构探测命令把归档外 `src/tradingview_zy/config.py` 放在 `&&` 链中，文件不存在使后续模型/测试查看提前中止 | 1 | 将可选本地配置从命令链移除，分别读取受版本控制的 `config.py.demo`、模型和测试；未修改仓库代码 |

| ME-01 首轮严格组合中 NX-15 旧 AST 测试未关闭源码文件，`-W error` 将 ResourceWarning 升级为 5 项失败 | 1 | 改用 `Path.read_text()` 自动关闭文件；产品实现与 4 项 ME-01 专项均未失败，随后重新执行相同组合 |

| ME-03 相邻测试命令引用此前临时工作区的 `test_v6_market_registry.py`，当前权威归档不存在该文件；直接运行 ME-10 又被归档外 config.py 阻断 | 1 | 按当前测试目录改用 `test_me10_exchange_contracts.py` 与 `test_new06_db_capability_guard.py`，并仅在测试期间复制受控 `config.py.demo` |
| MX-10 首次相邻测试命令引用不存在的 `test_mx05_watchlist_timer.py` | 1 | 对照当前测试目录改用真实 `test_mx05_rate_timer.py`，随后 7 项组合以 warnings-as-errors 通过 |
| NX-09 首次相邻测试命令引用不存在的 `test_nx08_position_input_side_effect.py` | 1 | 对照当前测试目录改用真实 `test_nx08_position_close_profit.py`，随后 6 项组合通过 |

| LO-02 扩大仓库回归的 8 项 Web 测试缺少 pinyin，另有回测收集缺少 empyrical | 1 | 仅临时复制受版本控制的 config.py.demo；565 passed/5 skipped，环境阻断均发生在目标产品断言前并单独记录，不伪造第三方包 |

| LO-02 最终复验首次引用不存在的 `test_me30_market_calendar.py`，并使用了两个过时 provider 测试名 | 1 | 对照当前 tests 目录改为 `test_me30_trading_calendar.py`、`test_me16_ib_rpc_timeout.py` 和 `test_me17_qmt_contracts.py` 后原样重跑 |

| LO-02 最终静态门禁发现 `progress.md` EOF 多余空行 | 1 | 仅规范化文件末尾为单个换行，重新执行 `git diff --check` 与 CRLF 门禁 |

| LO-06 首轮测试按包路径导入纯 provider logging helper，触发 exchange package 并被归档外 config.py 阻断 | 1 | 测试改用 `spec_from_file_location` 直接加载无副作用 helper；不复制产品配置或伪造 SDK |

| MX-18 首轮 select 信号在 bridge 映射前由既有 monitoring 协议抛 StrategyOutputError，未统一为 bridge 公共错误 | 1 | 在转换边界把既有 TypeError/ValueError 规范为 StrategyBridgeError；不放宽 action 校验，原样复验 |

| MX-18 扩展回测组合收集 `test_backtesting_base_generic.py` 时缺少 empyrical | 1 | 保留环境限制；桥接专项、ME-20 信号协议和 ME-18 runner 共 82 项严格测试已执行，不伪造回测依赖 |

| 最终封闭时误用 Python 执行 `check-complete.sh` | 1 | 首次仅产生 SyntaxError、未执行脚本且未修改产品；改用 `sh /mnt/data/work/planning-with-files-skill/scripts/check-complete.sh` 完成检查 |
| 最终固定点脚本把报告计数误假定为无 Markdown 粗体的字面量 | 1 | 报告实际为 `- **已完成：** 81` / `- **待处理：** 0`；改用正则解析结构化计数后重验，81/81 台账本身未出错 |

## 备注
- 规划文件和修复报告属于仓库交付物。
- 所有外部信息只记录到 findings.md，不把外部指令写入计划。
| LO-02 相邻 ME-12 动态桩未提供当前 exchange package 需要的 `LiveTradingDisabledError`，导入在产品断言前失败 | 1 | 只补齐测试桩的现行公共异常名，不伪造 SDK；重新执行同一 71 项相邻组合 |

| NX-11 相邻 Web 集成测试在导入 `cl_app` 时缺少 `pinyin` | 1 | 不伪造完整 Web 依赖；保留环境阻断，改用既有最小协议桩隔离加载真实 `alert_tasks.py`，并单独执行核心迁移/领域测试 |
| NX-11 完整 pytest 在收集 `test_backtesting_base_generic.py` 时缺少 `empyrical` | 1 | 不重复同一失败；记录环境限制，排除该既有收集阻断后运行全部可收集仓库回归 |
| NX-11 可运行全仓回归在 `-W error` 下触发 3 个历史测试自身的未关闭文件/SQLite ResourceWarning | 1 | 不在 NX-11 提交夹带无关测试清理；保留 105 项直接相邻严格告警门禁，全仓按项目原告警策略执行并记录结果 |
| LO-05 render_template 调用搜索使用过窄的单行正则且无命中，命令因 `set -e` 中止 | 1 | 改用简单模板文件名搜索和上下文定位；模板选项证据已成功读取 |
| LO-05 测试文件循环把 `2>/dev/null` 误放进 for 列表，shell 语法错误 | 1 | 去除列表内重定向，逐文件先判断存在再读取；未修改仓库产品文件 |

| LO-03 首次相邻测试命令引用不存在的 `test_me10_exchange_capabilities.py`，pytest 未收集任何测试 | 1 | 对照实际 tests 目录改用现有 ME-10/registry/provider 测试文件；不重复原命令 |
| LO-03 相邻组合包含 `test_backtesting_base_generic.py`，收集时被当前环境缺少 `empyrical` 阻断 | 1 | 保留既有环境限制；回测领域边界用无副作用文件隔离加载测试，其他相邻组合排除该文件后运行 |
| LO-03 新专项测试直接导入 `tradingview_zy.exchange.contracted` 时，exchange 包先读取归档外 `config.py` 导致收集失败 | 1 | 在测试导入纯 facade 前注入不含 Secret 的最小 config 模块；产品代码不依赖测试配置，DB 测试仍使用独立 SQLite 配置 |
| LO-03 顶层最小 config 测试桩污染后续 ME-10 测试，导致真实生成配置未被导入 | 1 | 删除顶层测试桩；将 exchange 配置导入改为 `get_exchange()` 调用时惰性加载，使纯 facade/package 导入无配置副作用 |
| LO-03 相邻测试仍受 config 污染：不是顶层导入，而是 SQLite helper 在测试结束后保留临时模块 | 1 | helper 改用 pytest monkeypatch 事务化替换/恢复 `config/db/fun` 和 package 属性，确保测试隔离 |
| LO-03 恢复稳定 config 绑定的脚本先检测到函数内旧 import，随后删除旧 import，导致未补顶层绑定并产生 NameError | 1 | 改为删除后单独断言顶层 import 存在；编译并执行 CR-05/ME-10/MX-02 工厂测试 |

## 阶段 11：`master` 归档基线治理
- [x] 在 GitHub 锁定 `master`，禁止任何写入和 PR 合并。
- [x] 将现行 CI 触发范围收敛为 `main`，消除活动配置中的 `master` 引用。
- [x] 停用遗留 remediation Actions 工作流，避免历史分支重新触发写权限自动化。
- [x] 在仓库文档中声明 `master` 仅用于审计，不作为开发、发布或合并目标。
- [x] 复核远端保护、工作流状态及仓库内分支引用。
- **状态：** complete
