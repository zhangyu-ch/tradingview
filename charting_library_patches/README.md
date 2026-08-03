# charting_library 补丁体系

对 vendored TradingView charting_library（CL v31.0.0）产物文件的所有修改，
统一以"锚点补丁"形式管理，保证可 review、可重放、库升级后可恢复。

> 背景与整体规划见仓库根目录 `FOOTPRINT_RENDERING_PLAN.md`（M0 阶段产物即本目录）。

## 目录结构

```
charting_library_patches/
├── README.md            本文件
├── patches.json         补丁数据：每条含 find（唯一锚点）/ replace / note
├── apply_patches.py     pristine + patches.json → 生成打好补丁的产物文件
├── extract_patches.py   当前产物 vs pristine 差异 → 生成/更新 patches.json
└── pristine/            原版未修改文件副本（提取自提交 d16d52d 之前）
```

## 常用命令

```bash
# 校验：当前生效文件是否与"pristine + 补丁"逐字节一致
python charting_library_patches/apply_patches.py --check

# 重放：从 pristine 重新生成全部打补丁文件（覆盖写入 charting_library/）
python charting_library_patches/apply_patches.py

# 固化：手工调试修改产物文件后，把差异提取回 patches.json（note 自动保留）
python charting_library_patches/extract_patches.py
```

## 工作流约定

1. **禁止只手改产物不提取**：任何对 `charting_library/` 下 6 个受管文件的修改，
   完成调试后必须运行 `extract_patches.py` 固化，并给新增补丁补 `note`。
2. **锚点唯一性**：`find` 必须在 pristine 中恰好出现一次；`apply_patches.py`
   在锚点失配时会报错退出——通常意味着库升级了，需人工重新定位。
3. **库升级流程**：用新版本文件替换 `pristine/`，运行 `apply_patches.py`，
   逐个处理报错的失效锚点。
4. **EOL 保护**：`.gitattributes` 已将 `charting_library/**` 与 `pristine/**`
   标记为 `-text`，禁止 git 做换行转换（历史上 CRLF 污染曾让补丁膨胀 38KB）。

## 当前补丁清单（16 处 / 6 文件）

全部服务于同一目的：**解锁 TradingView 内置但未发布的隐藏图表样式
`VolFootprint = 17`（成交量足迹图）**。

重要事实：原版库中已存在样式 17 的渲染骨架（`case 17:case 19:case 1:` 复用
`SeriesCandlesPaneView`，宽度系数 0.2 的窄蜡烛）及 18 处 `volFootprintStyle`
引用——上游只是把它排除在 UI 与枚举之外。本补丁集做的是注册枚举、样式菜单、
图标、默认配色与参数；**分价成交量单元格渲染上游并未实现**，由后续 M2 里程碑
以外挂模块补齐。

| 文件 | 补丁数 | 内容 |
|---|---|---|
| `bundles/library.257d…js` | 6 | 枚举注册、菜单顺序、解锁未支持列表、样式名映射、默认配色/参数 |
| `bundles/studies.d36…js` | 2 | 叠加系列涨跌色 switch 增加 case 17/19 |
| `bundles/2827.3dbd…js` | 1 | 设置对话框属性定义接入 volFootprintStyle |
| `bundles/series-icons-map.8e8…js` | 1 | 样式菜单图标（复用蜡烛图标） |
| `charting_library.d.ts` | 5 | ChartStyle/SeriesType 枚举、PreferencesMap、Favorites、Exclusions 类型声明 |
| `charting_library.standalone.js` | 1 | 加载器内枚举注册 |

每处补丁的具体说明见 `patches.json` 的 `note` 字段。

## 已知遗留问题

- 样式 17 启用后，图表状态栏标题生成偶发
  `TypeError: Cannot read properties of undefined (reading 'value')`。
  疑因 library 补丁 #4 只把 17 从未支持列表移除、未补 `BarSetRange` 配置条目。
  计划在 M3 里程碑修复（见 `FOOTPRINT_RENDERING_PLAN.md`）。
