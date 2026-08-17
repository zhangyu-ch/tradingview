# 发现记录：TradingView 仓库架构整理

## 初始边界
- 仓库路径：`E:/0-Quant/0-tradingview/tradingview`
- 当前分支：`main`，初始工作区无未提交差异。
- 根目录已有 `task_plan.md`、`findings.md`、`progress.md`，内容属于此前的 81 条问题修复任务；本次使用独立 scoped planning，避免覆盖历史记录。
- 用户要求只做整理，因此任何删除建议都只是 HTML 中的审计结论，不执行删除。

## 初步结构
已看到的主要区域：`src/`、`web/`、`script/`、`tests/`、`test_support/`、`docs/`、`notebook/`、`archive/`、`charting_library_patches/`、`audit/`、`package/`，以及 `pyproject.toml`、`uv.lock`、Windows 启动脚本和若干根级报告。

## 待验证问题
- 当前实际包入口、Web factory、CLI/cron 入口和测试配置需要以文件内容为准。
- `archive/`、Notebook、历史文档和审计产物不能仅按目录名判定为可删除，需要结合引用、Git 状态和使用方式核对。
- “很久未修改”需要用 `git log`/文件时间辅助说明；文件长期未改不等于无用。

## 证据规则
1. 静态引用：`rg` 搜索 import、路径、模板、脚本名和配置键。
2. 运行入口：README、`pyproject.toml` scripts、bat/config/cron 文件、GitHub Actions。
3. 测试状态：测试文件清单、pytest 配置、导入/收集约束；不因当前环境缺依赖而断言测试过时。
4. 历史性：目录命名、README/文档明确标记、Git log、归档内容和当前代码是否仍引用。
5. 结论分级：`确认可删除`、`高概率过时但需确认`、`不建议删除`、`无法判定`。

## 并行只读审计摘要

### 当前运行架构
- Web 组合根为 `web/tradingview_zy_chart/cl_app/__init__.py:create_app`；`app.py` 用 Tornado `HTTPServer + WSGIContainer` 承载 Flask，监听 9900。
- Web 蓝图通过 `WebAppServices` 获取依赖；行情请求从 UDF 蓝图进入 `src/tradingview_zy/exchange/get_exchange`，再由 `market_registry.py` 选择 provider、验证 capability、动态加载 adapter。
- Scheduler 是独立进程：`web/tradingview_zy_chart/scheduler.py` -> `scheduler_runtime.py` -> `AlertTasks` -> `MonitoringRunner` -> 注册策略 -> `BatchRunResult` -> 数据库事件记录。Web 仅保存配置并读取状态快照。
- 回测不由 Web 启动，`BackTest` 组合 `BackTestTrader` 与基于 `ExchangeDB` 的 `BackTestKlines`；其输入通常是已同步到数据库的历史数据。
- CI/治理由 `.github/workflows/`、`script/remediation/`、`docs/`、`audit/supply-chain/` 和测试共同构成可执行契约。

### 清理审计初判
- 当前证据不足以确认删除任何受版本控制的运行目录。
- `.venv/`、`.pytest_cache/`、`__pycache__/`、`.artifacts/`、`.ci-test-runtime/` 等本地生成目录属于明确清理候选，但需区分 Git 跟踪状态；`.worktrees/`、`.pi/`、`.pi-subagents/` 可能仍承载工作区/审计会话，删除前需确认。
- `notebook/` 当前无活动入口引用，是高优先级人工确认候选；未打开所有 notebook，不能断言研究结果可替代。
- `archive/` 明确不参与运行/打包/测试，但 README 和文档契约测试仍把它当迁移证据；若移至外部冷存储，需要同步调整 README 与测试。
- `package/` 是 `pyproject.toml` 的本地 wheel 依赖源，不能作为缓存删除。
- `charting_library_patches/` 是 pristine -> patched Web 产物的可重放维护链，不能按备份删除。
- `docs/`、`audit/supply-chain/`、`script/remediation/` 被 CI 与测试直接读取，不属于过时资料。
- 根级 `task_plan.md`、`findings.md`、`progress.md`、`remediation_report.md` 主要是已完成治理任务的历史证据，不影响 runtime，但是否删除取决于审计留存要求。

