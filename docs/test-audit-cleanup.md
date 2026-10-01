# 测试精简与行为边界核查

基线：`ed1f35f`；日期：2026-10-01。仅改工作区，不提交或推送。

## 编辑前证据：浏览器与门禁

| 原测试/位置（基线） | 可捕获失败与问题 | 生产调用/保留证明 | 历史、清理、风险与验证 |
| --- | --- | --- | --- |
| `test_me29_quality_gates.py:126::test_footprint_uses_public_timestamp_api` | 捕获 import 拼写，不保证实际使用；等价模块导入会误失败 | UDF footprint 路由调用 `aggregate_footprint`；`test_footprint` 实际验证 epoch、分段归属与守恒，`test_web_payloads` 验证市场本地化 | `9c97784` 为质量门禁引入；仅删测试，公开 helper 仍有生产调用；跑上述三个文件 |
| `test_me25_supply_chain.py:39::test_current_repository_supply_chain_contract_and_generation_are_deterministic` 内组件数153 | 合法依赖调整误失败，等数量错误内容漏报 | CI 调用 supply-chain 校验/生成器；保留完整校验、两次生成字节确定性、篡改/过期负例 | `bfd9bc1` 引入供应链证据；仅删库存断言，不删生成器；跑整个 supply-chain 文件及两个CLI |
| `test_cleanup_frontend_static.py:15::test_content_table_style_has_no_global_table_selectors` | 固定四行字符串不证明无全局样式 | 真实页面加载 app.css；保留/扩充 `test_content_table_style_is_opt_in` 的 Chromium computedStyle，对 table/tr/td/th 验证选择性生效 | `ed1f35f` 新增；仅删CSS源码项，百度统计禁令保留；Chromium 测试必须通过 |
| `test_me29_browser_dom.py:17::test_rendered_settings_dom_never_contains_existing_secret` | 离线模板且删掉脚本，不证明真实请求/JS运行后隐私 | `/setting`、`/setting/save` 真实蓝图与SQLite；并入 CSRF 浏览器组，保留代理字段、保存/重载、旧密钥不出现在DOM/控制台/响应的观察 | `9c97784` 引入，`00ea000` 补CSRF模板上下文，`ed1f35f` 退役飞书；替代通过后删除整个旧文件，同步CI/checker；不得削弱Chromium门禁 |

新增/扩充断言不引入生产专用接口：浏览器支撑只在临时数据库预置代理和旧密钥，所有脚本、路由和持久化使用生产代码。独立风险为浏览器执行后的DOM、控制台、表单传输和CSS作用域，不能由模板字符串测试覆盖。

## 保留决策

- 本地 pytest 的 readability/hygiene/dependency/quality/secret-exposure 正向入口保留；避免仅运行 pytest 时失去仓库级检查。
- 安全退役约束、TLS禁令、真实平台/迁移/事务/供应链负例保留。
- 不为减少测试数量删除仍有非测试调用的生产接口。

## 核心路由与选股

- ME02 (`6516be0`) 原用 AST 证明 tracker 调用；现执行真实 `/tv/history`，保留首次请求旁路、跟进节流响应和用户/IP/市场/代码/周期隔离。TTL/LRU/并发 helper 测试保留。
- ME03 (`1ac4df8`) 原保护漏掉纽约期货周期问题；现注入两个市场独有周期，验证 `/tv/config` 实际响应的并集，不再锁定源码变量。
- ME04 (`184efe5`) 原用 AST 顺序证明 payload 预处理；现验证 naive 日期的本地化/窗口过滤，以及缺成交量、代码/周期不匹配的稳定错误响应。
- `test_selection_monitoring.py` 的旧 clear/add 观察字段漏迁移源于 `118b161`；改查真实 replace 快照，删除失效 fake 方法，保留无目标组不得写入的契约。
- 新增共享 `test_support/isolated_web_app.py`，仅在子进程从 demo 构造临时 SQLite 配置，无生产注入接口。各生产 owner 均有真实路由/任务调用，本批不删生产代码。
- 核心组及相邻 payload/原子选股测试：51 passed；11 种真实 owner 临时故障均被新断言捕获，随后逐字节恢复。

## 工具链与平台

