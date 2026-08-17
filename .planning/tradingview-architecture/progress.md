# 进度日志：TradingView 仓库架构整理

## 2026-当前会话
- 已读取 `planning-with-files-zh/SKILL.md`。
- 已确认仓库工作区初始干净，分支为 `main`。
- 已恢复并识别根目录旧规划文件属于另一项历史修复任务。
- 已建立本次任务的 scoped planning 文件：`.planning/tradingview-architecture/{task_plan,findings,progress}.md`。
- 已完成初步顶层目录盘点，下一步进入只读结构与入口审计。

## 测试/验证
- 架构、文档和治理专项测试：37 passed。
- 完整测试：687 passed，2 skipped，1 条第三方 pyfolio 可选依赖告警。
- 质量、依赖、仓库卫生、provider 矩阵、图表补丁、供应链和 Secret 门禁全部通过。

## 文件变更边界
- 允许新增：本 scoped planning 文件和最终 HTML。
- 禁止修改：`src/`、`web/`、`script/`、`tests/`、配置、锁文件、既有文档和归档。

## 并行审计进展
- 已完成三路只读子审计：运行架构、目录/历史资产、测试/文档/CI。
- 已确认三个子任务均正常完成，无悬挂进程。
- 已记录关键入口、模块链路、删除建议分级和文档漂移候选。
- 下一步：主会话核对完整目录统计、关键文件内容、Git 历史/跟踪状态和候选引用，再生成 HTML。

## 审计阶段完成
- 已核对 Web/Tornado/Flask、provider registry/facade、DB、策略、独立 scheduler、回测、同步脚本、前端静态资源、CI/供应链的调用关系。
- 已完成受版本控制资产与本地生成目录区分，形成清理候选矩阵。
- 已完成 37 项专项测试和 687 项完整测试；全部通过，2 项按设计跳过，1 条第三方可选依赖告警。
- 已完成质量、依赖、仓库卫生、provider 文档、图表补丁、供应链和 Secret 门禁。
- 当前进入最终 HTML 编写与结构/路径校验阶段。

## 交付完成
- 已生成 `tradingview_repository_architecture.html`，包含 11 个章节、12 张表和完整内部目录。
- 已用 HTMLParser 检查标签、重复 id、内部锚点和章节顺序；已用 Node 校验内联 JavaScript 语法。
- 已逐项核对核心路径存在性、受版本控制目录覆盖和清理候选名称。
- 已清除本轮 `.pi-subagents/` 临时产物；最终工作区只保留 HTML 与 `.planning/` 记录。
- 已确认 `git diff --name-only` 为空，没有修改任何受版本控制的产品文件。

## 删除候选二次复核
- 用户要求确认真正可删除项，并按删除必要性排序；允许低收益、低风险项暂存。
- 当前工作树已有用户侧删除 `web/tradingview_zy_chart/cl_app/static/echarts.min.js`，复核期间不恢复、不覆盖。
- 已恢复上一轮审计证据，开始逐项检查引用、部署/公共接口风险、Git 历史与成组删除约束。
- 已确认 `online_market_datas.py` 被 live-trading-disabled 测试保护；AI 残留应成组处理；三个 `xuangu` 脚本是成功码墓碑；GM/IB 脚本保留。
- 已确认 `.worktrees/remove-chanlun` 属于另一 Git 主工作树，不能从当前仓库删除；当前仓库自身缓存约 5 MB，均为可再生本地产物。
- 已补充 source map、Notebook 和 archive 的低优先级/冷存储判断，下一步运行针对性回归并形成排序。
- 针对性回归 `36 passed`；quality/dependency/hygiene/provider-matrix/charting-patch 门禁全部通过。
- 完整回归 `687 passed, 2 skipped, 1 warning`；未执行任何候选删除，阶段 5 已完成。