## 主会话基线证据
- `git ls-files` 统计：`src/` 86 个、`web/` 2024 个、`script/` 39 个、`tests/` 91 个、`docs/` 10 个、`archive/` 150 个、`notebook/` 11 个、`package/` 7 个；文件类型以 JavaScript（1747）、CSS（211）和图片（112）为主，说明图表前端 vendored 资源是仓库体量主体。
- 当前工作树总大小约 211 MB；该数字包含图表库、静态资源和历史归档，不能据此判断代码冗余。
- `README.md` 明确当前能力为多市场行情、TradingView UDF、自选/策略监控、回测和部分只读账户查询；实盘 `order()` 统一 fail-closed。
- `pyproject.toml` 声明 Python `>=3.11,<3.12`，uv `0.10.0`/`uv.lock`，并从 `package/` 引用 6 个平台 TA-Lib wheel 与 1 个 pytdx wheel；删除这些制品会破坏安装契约。
- `.github/workflows/tests.yml` 定义 unit、provider、MySQL、browser、Windows、supply-chain 六类 job；`.github/workflows/repository-hygiene.yml` 直接调用质量、依赖、供应链、provider 文档和 Secret 门禁。
- `archive/README.md` 明确 archive 不导入、不打包、不作为支持运行模块，但它仍是迁移证据；`README.md` 和文档契约测试引用其存在。
- `.gitignore` 将 `.venv`、缓存、`data`、私有配置和 `.artifacts` 等列为非交付内容；其余 `.worktrees`、`.pi` 等需结合 Git 跟踪状态再判定。

## 源码与测试清单证据
- `src/tradingview_zy/` 的核心子域包括：`exchange/` provider 适配器、`backtesting/` 回测、`strategies/` 策略协议/加载器、`trader/` 只读交易相关 facade；根级还有 registry、DB、Web payload/security、calendar、sync batch、storage、watchlist 和监控模块。
- `web/tradingview_zy_chart/` 包含 `app.py`、`scheduler.py`、`cl_app/` Flask 应用、模板和静态资源；静态目录含 TradingView charting library、UDF datafeed bundle、业务 JS/CSS 和指标脚本。
- `script/` 分为 `crontab/` 数据同步/历史入口、`remediation/` 可执行质量/供应链/文档门禁、根级配置模板；前者有多份 JSON 同步配置，后者被 CI 直接调用。
- 由于 `rg --files web` 会被数百个语言 bundle 淹没，最终 HTML 将把 vendor 资源按“受补丁工程管理的静态依赖”整体描述，并单独列出业务可维护 JS/CSS/模板，不逐个罗列生成 bundle。

## 清理候选的新增证据
- `script/crontab/run_history_xuangu.py`、`xuangu_by_same.py`、`xuangu_by_process.py` 明确自称 Legacy Chanlun entrypoint，运行只打印迁移提示；三者都指向活动目录中不存在的 `docs/custom-strategy-integration.md`。可列为“确认无当前业务实现、建议删除或改为正确迁移说明”的强候选，但若外部 cron 依赖文件名，仍需先确认。
- `script/crontab/reboot_sync_gm_a_klines.py` 与 `reboot_sync_gm_futures_klines.py` 在模块导入阶段直接调用 `gm.api.set_* / get_symbols`，而 `pyproject.toml` 未声明 `gm.api` 依赖，README/活动 docs 也未列出入口；它们可能仍被外部部署使用，结论应为“高概率过时，需确认后删除/迁移”，不是确认可删。
- `script/crontab/script_ib_tasks.py` 虽无 README 入口，但 `ib-insync` 在依赖中，且脚本使用 `file_db`/IB RPC，不能仅因无静态引用删除；应列为外部运维入口、需确认。
- `src/tradingview_zy/encodefix.py` 被 Web 入口显式导入；`file_db.py` 被多个 provider、回测和 scheduler status 使用；`database_catalog.py`、`footprint.py`、`futu_context.py`、`history_request_tracker.py`、`sync_batch.py`、`tick_request.py`、`tv_storage.py` 等均有运行或测试引用，不能按孤立文件清理。
- `src/tradingview_zy/trader/online_market_datas.py` 当前未发现仓库内静态引用，但可能是外部 API 扩展点；结论只能是“疑似孤立，人工确认后处理”。
- 多个 `__main__` 块是开发/诊断入口或兼容脚本，不能统一删除；只有三个明确 Chanlun 墓碑块有强证据。
- `FOOTPRINT_RENDERING_PLAN.md` 标记 M0 完成、M1 待开工，并引用历史/未来工作；它与 `charting_library_patches/README.md` 的现行补丁工程互补，但计划中提到的 `patches.md` 与实际 `patches.json` 不一致，应标记为文档过时/需更新，而非静默删除。
- `notebook/` 的 11 个文件中至少两个包含 Chanlun/外部旧环境痕迹，且最大文件约 7.2 MB；当前无活动代码引用，但实验结果所有权未知，建议迁移到 archive 或经确认后删除。
- `audit/tradingview_current_open_issues_v1.md`、`remediation_report.md` 和根级历史规划记录含“原始/历史结论”，部分路径与当前代码相矛盾；它们不应当作为当前架构事实引用，但仍是治理追溯证据，适合“归档/压缩/生成当前摘要后删除”的人工确认候选。
- `tests/` 全量 CI job 直接执行 `uv run pytest -q`，且专项测试通过静态契约保护删除能力、文档和供应链；目前没有测试可确认过时的证据。`test_*_removed.py` 主要是防止已下线 provider 被重新带回，属于当前质量门禁。

