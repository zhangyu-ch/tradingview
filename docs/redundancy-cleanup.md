# 冗余精简实施与验证

基线：`68a56aa`；日期：2026-10-01。按只读审查的 21 项建议实施；不提交、不推送、不访问实盘或个人数据库。

## 实施清单

| # | 精简项 | 实施与保留边界 |
| --- | --- | --- |
| 1 | 存储路由重复规范化 | 图表、模板、绘图由 DB 在事务前执行权威 payload 校验；路由保留 owner 绑定、必填参数及 HTTP 错误映射。 |
| 2 | history 重复准备行情 | `klines_to_tv_history` 一次完整 prepare、一次时间戳转换，再过滤并列式输出；公共 helpers 仍独立校验，窗口外坏行不能被隐藏。 |
| 3 | 监控旧 runner fallback | 删除不可达的接口探测和逐代码 fallback；保留 `BatchRunResult` 协议检查。 |
| 4 | 策略参数重复解析 | 已验证 `StrategyParameters` 直接进入共享序列化函数；保留最终 32 KiB、UTF-8/NUL 与异常映射。 |
| 5 | runner 重复循环和 target 校验 | 两个 runner 共用 `run_strategy_batch`；内部 target 只校验一次，对外 `run_strategy_target` 仍检查手工构造对象。 |
| 6 | Binance 三段重复流程与排序 | 引入仅含行情逻辑的 `BinanceKlinesMixin`、周期表和帧构建函数；现货不继承合约，客户端、DB 市场和账户能力独立；保留缓存合并去重。 |
| 7 | 五个 ExHq ticks 副本 | 统一 `fetch_exhq_ticks`，保留单连接、转换函数、请求顺序、空报价与异常传播；不合并 A 股及 `all_ticks`。 |
| 8 | TDX 拼接后重复排序去重 | 删除 HK/FX/futures/NY futures 紧随共享刷新器的重复处理；日期修正、周期合成等必要处理保留。 |
| 9 | 四份相同平仓规则 | 两个公开 close hook 共用 `_calculate_close`，删除相同 mode 分支；子类仍可独立覆盖多空 hook。 |
| 10 | CSV 读取两次 | `BytesIO` 复用读取快照，解析和校验使用同一份字节；保留元数据降级、坏缓存隔离与未完成 bar 处理。 |
| 11 | 回测全历史扫描和重复排序 | 有序缓存通过 `searchsorted` 与 `iloc` 定位独立窗口；保留各市场 `<`/`<=`、先截窗再滤零成交量、K=0/负值切片语义。 |
| 12 | 回放队列 `pop(0)` | 使用 deque/popleft，删除重复初始化；保留多周期独立消费、耗尽与缓存清理行为。 |
| 13 | 旧路由服务 AST 改写 | 删除全部 32 项服务映射和属性改写器；测试向未改写的真实路由体注入 `get_web_services`。 |
| 14 | 四份 SQLite 测试搭建 | 统一 `test_support/sqlite_db.py`，恢复模块及 package 属性、关闭引擎；迁移测试额外引擎也使用 finally 清理。 |
| 15 | 同步脚本重复门禁 | 合并到 HI17，迁入 HK 完整 universe、期货 max_codes 独有断言；保留真实 import-safe 检查。 |
| 16 | TDX 生命周期重复门禁 | 合并到 NX20，保留共享生命周期、禁止直接 SDK 构造等全部独有断言和真实重试测试。 |
| 17 | CSRF 实现拼写断言 | 删除六条 JS 拼写检查，保留路由 POST、模板要求及真实 Chromium 的 token/跨域/iframe 行为测试。 |
| 18 | 退役路径重复不存在断言 | trader 路径集中于 CR03，other_tasks 路径集中于 MX16；运行引用扫描、实盘禁令和特殊退役契约保留。 |
| 19 | 五个闲置直接依赖 | 移除 dbutils/dtaidistance/gevent/mytt/openai，连带裁去九个独占传递依赖；同步锁指纹、SBOM、许可证及离线漏洞占位证据。 |
| 20 | 退役 AI 前端残留 | 删除无消费者的 marked 资源与加载、两个失效 `#ai_code` 写入；旧私有配置迁移字段保留。 |
| 21 | 多图重复刷新自选 | 页面统一刷新批量切换；图表回调仅为独立的新标的刷新；显式自选成员变更仍可刷新同一标的。 |

## 兼容说明