- 环境检查 (`8650431`) 改为临时目录完整 CLI，独立预期覆盖配置失败、合法/非法版本、可选服务降级；代理检查验证无 telnetlib 仍能工作、连接关闭及有界超时。不再执行开发者本地服务，也不再由被测 helper 生成预期。
- Windows 两启动器使用真实 cmd.exe 与同一个 fake-uv 支撑，验证失败码37、默认等待确认及 NO_PAUSE 非交互退出；加入 Windows CI 和质量门禁。
- 密钥原子轮换 (`88c3d8c`、`docs/secrets.md`) 在现有版本/权限测试中补发布失败注入，验证旧版本不变、新版本不可见、临时文件清理。
- MySQL 用例准确改名为 current-schema/long-text round trip，不再声称证明旧 schema 升级；真实 MySQL 门禁保留。本机无 docker/mysqld 命令，未连接现有数据库替代测试服务。
- FIFO (`0ffe665`) 完整脚本/调用/历史核查确认：无当前生产对象和独立 CI 入口，三个测试仅测试指定调用名的源码行号。删除 `test_new05_fifo_atomicity_guard.py` 与75行 scanner；更新活跃架构文档，历史审计记录保留。未来引入FIFO必须在结算边界证明失败原子性，不代表永久放弃该功能。
- 工具链及相关文档：32 passed / 1 skipped（MySQL）；吞退出码、不关代理连接、遗留临时密钥、去掉暂停、吞启动器错误码五组临时故障均被捕获并恢复。

## 行情与架构

- LO02 (`de35f67`) 与 LO04 (`b4a182f`) 的美股适配器源码 grep 合并为 `test_us_provider_history.py`。真实 `StockBarsRequest`/`BarSet`/`Agg` 类型进入真实 `klines`，分别验证请求时区、周期、SDK时间单位、OHLCV字段与排序去重；客户端仅替代网络传输，未复制被测算法。
- LO07 (`901b760`) 默认 hook 不再锁定 `return None` AST；真实策略子类调用后检查返回和两侧状态不变，生产回测调用仍保留。
- B18 空结果场景迁入 B5 的六适配器缓存矩阵，保留单次连接/调用、关闭连接、参数不变及日线pages=1输入；共享fake仍有其他测试调用，保留。
- cleanup 日线文件删除，变化OHLCV、上海07:59/08:00边界迁入 B12 的多时区/闰日/3h测试；使用内部极值以区分 max/min 与 first/last，不删除转换器。
- ME12 (`9bad598`) 四provider日历断言完全包含于 ME30 (`66f1d11`)，删除重复函数与专属map；保留ME30架构契约和实际日历运行行为。
- 本批265 passed（严格警告）；SDK文件单独4 passed。九种临时故障（单位、映射、周期、修订去重方向、hook状态、日线high/low、连接泄漏、空数据误返回旧缓存）全部被捕获并恢复。生产代码零修改。

## Web、退役能力与数据库

- CR02 (`668f0eb`) 整文件删除：公网绑定/私有密钥持久化由 `test_web_security.py` 承担；代理DOM字段迁入 B4，浏览器实际保存/重载另在 browser gate。B4 的不读取、不改写旧凭证与 secret-exposure 门禁保留。
- NX01 (`a3d844d`) 和 NX25 (`9692fb9`) 的 CTP/ZB 退役清单与引用扫描，分别重复 CR05 (`9b74148`) 和 MX02 (`a7b3e69`)，只删重复项。前置地址禁令、TLS禁止绕过与恢复要求保留。
- CTP/ZB 工厂源码顺序测试和旧终态测试合并进 CR05：两provider × 冷缓存/匹配provider缓存/不同provider缓存，验证真实 `get_exchange` 拒绝，且不导入SDK、不关闭实例、不改动当前或其他市场缓存。消除全局cache清空与过时tzlocal替身。
- MX04 (`75fda23`) 的 None/pass AST禁止项被同文件实际执行后严格False契约包含；NX18 (`93c4136`) 的const拼写和单独JS语法项被完整脚本的分支/全局泄漏行为测试包含；MX10 (`7793515`) 的单独parse被完整VM加载包含，保留其独立API契约。
- NEW06 (`c380310`) 两个能力声明重复项归并到 ME10 的真实注册表保守能力测试 (`5cfd113`)。NEW06保留文档限制；声明不等于行为，catalog部分另在NX23验证。
- NEW06字典拼写与NX23抽取方法测试 (`fe49f51`) 改为显式临时SQLite的真实插入→`ExchangeDB.all_stocks`：空目录、跨分区/频率去重、市场隔离、code-as-name和不支持plate。删除AST/fake DB，不删仍由搜索/选股调用的生产catalog。
- NX22 (`8d7f4e0`) 删除禁止任何warnings import的源码检查，真实DB导入后验证五类caller warning policy；明确临时数据库配置，删除重复tzlocal替身与不可靠的HOME-only隔离。
- MX05 (`da60532`) 三项合并为实际Jinja渲染并执行全部inline JS，驱动已注册页面启动/折叠回调；验证立即刷新、30秒定时、重复启动替换、关闭、无关面板及重开。
- RV01 (`d43e05b`) 故障样本改为重新插入已存在KEEP，真正触发删除和移位同时回滚；限定IntegrityError及触发器消息。修复fixture的sys.modules/package污染并关闭engine。
- 本批与相邻安全/注册表/生命周期/日历测试65 passed（严格警告）；8种临时故障（工厂晚拒绝/早导入、错误catalog名称、压制FutureWarning、计时器启动/关闭失联、提前提交、JS全局泄漏）全部被捕获并恢复。后续补回冷缓存case以保留旧测试的独立输入分支。