## README 与活动文档刷新
- 用户要求核对 README 及其他文档是否过时并直接更新。
- 初步清单：当前用户文档为 `README.md` 与 `docs/*.md`；`docs/provider-support-matrix.md` 是生成文档；`archive/docs/**`、audit 原始问题清单和根级历史规划属于历史证据。
- 初筛发现示例配置仍含旧 `.chanlun_pro`、`chanlun_klines` 和 AI 配置，而当前文档声明 Chanlun/AI 运行入口已移除；需分别核对“兼容保留”还是“真正过时”。
- 阶段 6 已开始，当前未修改活动文档。
- 已完整读取 README 和 pyproject；按常见命名尝试的三个入口文件不存在，已转为从 Git 清单定位真实启动脚本并记录到错误表。
- 已完整读取第一批与第二批活动文档，确认 Windows uv 策略、AI Secret 描述和足迹里程碑存在待核实漂移；生成 provider matrix 保持只读。
- 两路只读复核已完成；独立发现与主审计一致，并额外确认 Windows ACL 权限保证、strategy bridge 文案和 charting library 路径三处漂移。
- 已完成阶段 6 的文档清单和事实核验，确定修改 README、Secret、供应链、策略协议、补丁说明和足迹计划六个文件。
- 已实际更新 README、4 个 `docs/` 文件、补丁 README、Footprint 计划、示例配置注释和架构 HTML，共 9 个文件；未修改运行逻辑或生成 provider 矩阵。
- 阶段 6 进入验证：检查 diff、链接/路径、生成一致性、文档契约、补丁重放和完整测试。

## 文档刷新验证与收尾
- 本地 Markdown 链接检查：13 个活动文档，0 个缺失本地链接。
- 架构 HTML：13 个 id、无重复 id、无缺失内部锚点；内联 JavaScript 通过 `node --check -`。
- 文档契约专项：`61 passed`，覆盖 README、provider matrix、supply chain、Secret、quality gates、Windows launcher、Footprint 和 strategy bridge。
- 生成/门禁：`uv lock --check`、quality gates、dependency contract、supply-chain/evidence、provider matrix、Secret reference/exposure、readability、repository hygiene、charting patch `--check` 全部通过。
- 完整回归：`PYTHONPATH='.;src' uv run pytest -q` -> `687 passed, 2 skipped, 1 warning`；告警为 pyfolio 可选 `zipline.assets`。
- `git -c core.whitespace=cr-at-eol diff --check` 通过；清理了本轮 `.pi-subagents/` 临时产物。
- 当前未解决但已明确标注的边界：Windows Secret DACL 需部署侧保障；`windows_run.bat` 的 uv 0.11 宽松启动策略与安装/CI 的 0.10.0 基线不同；Footprint M2 正式 Canvas 渲染尚未完成；archive/audit 仍是历史证据。
- 阶段 6 完成，未修改产品运行逻辑，也未重写生成 provider matrix、archive 或 audit 原始证据。

## 独立最终复核补充
- reviewer 发现 `windows_run.bat` 使用未带 `--locked`/`--no-sync` 的 `uv run python`，因此它可能按 uv 默认行为同步环境；已决定只修正文档事实描述，不改启动脚本及其现有 Windows 测试契约。
- reviewer 发现架构 HTML 的旧“只读/未修改文档”声明、Footprint loader 调用 endpoint 的表述、M1 路由覆盖强度和 211 MB 快照数字已漂移；这些属于报告文案，需要补正。
- 已逐项修正 reviewer findings：手工命令使用 `uv run --locked`，Windows run 默认同步行为如实说明，供应链 CI 顺序按 job 区分，Footprint 覆盖和 HTML 快照状态收紧。
- 修正后专项回归再次 `61 passed`，本地链接 0 缺失，HTML 锚点/内联 JavaScript、依赖/供应链和图表补丁均通过。
- 修正后完整回归再次 `687 passed, 2 skipped, 1 warning`；阶段 6 最终完成。
