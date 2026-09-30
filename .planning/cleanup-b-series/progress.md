# 实施进度

## 2026-09-29
- 读取当前 Git 状态、历史规划与用户指令。
- 确认上一轮修复仍在工作区，未提交。
- 开始按模块隔离实现；主会话负责整合、回测/参数、文档和全量回归。

- 测试红灯：新增 B8/B11 8 条失败，B12 保持行为 1 条通过。裸 python 是 conda 缺 empyrical，后续统一用主项目 .venv/Scripts/python.exe。
- 已修 B8 run 参数/日志、B12 恒真 mask；B11 追加两版并保留旧参数 SHA。
- 并行 Agent 工具结果与任务顺序不同，已逐个按回信确认：前端 ade88、飞书 a587、DB a2c829、行情 a812、指标 ac173；全部在独立树无编辑冲突。

- 主树 B8/B11/B12 + 既有 B6/B7/B9/B10/B13 已通过专项 32 passed；集成前全量 701 passed、2 skipped，唯一告警为既有 pyfolio 可选 zipline。
- docs/futures-parameter-versions.md 已说明新版本、load-only 原快照与显式近似使用；docs/currency-timezone-options.md 完成四种方案及迁移/回滚验收。
- 前端 agent 报告真实 Chromium 专项已通过，待收patch后主树复验；class 使用 content-table。
- 已新建根目录历史修正.md（目前 B14/B8/B11/B12），待数据库patch完成后追加 B16/B17 实际实现与约束。
- 已编写 docs/indicator-series-state.md，以槽位顺序、历史深度、预热与重复bar覆盖解释B20用法；请求指标agent按实际引擎校核。
- 生成的 .claude/worktrees 为此次隔离开发副本，最终在补丁整合验证后清理，不加入交付。

- 前端补丁 frontend-csrf-ade88.patch 已在主树应用；主树真实 Chromium + CSRF/静态组合严格测试通过（12项，4项真实浏览器）。
- 独立只读核验发现B11新参数可能复用旧优化/多进程缓存。已委派原核验agent直接在主树补齐缓存manifest身份与回归；其他主会话不编辑backtest。

- B16/B17补丁已合并；主树数据库专项+相邻60 passed；历史修正.md已加入迁移顺序/版本4/锁生命周期/旧重名处理和唯一性语义。
- B20补丁已合并；真实PineJS/Context序列验证覆盖11配置414000次历史实时对比；主树pytest复验已通过。文档已按真实prepare/modified语义修正set说明。
- B11缓存隔离补修已直接落主树：优化key/多进程产物包含manifest身份，完整哈希不符拒绝复用，不覆盖旧产物；8项新增回归。

- 飞书补丁合并后（行情补丁尚待）：全量725 passed、6 skipped；13项浏览器/CSRF/静态严格测试通过，其中5项真实Chromium。
- 8个 script/remediation/check*.py 门禁全部通过；uv lock --check --offline通过。
- 飞书ZIP有34个原始文件+MANIFEST/RESTORE，SHA256已核对：279be3438fecf2bda70acf33e8b9fea0e1bcfc454907d1cb52689742e7b38a0b。未包含私有config或数据库。
- 主树单独执行 node tests/js/indicator_realtime.cjs 确认输出：11 configurations, 414000 historical/realtime plot comparisons plus changed-bar/reset/warmup checks。
- 飞书归档34个源码逐一与基线git blob比较（仅忽略CRLF差异），全部一致。
- 前端/DB/飞书/指标四个临时工作树和对应临时分支已清理；补丁备份保存在系统临时目录，主树改动完整保留。
- 活动 src/web/pyproject/uv.lock 全局检索无 lark_oapi、send_fs_msg、FEISHU_、settings_security、messaging_reliability、is_send_msg 引用。
- 新增说明与根目录历史修正文档的本地链接均已验证。
- 全部当前Python源/测试 compileall 通过；9个修改过的前端JS通过 node --check。

## 最终验收：2026-09-30
- B18/B19补丁整合完毕；B5完整方案在docs/tdx-cache-options.md，缓存key/增量算法未实施。
- 最终默认完整测试788 passed、6 skipped；启用真实浏览器后的完整测试793 passed、1 skipped、1条既有pyfolio可选zipline告警。唯一跳过为真实MySQL集成门控。
- 最终8个门禁全部通过；锁文件离线校验、编译、JS语法与diff格式通过。
- 所有临时工作树/分支清理完毕；对应patch备份仍在系统临时目录；没有Git提交或暂存，没有主动修改实际业务DB/配置。
- 历史修正.md完成（含必需B14/B16/B17及相关维护边界）。四份主题说明和飞书ZIP/恢复说明完成。
- 限制：AkShare/CCXT若忽略timeout，后台任务保留有限槽直到退出，可能需重启；A股除权请求有独立预算；B12时区问题与B5缓存问题按要求暂不实施。