## 当前 Git/时间证据
- HEAD 为 `7f517793a108fc607d07db20deef5ee46bb0d30e`，最近提交日期为 `2026-08-16`，主题为“完善质量门禁与 Windows 启动流程”；仓库并非无近期修改。
- 本轮产生的未跟踪目录为 `.planning/` 与 `.pi-subagents/`；`.artifacts/`、`.venv/`、缓存、私有 `src/tradingview_zy/config.py` 等被 `.gitignore` 排除。最终应清理本轮 `.pi-subagents/`，保留 HTML 和 scoped planning。

### 已发现漂移
- 三个 Chanlun 墓碑脚本 `script/crontab/run_history_xuangu.py`、`xuangu_by_same.py`、`xuangu_by_process.py` 指向不存在的 `docs/custom-strategy-integration.md`，属于活动提示文本过时。
- 根级历史规划/进度记录包含个别已不存在或改名的测试路径；它们是历史记录漂移，不代表当前测试过时。
- 暂无证据支持删除当前 `tests/` 中的测试：CI 具备单元、provider、MySQL、Chromium、Windows、供应链分层，专用环境 skip 是设计行为。
- 子审计报告正确环境下全套为 687 passed、2 skipped、1 warning；需要主会话独立复核关键命令与配置后再写入最终文档。
- `src/tradingview_zy/trader/online_market_datas.py` 只有 62 行，定义旧的 `OnlineMarketDatas` 实盘数据抽象，仓库内无静态调用；它不是可确认删除的生成物，需询问外部使用者后再处理。

## 验证结果
- `python script/remediation/check_quality_gates.py`：通过，六个稳定 CI job 存在。
- `python script/remediation/check_dependency_contract.py`：通过，`pyproject.toml + uv.lock` 是唯一解析源。
- `python script/remediation/check_repository_hygiene.py`：通过。
- `python script/remediation/generate_provider_support_matrix.py --check`：通过，生成矩阵与 registry 一致。
- `python charting_library_patches/apply_patches.py --check`：通过，6 个受管图表产物逐字节一致。
- 供应链、生成证据、Secret 引用和 Secret 暴露门禁均通过。
- 架构/文档/清理专项：37 passed。
- 完整测试：`PYTHONPATH='.;src' uv run pytest -q` -> `687 passed, 2 skipped, 1 warning`；告警来自环境中的 `pyfolio` 对可选 `zipline.assets` 的 UserWarning。

