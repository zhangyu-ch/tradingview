# B20：PineJS 状态序列与重复计算

## 为什么不能直接累加 JS 对象里的状态

图表会多次计算同一根实时 K 线。两次调用之间可能没有新 bar，只是收盘价/成交量更新，甚至数据完全相同。

如果把递推值保存在 `this.xxx`、普通数组或对象里，每次 `main()` 都对上一次调用结果递推，就把“同一根 bar 更新了十次”误当成“经过了十根 bar”。历史完整回放往往正确，实时显示却会漂移；刷新后重算又变回历史值。

状态序列应当按 **bar** 推进，而不是按 JS 函数调用次数推进：读取上一根已提交 bar 的值，用当前 bar 的最新输入重新计算，再覆盖本 bar。

## “必须每次按相同顺序无条件调用”是什么意思

### 1. `new_var()` 不是按 JS 变量名查找序列

PineJS 在一次 `main()` 调用中，按 `new_var()` 的调用位置/顺序对应状态槽位。变量名 `foo`、`emaState` 只是 JS 的局部名字，图表库不知道这些名字。

错误示例：

```javascript
if (close > open) {
    const onlyUp = context.new_var(close); // 只在阳线占第一个槽
}
const state = context.new_var(NaN);        // 阴线第一个槽，阳线却是第二个槽
```

同一段 `state` 代码，在不同 bar 中读写的可能不是同一条历史序列。

正确做法是让**序列创建/获取顺序固定**，只对数学计算做条件分支：

```javascript
const closeSeries = context.new_var(close);
const state = context.new_var(NaN);
const previous = state.get(1); // 每次都声明/读取所需历史深度

const current = Number.isFinite(previous)
    ? previous + alpha * (closeSeries.get(0) - previous)
    : close;
state.set(current);            // 每次都覆盖本 bar，包括重复更新
return [current];
```

实际指标必须使用各自原本的初始化公式与 NaN 规则，不能把这里的通用示例直接替换进所有指标。

### 2. 不要把历史读取藏在数据相关的分支里

例如 `condition ? state.get(1) : 0` 可能让引擎在初始化/确定历史深度时没有看到需要的历史值。先无条件读取 `const previous = state.get(1)`，再决定如何使用它。

这里的“无条件”针对引擎的状态槽位/历史访问路径，**不代表禁止指标公式出现 if/else**。条件信号、涨跌颜色、阈值判断都可以保留。

### 3. 预热阶段也不能跳过后面的状态槽

```javascript
if (notEnoughBars) return [NaN];
// 后面的 new_var/get 从未在这些 bar 执行
```

这样的早退容易导致初始化与历史槽不完整。应该先按固定顺序访问所有必需序列，按指标规则写入预热值，最后返回 NaN 输出。

### 4. 不应只在“条件成立”时写 `set()`

本 bar 的状态每次都应定义清楚。条件不成立时，也需要写入该公式要求的保持值/零/NaN。实际引擎会在准备重复计算时回滚本 bar，但如果一个序列本轮没有被标记为已修改，推进下一根 bar 时可能跳过它的历史推进，导致后续 `get(1)` 对不上上一根 bar。因此不能依赖“没写就自动沿用”的模糊含义。

## 用一个数字理解实时幂等

设上一根 bar 的状态为 10，当前输入 20，递推公式为 `(previous + input) / 2`。

- 普通 JS 累加：第一次 15，第二次 17.5，第三次 18.75——没有新 bar，却不断变化。
- bar 序列：每次 `get(1)` 都是上一根 bar 的 10，因此当前输入不变时每次都是 15。
- 若同一根 bar 的输入变成 22，则重新得到 16；直到下一根 bar 才把这个最终值作为新的上一根状态。

## AMA 单周期边界的初始化修正

`cal_type=1, N=1` 的 `ER=(high-low)/TR` 在第一根有振幅的有效 bar 上就可计算，因此旧实现不会经过 `sc=NaN` 的收盘价初始化分支。此时上一根 AMA 尚不存在，`NaN + sc * (close - NaN)` 会使后续全部输出 NaN。

仅对此参数组合增加初始化：上一根 AMA 为 NaN 时，以当前收盘价为种子；若收盘价仍缺失则继续输出 NaN。其后仍使用原递推 `AMA=previous+sc*(close-previous)`，不修改 TR、ER、平滑系数或颜色规则。该选择相当于把首次递推的前值设为当前价格，不引入零价偏差；已有有效前值时仍从上一根已提交 bar 计算，而不是本 bar 上一次 tick。零振幅导致 `sc=NaN` 时继续保留原有的收盘价回退。

其他参数组合维持原历史输出；CDBB `FILTER >=` 边界不变。此修复没有增减或重排 `new_var()`，`ama.get(1)` 与 `ama.set()` 仍无条件执行。

### 真实引擎回归

- `tests/js/indicator_runtime.cjs` 加载仓库随附 bundle 中的真实 PineJS 数学函数及 Context/有界序列实现，不使用状态 mock。
- `node tests/js/indicator_realtime.cjs` 保留其他 10 组历史 SHA256 基线；N=1/type=1 不再以旧全 NaN 摘要作为成功标准，改用独立 TR/ER/SC 数学递推 oracle 并要求有效价格产生有限 AMA。
- 覆盖两组快慢周期、跳空的真实平滑、缺值预热、零价格/零振幅、重复与变动 tick、恢复原输入、提交变动收盘价后推进下一 bar，以及复用指标 body、重建 Context 的品种/周期/参数切换并切回 N=1。检查槽位数量和逐槽历史容量保持不变。
- `PYTHONPATH=src python -m pytest tests/test_b20_indicator_realtime.py` 从 pytest 调用相同真实引擎回归；AMA 子项还要求 N=1 数值专项确实执行。

## 维护与回归要求

- 历史一次计算应与旧公式一致，除非另行批准公式修正。
- 相同 bar 重复输入、变化输入再恢复、推进下一 bar，都要与完整重算对比。
- 切换品种、周期、输入参数时不得残留前一个实例的状态。
- 覆盖预热 NaN、连续条件/间断条件、反转信号以及长窗口。
- 本轮修复目标是 rsx、ama、cdbb、macdbl、hdly 的状态管理，不顺带更改 CDBB `FILTER >=` 等公式边界。
