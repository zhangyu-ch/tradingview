# 真实足迹渲染（Volume Footprint）实施规划

> 制定日期：2026-07-30
> 关联提交：`d16d52d` 为 TradingView 图表库新增 Volume Footprint 图表类型
> 状态：M0 已完成（`charting_library_patches/`），M1 待开工
>
> **M0 期间的重要修正**：侦察发现原版 CL v31.0.0 中本就存在样式 17 的渲染骨架
> （`case 17:case 19:case 1:` 复用蜡烛 PaneView、0.2 宽度系数、18 处
> `volFootprintStyle` 引用）——VolFootprint 是 TradingView 内置但未发布的
> 隐藏样式，`d16d52d` 的本质是"解锁"而非"新增"。0.2 窄蜡烛正是上游为
> 足迹单元格预留的骨架布局，M2 的渲染方案与上游意图吻合。

## 0. 现状基线与目标

### 现状

- 样式 `VolFootprint = 17` 已通过手改压缩 bundle 注册进 vendored charting_library（CL v31.0.0），但**只是"宽度系数 0.2 的窄蜡烛"**，复用 `SeriesCandlesPaneView`，没有任何分价成交量渲染。
- 注入点（唯一实例化处，位于 `bundles/library.257d05210b16f5ddbfc2.js`）：

  ```js
  case 17: case 19: case 1:
    this._paneView = new Ft.SeriesCandlesPaneView(this, this._model,
        1===e || 19===e ? 1 : .2);   // 样式17宽度系数 0.2，普通蜡烛为 1
  ```

- 已知遗留问题：
  1. 0.2 系数导致缩小时 K 线过早退化成细线（实体宽度只有普通蜡烛的 1/5）；
  2. 图表状态栏标题生成对样式 17 抛 `TypeError: Cannot read properties of undefined (reading 'value')`（补丁不完整）；
  3. 补丁是手改压缩产物，不可 review、不可重放，库升级即丢失。

### 目标

每根 K 线内按价格分层显示成交量单元格（色块 + 数字），支持买卖力量近似（delta），缩放时自适应降级，且整套扩展**可维护、可重放、升级库后可恢复**。

## 1. 架构总原则：最小锚点补丁 + 外部可读模块

基于两个已查实的技术事实：

- **接缝存在**：`SeriesCandlesPaneView.renderer()` 返回 `CompositeRenderer`，支持 `append()` 追加自定义 renderer —— 不必重写渲染管线，只需"蜡烛骨架 + 追加足迹层"。
- **样式 17 的实例化点只有一处**（上文 switch），是理想的劫持锚点。

因此 bundle 内只保留 2~3 个一行级锚点补丁：

1. iframe 文档加载时注入 `<script src="static/js/footprint/loader.js">`（外部代码进入 iframe 上下文的通道，同源无障碍）；
2. `case 17` 分支改为：
   `window.__FootprintPaneView ? new window.__FootprintPaneView(this, this._model, 内部类引用) : 现状窄蜡烛`
   （外部模块未加载成功时优雅回退）；
3. （视需要）把 `PaneRendererCandles`、`optimalBarWidth` 等内部工具挂到 iframe 全局，供外部模块复用。

**全部真实逻辑放在 `static/js/footprint/` 下的普通可读 JS**，改渲染只需刷新页面，不再碰压缩代码。

## 2. M0：补丁工程化（前置地基，约 0.5 天）

- 仓库新增 `charting_library_patches/`：
  - `pristine/` —— 原版未改 bundle 副本（从 git 历史 `d16d52d^` 提取）；
  - `apply_patches.py` —— 锚点字符串精确替换脚本，替换失败即报错退出（防库升级后静默失效）；
  - `patches.md` —— 每个锚点的位置、目的、原文/替换文。
- 把现有 `d16d52d` 的全部手改（d.ts 枚举、standalone 加载器、library / studies / 2827 / series-icons-map 各 bundle、图标映射）迁移进脚本，跑一遍验证产物与当前文件逐字节一致。

**验收**：删掉现有 bundle → 跑脚本重新生成 → 页面功能与现在完全相同。

## 3. M1：数据层 `/tv/footprint` 端点（约 1 天）

足迹的本质是"每根显示 K 线内部的分价成交量"，后端已有的 `ex.klines(code, frequency)` 可支撑聚合方案。