## 孤立资产确认矩阵
| 资产 | 静态证据 | 当前判断 |
|---|---|---|
| `web/.../templates/options.html` | 无 `render_template`/include 引用；内容是旧配置不可用页，指向不存在文档并宣称交易执行 | 确认无活动路由引用；建议删除或先移入 archive |
| `web/.../static/echarts.min.js` | 全仓只有自身文件名，无模板/JS加载引用 | 高置信可删除；删除前确认没有外部页面直接引用 |
| `web/.../static/css/layui-theme-dark-legacy.css` | 无活动模板/脚本引用，现行 `dark.html` 加载另一份 `layui-theme-dark.css` | 高置信可删除 |
| `web/.../static/marked.min.js` | 首页加载，但无 `marked()`/`marked.parse()` 等业务调用 | 高概率过时；删除需同步移除首页 script 标签并做浏览器回归 |
| `src/tradingview_zy/db.py:334` `TableByAIAnalyse` | 无查询/写入方法调用；AI 配置仅存在模板与 Secret inventory | 高概率孤立；需确认数据库兼容/外部脚本后迁移模型与配置 |
| `src/tradingview_zy/backtesting/klines_generator.py` | 类只被自身 `__main__` 示例引用 | 疑似旧工具；外部 Notebook/脚本确认后再删 |
| `src/tradingview_zy/backtesting/signal_to_trade.py` | 类无仓库内 import，文件是旧“信号转交易回测”工具 | 疑似旧工具；外部研究流程确认后再删 |
| `src/tradingview_zy/trader/online_market_datas.py` | 类无仓库内 import，模块描述实盘交易数据 | 疑似孤立扩展点；不能自动删除 |
| `script/remediation/parse_issue_report.py` + `update_issue.py` | 只被历史报告/状态和一个报告计数测试使用，CI 不直接调用 | 若治理台账封存，可整组归档/删除 |
| `tests/test_remediation_report_counts.py` | 只验证历史 81 条报告生成器 | 仅在上述报告工具/报告不再保留时删除；当前仍是有效回归 |
| `script/remediation/check_fifo_atomicity.py` + `tests/test_new05_fifo_atomicity_guard.py` | 当前没有 FIFO 实现，检查器只扫描未来可能出现的函数名 | 条件性过时；若项目明确不再支持 FIFO，连同历史问题记录归档 |
| 三个 `script/crontab/*xuangu*.py` 墓碑 | 只打印“缠论已移除”，且链接不存在 | 确认无业务实现；外部 cron 确认后可删或改为有效迁移入口 |
| `reboot_sync_gm_a_klines.py` / `reboot_sync_gm_futures_klines.py` | 无活动文档/CI 引用，导入即依赖未声明的 `gm.api` | 高概率过时但可能是外部 cron；必须人工确认 |

## 二次复核结论（本轮）
- `options.html` 没有任何活动 Flask `render_template`、include 或路由名引用；内容是旧配置不可用页，并引用不存在的 `docs/custom-strategy-integration.md`。仓库内可确认无消费者；外部直接 URL 仍需部署确认。
- `static/echarts.min.js` 已在当前工作树被用户删除（状态 `D`），仓库内没有本地加载引用；Notebook 使用 `https://assets.pyecharts.org/assets/echarts.min.js`，不依赖该文件。
- `static/css/layui-theme-dark-legacy.css` 没有引用；活动 `dark.html` 动态加载 `layui-theme-dark.css`。可列为确认可删的静态资源。
- `static/marked.min.js` 仍被 `templates/index.html:27` 请求，但没有业务代码使用 `marked` 全局；必须连同该 script 标签一起移除，不能单删文件。
- `online_market_datas.py` 被 `tests/test_cr03_live_trading_disabled.py:60` 明确要求存在，是“保留行情 facade、禁止未验证下单”边界的一部分，不能按孤立模块删除。
- `KlinesGenerator` 和 `SignalToTrade` 没有当前仓库 import，但 archive cookbook 仍记录其用途；前者可选清理，后者还可能影响旧回测 pickle 的模块路径，均不具备高删除必要性。
- `TableByAIAnalyse` 是唯一活动代码中的 AI schema 残留；`openai` 依赖、AI 配置和 Secret policy 也未被活动逻辑使用。建议作为 DB/依赖/配置/测试成组治理，不单删模型类。
- 三个 `script/crontab/*xuangu*.py` 只有成功退出的墓碑提示，且链接已死；确认外部 cron 后删除可避免旧任务静默空跑。GM 两个同步脚本是真实可执行集成，必须保留到运维确认停用。
- `script_ib_tasks.py` 被 IB 专项测试读取，不能按无静态启动入口删除；remediation/FIFO 工具与对应测试仍有治理价值。
- `archive/`、`notebook/`、旧 audit/report 是非运行资产和追溯/研究资料；可冷存储但当前删除必要性低。`archive` 及 JoinQuant ZIP 还被 README/文档契约测试保护。
- `.worktrees/remove-chanlun` 属于另一 Git 主工作树 `E:/AI-code-local/tradingview` 的已注册 worktree，虽占约 1.2 GB，不属于本工作区可安全删除对象。
- `.worktrees/remove-chanlun` 属于另一 Git 主工作树 `E:/AI-code-local/tradingview` 的已注册 worktree，虽占约 1.2 GB，不属于本工作区可安全删除对象。
- `layui.js.map` 与 `css/layui.css.map` 仅供调试，未见运行时引用；可在生产发布策略明确不保留 source map 后删除，收益约 1.8 MB，优先级低。

