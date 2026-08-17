# 真实足迹渲染（Volume Footprint）实施规划

> 制定日期：2026-07-30
> 最近核对：2026-08-17
> 关联提交：`d16d52d` 为 TradingView 图表库新增 Volume Footprint 图表类型
> 状态：M0 补丁工程与 M1 数据端点已完成；M2 注入 spike 已落地，正式渲染待实现；M3 待开始
>
> **M0 期间的重要修正**：侦察发现原版 CL v31.0.0 中本就存在样式 17 的渲染骨架
> （`case 17:case 19:case 1:` 复用蜡烛 PaneView、0.2 宽度系数、18 处
> `volFootprintStyle` 引用）——VolFootprint 是 TradingView 内置但未发布的
> 隐藏样式，`d16d52d` 的本质是"解锁"而非"新增"。0.2 窄蜡烛正是上游为
> 足迹单元格预留的骨架布局，M2 的渲染方案与上游意图吻合。

## 0. 现状基线与目标

### 现状

- 样式 `VolFootprint = 17` 已通过 `charting_library_patches/` 的 18 处锚点补丁注册进 vendored charting_library（CL v31.0.0）；6 个受管产物可由 `pristine + patches.json` 重放和逐字节校验。
- M1 数据层已经实现：`src/tradingview_zy/footprint.py` 聚合子周期 K 线，登录保护的 `GET /tv/footprint` 路由提供结果；当前测试覆盖聚合/缓存和静态 route guard，尚无 HTTP 行为测试。
- M2 已有两个 bundle 锚点和 `static/js/footprint/loader.js`：iframe 会加载外部 PaneView 包装器，但当前包装器只追加紫色矩形 dummy renderer，用于验证接入通道。
- **真实分价成交量单元格、数字、LOD 和增量前端数据缓存尚未实现。**
- 当前已知问题：
  1. fallback 仍使用 0.2 宽度系数，缩小时 K 线会比普通蜡烛更早退化成细线；
  2. 图表状态栏标题生成对样式 17 偶发 `TypeError: Cannot read properties of undefined (reading 'value')`；
  3. 选择样式 17 会显示 spike 的紫色调试矩形，不能视为可交付的足迹渲染。

### 目标

每根 K 线内按价格分层显示成交量单元格（色块 + 数字），支持买卖力量近似（delta），缩放时自适应降级，且整套扩展**可维护、可重放、升级库后可恢复**。

## 1. 架构总原则：最小锚点补丁 + 外部可读模块

基于两个已查实的技术事实：

- **接缝存在**：`SeriesCandlesPaneView.renderer()` 返回 `CompositeRenderer`，支持 `append()` 追加自定义 renderer —— 不必重写渲染管线，只需"蜡烛骨架 + 追加足迹层"。
- **样式 17 的实例化点只有一处**（上文 switch），是理想的劫持锚点。

当前已经落地两个一行级锚点补丁：

1. iframe 文档加载时注入 `<script src="/static/js/footprint/loader.js">`；
2. `case 17` 分支优先使用 `window.__FootprintPaneView`，loader 不可用时回退内置窄蜡烛。

正式渲染逻辑继续放在 `static/js/footprint/` 的可读模块中。只有在现有 spike 证明
外部模块无法复用必要能力时，才增加第三个补丁来暴露 `PaneRendererCandles`、
`optimalBarWidth` 等内部工具，避免无依据扩大 bundle 修改面。

## 2. M0：补丁工程化（已完成）

当前产物：

- `charting_library_patches/pristine/`：6 个原版受管文件；
- `charting_library_patches/patches.json`：18 处唯一锚点、替换内容和说明；
- `apply_patches.py`：重放补丁或用 `--check` 与 Web 生效文件逐字节比较；
- `extract_patches.py`：把受管产物与 pristine 的差异重新固化到 `patches.json`。

**当前验收命令**：

```bash
uv run --locked python charting_library_patches/apply_patches.py --check
```

## 3. M1：数据层 `/tv/footprint` 端点（已完成）

当前实现：

- `src/tradingview_zy/footprint.py` 用 `SUB_FREQUENCY_MAP` 选择子周期，把子 K 线成交量按价格区间分摊到约 18 个 1/2/5 归整后的价格箱；
- 子 K 线收盘价不低于开盘价时计入买量，否则计入卖量；这是 delta 近似，不是逐笔 bid/ask；
- `web/tradingview_zy_chart/cl_app/blueprints/udf.py` 暴露登录保护的
  `GET /tv/footprint?symbol&resolution&from&to`；不支持子周期时返回 `no_data`；