- `BackTestKlines.loop_datetime_list` 属性名不变，值从 list 改为 deque。仓内调用仅依赖遍历、长度和顺序消费；外部扩展若使用 `pop(0)` 或 `.sort()`，应改为队列接口或显式转 list。不新增隐藏适配层。
- Binance 行情方法的调用签名保留，方法由 mixin 提供。ME10 能力门禁已支持实际导入的具体项目基类，不把通用 `Exchange` 的 unsupported/abstract 方法当作实现，也不为检查而导入可选 SDK。
- 私有策略对移除包的依赖必须由扩展显式声明和锁定，见 [供应链说明](supply-chain.md)。其余锁定包的版本、来源、制品哈希均未改变。
- CSRF、认证、对象归属、配额、事务锁、缓存安全反序列化、策略白名单、实盘 fail-closed 和真实平台门禁不属于删除范围。

## 测试去重与新增回归

测试支撑与旧断言按已有更强覆盖合并，而非以测试数量为目标。新增行为回归针对本次生产改动：

- `test_redundancy_boundaries.py`：真实 Flask+SQLite 的 owner/字段大小/配额/事务前拒绝；窗口外坏行情；手工 target、purpose、失败隔离与配置最终字节边界。
- `test_redundancy_providers.py`：真实 provider 类配内存 transport/cache，覆盖多市场差异、分页/单页、UTC、缓存重叠、有限重试与连接关闭；替代原 Binance 方法抽取与 TDX Tick 拼写检查。
- `test_redundancy_backtest.py`：有序窗口与原可见前缀语义等价、缓存不被返回值修改、多周期队列及公开 close hook；零成交量过滤的独有预期并入窗口矩阵，不重复搭建。
- `test_hi16_file_cache_safety.py`：单次读取、文件替换间隙的同快照校验、损坏隔离及尾 bar 语义。
- `test_mx10_chart_display_contract.py`：加载真实图表/自选脚本与渲染后的页面脚本，1/2/4 图同步及延后事件均只有一次请求，独立切换和显式刷新仍有效。

## 验证记录

- Python 3.11.15、pandas 2.1.0、NumPy 1.26.4、uv 0.10.0；在临时 checkout 从 demo 生成隔离配置，不覆盖日常工作区个人配置。
- 编辑前完整基线：935 passed / 1 skipped / 1 warning。
- 删除依赖后执行全新 `uv sync --locked --offline`，确认被删除的直接包及 httpx/anyio 等传递包确实不存在；前端与依赖变更阶段完整测试 936 passed。
- 最终版本完整测试：1144 passed / 1 skipped / 1 warning，85.83 秒，包含真实 Chromium 与原生 Windows 启动器。唯一跳过为真实 MySQL 专项；唯一警告为已有 pyfolio 缺少可选 zipline.assets。
- 行情、内部边界、真实浏览器、Windows 启动器及供应链组合：106 passed（`-W error`）。
- quality/readability/hygiene/dependency/supply-chain/secret-reference/secret-exposure 门禁、供应链与 provider 文档生成物检查、`uv lock --check --offline` 均通过；全部改动 Python 文件 Ruff `F401,F811` 与 CRLF-aware `git diff --check` 通过。
- ME10 能力门禁以三种内存故障复核：删除共享方法、共享方法改为 pass、provider 覆盖成 pass，均正确失败，未修改源文件。
- 业务源码与自有前端净减 406 行（不含第三方 marked 删除、依赖锁和生成证据）；测试净增加的是本次重构的行为回归，不把用例数量下降当作交付目标。
- 前端回归用内存方式替换回原 charts.js，新增测试正确失败；未临时覆盖生产源文件。
- SQLite 支撑另验证了缺失/None/已有模块和正常/异常/导入失败的 27 种恢复组合。
- 不运行在线行情、实盘或 live OSV 扫描；离线漏洞报告仍标记 `scan_completed: false`，不把空 advisory 视为安全结论。本机无 docker/mysqld，不使用个人数据库代替独立 MySQL 测试服务。

### 复现

在包含工作区改动的临时 checkout 中运行 `python script/remediation/prepare_test_config.py <临时checkout>`，以 Python 3.11 执行 `uv sync --locked`。将临时根目录、`src`、`web/tradingview_zy_chart` 加入 PYTHONPATH，安装 Playwright Chromium 并设置 `RUN_BROWSER_TESTS=1`：

```text
python -B -m pytest -q -rs -p no:cacheprovider tests
```

各平台和供应链专项仍按 `.github/workflows/tests.yml` 执行；本地通过不等同于远端 CI 已运行。