## 二次复核验证
- 针对性回归：`36 passed`，覆盖 live-trading 边界、死代码门禁、归档契约、IB worker、FIFO guard、历史报告和 Secret policy。
- 完整回归：`PYTHONPATH='.;src' uv run pytest -q` -> `687 passed, 2 skipped, 1 warning`（告警为 pyfolio 可选 `zipline.assets`）。
- 门禁：quality gates、dependency contract、repository hygiene、provider matrix、charting patch check 全部通过。
- Git 状态保持为用户侧 `echarts.min.js` 删除，加本轮未跟踪 HTML/scoped planning；没有修改源代码、配置、锁文件、测试或归档。

## 排序原则
- “确认可删”只表示仓库内运行链路和测试没有消费者；外部 cron、部署脚本、私有 Notebook、数据库仍需由维护者确认。
- 首批按收益/风险排序：已删除的 ECharts、旧暗色 CSS、旧 options 模板；随后是需联动的 marked 和需 cron 确认的三个 xuangu 墓碑。
- AI 残留的清理收益高但必须做 DB/依赖/Secret 成组迁移；Python 工具、Notebook、archive、审计报告和测试当前保留。

## 文档刷新初始发现
- 活动文档范围为 `README.md`、`docs/*.md`、`charting_library_patches/README.md` 以及必要的脚本/模板说明；`docs/provider-support-matrix.md` 由生成器维护，不直接手改数据行。
- `archive/docs/**`、`audit/tradingview_current_open_issues_v1.md`、`remediation_report.md` 和根级历史规划是历史/治理证据，应保留原貌并通过当前 README 标明边界。
- `src/tradingview_zy/config.py.demo` 仍使用 `.chanlun_pro`、`chanlun_klines` 名称并保留 AI 配置；这可能是运行兼容默认值，不能仅因命名旧就直接改。需要检查配置加载、数据库默认值、迁移和测试。
- README 当前明确声明 Chanlun 运行时已移除、实盘下单 fail-closed、uv 是唯一依赖入口；这些高层声明与上一轮代码审计一致，但安装、启动、配置、能力表和链接仍需逐项验证。
- README 的主启动路径 `web/tradingview_zy_chart/app.py` 存在于仓库清单；仓库没有根级 `run.sh`、`run.bat` 或 `src/tradingview_zy/app.py`，后续入口核对必须从受版本控制文件反查。
- README 声称“Windows 脚本只执行 `uv sync --locked`”，需定位真实 Windows 脚本验证；当前根目录未见该通用命名。
- 真实入口为 `windows_install.bat` 与 `windows_run.bat`。前者严格要求 `uv 0.10.0` 并执行 `uv sync --locked`、复制配置和环境检查；后者不安装依赖，接受 `uv 0.10` 或 `0.11` 后启动 Web。README 应增加 Windows 快速开始，并避免暗示运行脚本也会安装依赖。
- `docs/supply-chain.md` 的“Windows 脚本只接受 PATH 中精确 uv 0.10.0”与 `windows_run.bat` 接受 0.10/0.11 直接矛盾。需结合 Windows 契约测试判断是文档还是脚本应作为事实。
- `FOOTPRINT_RENDERING_PLAN.md` 顶部仍标记 M1 待开工且 M0 章节描述 `patches.md`，当前实际已使用 `patches.json`、`extract_patches.py` 和 16 处/6 文件补丁；代码还存在 `/tv/footprint` 路由，必须核实端点语义后刷新里程碑状态。
- `/tv/footprint` 已有登录保护、参数解析、子周期能力检查、TTL cache 和 `aggregate_footprint()` 聚合调用；`tests/test_footprint.py` 进入 provider-contracts job。M1 至少已经实现，实施计划的“待开工”不再成立；还需核对前端 footprint 模块判断 M2 状态。
- M2 当前只有 `static/js/footprint/loader.js` spike：bundle 补丁把它注入 iframe，并为样式 17 包装原蜡烛 renderer、追加紫色矩形以验证 draw 签名。正式 `data_cache.js`、`pane_view.js`、`renderer.js` 尚不存在。因此准确状态是 M0 完成、M1 后端完成、M2 spike 已落地但正式渲染待实现。
- `docs/quality-gates.md` 对六个稳定 job 的描述与 `.github/workflows/tests.yml` 相符；repository-hygiene 还额外执行 readability、Secret 和生成文档校验，文档目前只概括其中一部分，属于可补充而非错误。
- `docs/provider-support-matrix.md` 明确由生成器生成且与 registry 一致，数据行不手改；`provider-capabilities.md`、策略协议边界、禁用实盘和 unsupported-provider 文档的核心声明目前与审计结果一致。
- `docs/secrets.md` 仍将 AI 作为现行凭据类别；代码 Secret inventory 确实保留 AI policy，但 AI Web/工具入口已移除。文档应明确这是兼容/待清理配置，不应让用户误认为仓库仍提供 AI 分析功能。
- Secret 权限实现只在 `os.name != "nt"` 时校验 `file://` 的 group/other mode 并设置 managed 目录 `0700`、文件 `0600`；Windows 跳过权限校验和 chmod，测试也显式跳过这些断言。`docs/secrets.md` 必须限定 POSIX 保证，并要求 Windows 运维自行施加 DACL或使用平台 Secret 注入/keyring。
- `docs/strategy-protocol.md` 最后一段称跨域转换仍 deferred，但 `tradingview_zy.strategy_bridge`、`docs/strategy-protocol-boundary.md` 和测试均已存在。应改为引用 opt-in bridge，并继续强调只支持 paper/backtest、不授权实盘。
- `charting_library_patches/README.md` 将受管路径简称为不存在的根级 `charting_library/`；实际目标为 `web/tradingview_zy_chart/cl_app/static/charting_library/`，命令说明和工作流约定应写全路径。