- **聚合策略**：取低一级频率的子 K 线（映射表：日线←5m、60m/30m←1m、5m←1m…），把每根子 K 线的成交量记入显示 K 线窗口内的价格箱。价格箱大小自适应：`(high − low) / 目标行数（约15~25行）`，对齐 mintick。
- **delta 近似（一期）**：子 K 线收阳/上涨 → 计买量，收阴 → 计卖量。真实逐笔 bid/ask（tdx 分笔仅近几日、币安 aggTrades 可做精确 delta）留二期。
- **接口**：`GET /tv/footprint?symbol&resolution&from&to`
  返回 `{"s": "ok", "bars": {"<ts>": [{"p": 价格, "vb": 买量, "vs": 卖量}, ...]}}`。
  带 `@login_required`，复用现有 `__history_req_counter` 限流模式，内存 LRU 缓存。
- **范围假设**：先支持 A 股（分钟数据最全），其他市场按 exchange 能力逐个开。

**验收**：pytest 单测（聚合正确性、分箱边界、限流）+ curl 抽查，分价量合计与该 K 线总成交量对账。

## 4. M2：渲染层 MVP（约 2~3 天，核心难点）

`static/js/footprint/` 模块结构：

| 文件 | 职责 |
|---|---|
| `loader.js` | 注册 `window.__FootprintPaneView`，模块入口 |
| `pane_view.js` | **组合**（而非继承）原蜡烛 PaneView：内部持有一个 `SeriesCandlesPaneView`（窄蜡烛骨架），自己的 `renderer()` 返回 `CompositeRenderer{蜡烛, FootprintRenderer}`；坐标复用蜡烛 items 的 `left/right/center` 像素值 + `priceScale` 价格→像素换算 |
| `data_cache.js` | 按可见范围增量 `fetch('/tv/footprint')`，Map 缓存（key = barTime），到货后触发重绘 |
| `renderer.js` | canvas 画格子：色块（按买卖比例着色）→ 数字文本，LOD 分级 |

**LOD（缩放自适应）分级**：

- `barSpacing ≥ 60px`：色块 + 数字；
- `20 ~ 60px`：仅色块；
- `< 20px`：退回蜡烛形态 —— 此时把 0.2 系数动态换成 1，**顺带根治"过早变细线"问题**。

**首日 spike**：先注入一个只画彩色矩形的 dummy renderer，运行时验证 `IPaneRenderer.draw(ctx, …)` 的确切签名（本规划唯一未完全查实的接口细节，最大不确定性最先消化）。

**验收**：A 股日线/分钟图上格子与数字正确对齐蜡烛、缩放平移无错位、一屏 300 根 × 20 行无明显掉帧。

## 5. M3：打磨（约 1~2 天）

- POC（最大成交价格行）高亮、底部 delta 汇总、失衡标记（对角比较）—— 按需取舍；
- 修状态栏 `TypeError`（定位样式 17 标题生成缺的字段，修复纳入补丁脚本）；
- 设置项（行数、文字开关）先走 `localStorage`，接入库设置面板留二期。

## 6. 风险清单

| 风险 | 应对 |
|---|---|
| renderer 接口签名与推断不符 | M2 首日 spike 验证；失败则改用"劫持 `renderer()` 返回值包一层"的备选注法 |
| 文本绘制性能 | LOD 分级 + 每帧只画可见 bar；数字只在最高档出现 |
| 库升级丢补丁 | M0 锚点脚本，替换失败即显式报错 |
| 授权边界 | 改动仅限自用部署的产物注册与外挂渲染，不扩散到分发场景 |

## 7. 总量与默认假设

- 总量约 **5~7 个工作日**，各里程碑独立可验收；M0/M1 不碰渲染、风险为零。
- 两个可推翻的默认假设：
  1. 先只做 A 股市场；
  2. delta 用分钟级近似而非逐笔数据。

## 附录：本次侦察查实的技术事实

- 库默认 `minBarSpacing: 0.5`（缩放下限，非退化阈值）；
- 普通蜡烛宽度算法 `optimalCandlestickWidth`：间距 2.5~4px 时实体固定 3 物理像素，>4px 按比例连续缩放，最小兜底 1 像素 —— 普通蜡烛只有一屏 800+ 根时才会退化成线；
- 样式 17 的设置面板已部分接入 `volFootprintStyle`（颜色类属性可用）；
- 图表页 widget 挂在 `window.tvWidget`，`ITimeScaleApi` 提供 `barSpacing()/setBarSpacing()/barSpacingChanged()` 可用于运行时测量与钳制。
