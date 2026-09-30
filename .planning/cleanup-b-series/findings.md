# 实施发现

- 起点 HEAD 7bece68；工作区既有 7 文件 +109/-11，新增 4 条测试；基线 692 passed、2 skipped。
- root task_plan/progress/findings 属于上一轮 81 项修复历史，不覆盖。
- 用户已经选定实施方案；B5 缓存统一与 B12 时区重构只出方案。
- 历史修正.md 尚不存在，集成阶段新建根目录文档，至少记录 B14、B16、B17 的目的和约束。

- B11 参数 manifest 校验逐版本 hash；原 2024-12-13 记录不可原地更改，否则历史 pkl 均失败。采用旧版本仅加载、新修正版本和显式 legacy-static 版本，旧 metadata/hash 保持。
- B8 run 无 begin_start_dt 调用方；删除参数并要求 callback 关键字传递，防止旧位置参数被误当 callback。
- B12 日线 mask 的移除不改 trade_day；ExchangeDB 把无时区 DB 时间按 UTC 解释，BackTestKlines currency 默认上海且用 astimezone 解析 naive 输入，时区方案需覆盖整个链而非只日线。

- B12 读写根因：两个 Binance provider 使用本机时区，DB 两条insert路径去时区不转时刻，ExchangeDB却贴UTC；增量游标以naive字符串往返。四方案建议限定crypto，旧数据须先确认来源，不可全库盲目减8小时。

- B11补充修复：优化和多进程缓存须包含完整参数快照身份；只发布修正版却允许自动读取旧缓存会绕过乘数修正，已纳入回归。
- B18港/美AkShare与Binance用固定小容量DeadlineCaller，不能杀线程，超时继续占槽且新请求可能快速失败；A股xdxr另有预算，不能声称全部klines硬性12秒。
- B20真实prepare会回滚本bar；未set的问题还包括modified=false不推进序列历史，文档已准确限定；AMA cal_type=1,N=1旧全NaN公式边界保留。

## 2026-09-30 追加决策
- 用户已授权 B5B / B12C / B20 后续修复，之前“暂缓”属于上一轮状态。
- B12C 需要显式、持久且不可静默改变的旧存储时区。无时区历史值不能自行推断来源，因此实现不能默认把已有数据认作上海；真实部署确认留给用户，开发只针对临时数据库。
- B5 新版本 key 不回退可能已有内部缺口的旧缓存，六市场分页上限及复权差异保留。
- B20 既有五指标序列修复不重复重写；聚焦剩余 AMA cal_type=1/N=1 以及真实引擎验证。
- B20 子任务已定位：N=1 时第一根 sc 已有限，但 previous_ama 为 NaN，递推没有播种；拟仅此边界初始化为当前 close，并用独立 TR/ER/SC 数值 oracle 验证，其他参数保留旧历史 digest。
- 集成注意：tests/test_b16_b17_schema_migrations.py 两处主 DB 版本断言固定为4；待 B12 追加迁移确定版本后由协调者同步，不能改独立迁移引擎用例中的版本1。
- B5 已完成共享helper及六适配器接入，原FileCache概率触发15天清理没有改变；不主动删除旧key不等于永久保留旧文件。
- B12 复核：登记完成后的常规读取不能拿SQLite写锁，工作者已改只读快路径；还需专项验证。
- B12 旧合成3h/10m/2m不能仅换时区就当已修复；工作者采用内部频率C1命名空间隔离旧行（不是全库重建，不改变旧主键），对query/write/delete/latest一致映射。曾考虑强制从基础频率重合成，但会与同步存储行为不一致，已弃用。