## 验证记录

- 初次工具链/浏览器基线因缺Chromium无法启动；安装对应浏览器后，原定向基线43 passed。
- 合并后的浏览器/工具链/footprint/payload/PineJS 严格警告组：46 passed。
- 浏览器三种临时故障（全局CSS、运行时控制台泄密、丢失代理写入）全部触发预期断言，生产文件已恢复。
- quality/readability/hygiene/dependency/supply-chain/secret-reference/secret-exposure 检查、供应链与provider文档生成物校验、`uv lock --check` 均通过。
- CI 显式安装 Node.js，避免 PineJS 测试因为缺 Node 而静默跳过；本地正向门禁继续保留。
- 集成后的CI行情矩阵及相邻行情测试：340 passed（`-W error`）；Windows/环境检查/真实浏览器组合：59 passed（`-W error`）。
- 对所有改动Python文件运行 Ruff `F401,F811`；清理五个未使用导入后通过。未做全仓格式重排。
- 首轮隔离全量（Web补丁尚未集成）：949 passed / 1 skipped / 1 warning；skip为MySQL opt-in，warning为既有pyfolio缺少可选zipline.assets。
- 最终版本全量：**935 passed / 1 skipped / 1 warning，48.80s**，包含真实Chromium与原生Windows启动器；唯一跳过为真实MySQL服务专项，唯一警告为既有pyfolio缺少可选zipline.assets。
- 独立只读复核发现ME24的`closing`替身不支持合法显式close重构；已改用不连接网络的真实socket。实际验证显式try/finally关闭仍通过、漏关闭会失败，随后恢复源码；最终复核无未修复的确认缺陷。
- 所有本地仓库门禁和生成物检查在最终版本重新通过，Ruff `F401,F811` 通过。`git -c core.whitespace=cr-at-eol diff --check` 通过；保留原有CRLF的选股测试文件，未作全文件行尾转换。
- 测试文件103→100，test函数652→625（不等同于参数化用例数）。测试与支撑 `+829/-874`，净减45行；工具脚本 `+5/-77`，净减72行；业务源码 `src/`、`web/`、环境检查及Windows启动器均无修改。文档和CI变更另计。
- 未提交、推送或创建PR；未执行在线行情/实盘、live OSV网络扫描或真实MySQL测试，不把本地门禁通过等同于远端CI已运行。

### 复现方式

在全新临时checkout中应用本次改动，运行 `python script/remediation/prepare_test_config.py <临时checkout>`，不要覆盖日常工作区的个人配置。使用Python3.11，将临时仓库根、`src`、`web/tradingview_zy_chart`加入PYTHONPATH，安装Playwright Chromium并设置 `RUN_BROWSER_TESTS=1` 后执行：

```text
python -B -m pytest -q -rs -p no:cacheprovider tests
```

各CI专项按 `.github/workflows/tests.yml` 路由执行；真实MySQL专项只可使用独立测试实例/数据库（用例含建表和删表），本轮本机未提供该服务。