- Web services 使用 10 秒 TTL cache，key 为 symbol 和显示周期；
- `tests/test_footprint.py` 验证纯聚合函数的时间归属、成交量守恒、买卖拆分、分箱和 TTL cache，并进入 provider-contracts CI job；其他 Web 契约只静态检查路由注册、参数校验顺序和错误形状。

当前限制：尚无 Flask HTTP 行为测试覆盖登录、provider 调用、`no_data`、缓存命中和时间过滤。端点依赖 provider 已支持并缓存显示周期和子周期 K 线；不同频率成交量单位可能不一致，因此前端只能使用单根 bar 内的相对比例。当前没有独立的 footprint 请求限流器，也没有逐笔精确 delta。

## 4. M2：渲染层 MVP（spike 已落地，正式实现待完成）

现有 `loader.js` 已注册 `window.__FootprintPaneView`，用 Proxy 包装内置蜡烛
PaneView，并尝试向 CompositeRenderer 追加 dummy renderer。它用于记录真实
`draw()` 参数和验证 iframe/PaneView 接入通道，尚未消费 `/tv/footprint` 数据。

正式模块仍按以下边界拆分：

| 文件 | 职责 |
|---|---|
| `loader.js` | 当前 spike 入口；正式版本负责组装并注册 `window.__FootprintPaneView` |
| `pane_view.js` | **组合**（而非继承）原蜡烛 PaneView：内部持有一个 `SeriesCandlesPaneView`（窄蜡烛骨架），自己的 `renderer()` 返回 `CompositeRenderer{蜡烛, FootprintRenderer}`；坐标复用蜡烛 items 的 `left/right/center` 像素值 + `priceScale` 价格→像素换算 |
| `data_cache.js` | 按可见范围增量 `fetch('/tv/footprint')`，Map 缓存（key = barTime），到货后触发重绘 |
| `renderer.js` | canvas 画格子：色块（按买卖比例着色）→ 数字文本，LOD 分级 |

**LOD（缩放自适应）分级**：

- `barSpacing ≥ 60px`：色块 + 数字；
- `20 ~ 60px`：仅色块；
- `< 20px`：退回蜡烛形态 —— 此时把 0.2 系数动态换成 1，**顺带根治"过早变细线"问题**。

下一步先在真实浏览器中记录现有 spike 的 `draw()` 参数并确认 append 通道，再替换
紫色矩形。若接口签名与推断不符，优先包装 `renderer()` 返回值，不直接扩大 bundle
补丁。仓库目前没有覆盖该 Canvas 通道的自动化像素测试。

## 5. M3：打磨（约 1~2 天）

- POC（最大成交价格行）高亮、底部 delta 汇总、失衡标记（对角比较）—— 按需取舍；
- 修状态栏 `TypeError`（定位样式 17 标题生成缺的字段，修复纳入补丁脚本）；
- 设置项（行数、文字开关）先走 `localStorage`，接入库设置面板留二期。

## 6. 风险清单

| 风险 | 应对 |
|---|---|
| renderer 接口签名与推断不符 | 现有 M2 spike 先在真实浏览器记录参数；失败则包装 `renderer()` 返回值 |
| 文本绘制性能 | LOD 分级 + 每帧只画可见 bar；数字只在最高档出现 |
| 库升级丢补丁 | M0 锚点脚本，替换失败即显式报错 |
| 授权边界 | 改动仅限自用部署的产物注册与外挂渲染，不扩散到分发场景 |

## 7. 剩余工作与默认假设

- M0 和 M1 已完成；剩余工作是 M2 正式渲染与 M3 打磨。原始 5~7 个工作日估算已不再代表剩余工期，应在完成真实浏览器 spike 后重新估算。
- 两个可推翻的默认假设：
  1. 正式 UI 验收先以 A 股为主，但后端端点按 provider 的子周期能力工作；
  2. delta 继续使用子 K 线方向近似，逐笔数据属于后续能力。

## 附录：本次侦察查实的技术事实

- 库默认 `minBarSpacing: 0.5`（缩放下限，非退化阈值）；
- 普通蜡烛宽度算法 `optimalCandlestickWidth`：间距 2.5~4px 时实体固定 3 物理像素，>4px 按比例连续缩放，最小兜底 1 像素 —— 普通蜡烛只有一屏 800+ 根时才会退化成线；
- 样式 17 的设置面板已部分接入 `volFootprintStyle`（颜色类属性可用）；
- 图表页 widget 挂在 `window.tvWidget`，`ITimeScaleApi` 提供 `barSpacing()/setBarSpacing()/barSpacingChanged()` 可用于运行时测量与钳制。