## 文档刷新已实施
- `README.md`：增加完整文档导航、Windows/Bash 安装启动路径、uv 安装与启动入口差异、兼容数据路径/AI 字段说明；移除不必要的 Bash-only `PYTHONPATH`，本地门禁统一为 `uv run python`。
- `docs/supply-chain.md`：明确 `windows_install.bat` 固定 uv 0.10.0、`windows_run.bat` 接受 0.10/0.11 但不是依赖解析入口，并更新本地命令。
- `docs/secrets.md`：限定 0700/0600 为 POSIX 保证，明确 Windows 不设置/验证 DACL；补 PowerShell 示例并标注 AI inventory 为兼容残留。
- `docs/strategy-protocol.md`：将“跨域转换 deferred”改为引用已实现的 opt-in `strategy_bridge` 和 paper/backtest 边界。
- `docs/quality-gates.md`：补齐 repository-hygiene 实际执行的 readability、repository hygiene 和 Secret checks。
- `charting_library_patches/README.md`：修正真实受管路径和命令；按 `patches.json` 更新为 18 处/6 文件，其中 2 处是 M2 spike。
- `FOOTPRINT_RENDERING_PLAN.md`：更新为 M0/M1 完成、M2 spike 已落地、正式渲染与 M3 待做；用实际 endpoint/cache/test 行为替换旧计划假设。
- `src/tradingview_zy/config.py.demo`：只更新兼容性注释，不改默认值或运行逻辑；移除会误导新部署的旧 AI 推广/启用说明。
- `tradingview_repository_architecture.html`：同步 online-market-data、GM、ECharts、Windows uv 与 Footprint 复核结论。
- 独立最终复核发现并已修正：`windows_run.bat` 的默认 `uv run` 可能同步环境，不能文档化为绝不更新锁；Footprint 当前只有聚合单测和静态 route guard；loader 尚未消费 endpoint；架构 HTML 的只读变更声明、211 MB 体量数字和 static/ECharts 描述已漂移。
- 手工文档命令统一为 `uv run --locked`；不改变 `windows_run.bat` 的现有行为或 Windows 测试契约，README/供应链文档明确要求先执行锁定安装。