## 追加实施：2026-09-30
- 用户选择 B5 方案 B、B12 方案 C（记入历史修正），并要求继续修复 B20。
- 上轮未提交改动完整保留。三个工作者按文件所有权直接编辑主工作区：TDX 缓存、crypto 时间边界、指标边界；协调者负责规划/历史记录/整体验证，避免在缺少未提交修复的 HEAD 工作树上开发。
- B5 采用推荐的版本化新 raw key；旧文件保留。B12 不假定旧库来自上海，不操作实际库，旧库须显式确认时区后登记；B20 复核既有状态修复并补 AMA N=1 边界。
- 所有实现/回归仍在进行，上一轮 793 passed 不是本轮验收结果。
- 启动协调：自动 worktree 初始环境禁止回主目录执行命令，因此暂停后调整。B5/B12 续跑的官方环境已回主仓库；B20 则导入公开未提交快照，在隔离树实现，临时基线 tree=2e13478991508f4a68d5a620de397cfe3286ff66，后续只应用增量补丁。没有绕过目录/权限限制，主仓库 index 未改。
- 只读尝试 tests/conftest.py 不存在；未再假定该文件存在，也未执行错误测试命令。
- 公开基线ZIP位于系统临时目录 cleanup-followup-baseline.zip，不包含私人config.py、凭据或数据库。
- B12 将追加第5迁移 migrate_crypto_storage_timezone；协调者已同步 B16/B17 测试的 _steps 和两个主DB版本断言，保留独立迁移引擎版本1测试不变，待代码落地后执行。
- B5 因共享分页helper被引入，获准仅向 B18 的 TDX AST 测试环境注入两个新依赖，不削弱原重试/超时断言。
- B20 四文件增量补丁已审阅并应用主树；主树 Node 11配置414000次 + N1独立oracle全部通过，pytest 5 passed。历史修正已补初始化原因与验证边界。
- B20 增量已反向check确认在主树，并核对隔离树仅有预期4文件增量后，清理该临时worktree/branch；外部patch及基线ZIP保留。
- 主树 B16/B17 17项全部通过（版本5），历史修正已记录第5步只建crypto时区台账，前四迁移不重排。B12时间语义专项仍由工作者验证。
- B5 10个文件完成，主树专项与相邻7文件218 passed；协调者初审共享helper和文档，历史修正已记录断档/raw日期/旧清理边界。
- B12 初审发现已登记时区仍每次拿迁移锁与SQLite写锁，会阻塞纯查询；已要求工作者增加只读快路径及“另一个写者持锁时仍能读取”回归。

## 追加集成验证：2026-10-01
- 默认全量预检889 passed、6 skipped、2 failed：日线pd.to_timedelta('D')异常；Binance游标旧无时区字符串断言。前者由B12工作者修正为UTC左标签分组，后者协调者更新并增加3时区绝对游标测试。
- 日线旧测试随后暴露上海输出标签断言，按新UTC契约更新，仍验证上海08:00边界、全部OHLCV和输入不变；相关严格组合26 passed。
- 8个门禁、uv lock --check --offline、AMA JS语法及CRLF-aware diff检查已通过；B12剩余专项/最终全量待完成。
- 读取预检日志时首次路径拼错（项目名中的连字符误作目录分隔），按工具返回完整路径更正后读取成功，未重跑同一错误命令。
- 含真实Chromium的首轮完整集成937 passed、1 skipped、1条既有pyfolio告警（36.38s）；MySQL真实集成仍门控跳过。
- B12工作者随后补强优化身份和多频回放测试，专项41 passed；协调者追加要求确认直接[3h,1m]薄历史时不会因tail120/丢首桶保留完整未来高周期OHLCV，最终验收待该项结论。历史修正已补实际CRYPTO_STORAGE_TIMEZONES、C1频率/产物隔离、版本5与回滚要求。

## 追加最终验收：2026-10-01
- 已确认并修复crypto薄历史未来OHLCV路径：按周期比扩充基础窗口，未完成高周期从基础数据重建，缺桶起点时明确CryptoTimezoneError。新增缓存/按需两模式×有/缺起点4例，用相同close但未来high/low/volume极值验证；B12专项45项，相邻组合95 passed。
- 最新完整回归（开启真实Chromium）：944 passed、1 skipped、1条既有pyfolio可选zipline告警，38.87s。唯一skip为真实MySQL门控；没有连接实际MySQL/交易所。
- 最后8个质量/安全/供应链门禁全部通过；编译、CRLF-aware diff、交付文档链接通过；uv锁离线检查和AMA JS语法已通过。
- B20真实PineJS 11配置414000次历史/实时比较及N1独立oracle通过；B5七文件专项/相邻218 passed。
- 历史修正.md 已覆盖选择、实现、C1命名空间、时区确认、薄历史重建与版本5回滚约束。
- 主仓库index为空，无Git提交；无临时agent工作树遗留，原有其他工作树未改。私人config.py、凭据、实际业务库/历史行情均未操作。所有本轮任务完成。
