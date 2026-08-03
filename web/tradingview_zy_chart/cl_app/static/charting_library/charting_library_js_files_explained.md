# `charting_library` 四个 JavaScript 入口文件说明

本目录下的四个文件：

- `charting_library.cjs.js`
- `charting_library.esm.js`
- `charting_library.js`
- `charting_library.standalone.js`

本质上是同一套 TradingView Charting Library Widget 入口代码的不同打包格式。它们暴露的核心能力基本一致，主要包括：

- `TradingView.widget` / `widget`：创建图表 Widget 的入口类或构造器。
- `version`：当前库版本信息。
- 一系列枚举和类型常量，例如 `ActionId`、`ChartStyle`、`ConnectionStatus`、`SeriesType` 等。

它们的主要区别不是功能差异，而是面向不同运行环境和模块系统。

当前 `package.json` 中声明：

```json
{
  "type": "module",
  "main": "charting_library.cjs.js",
  "module": "charting_library.esm.js",
  "types": "charting_library.d.ts"
}
```

含义是：

- CommonJS 环境默认使用 `charting_library.cjs.js`。
- ES Module / 现代打包器优先使用 `charting_library.esm.js`。
- TypeScript 类型定义来自 `charting_library.d.ts`。

---

## 总览对比

| 文件 | 模块格式 | 主要使用场景 | 导出方式 | 是否适合 `<script>` 直接引入 |
|---|---|---|---|---|
| `charting_library.cjs.js` | CommonJS | Node.js、旧版构建系统、使用 `require()` 的项目 | `exports.widget`、`exports.version` 等 | 不推荐 |
| `charting_library.esm.js` | ES Module | Vite、Webpack、Rollup、现代前端项目 | `export { widget, version, ... }` | 可用于 `<script type="module">`，但通常由打包器处理 |
| `charting_library.js` | UMD | 浏览器全局变量、AMD、CommonJS 兼容场景 | 自动判断环境，挂到 `TradingView` 或 `exports` | 推荐用于普通浏览器 `<script>` |
| `charting_library.standalone.js` | Standalone / IIFE | 纯浏览器环境，不依赖模块系统 | 创建全局变量 `TradingView` | 推荐用于最简单的浏览器直接引入 |

---

## 1. `charting_library.cjs.js`

### 格式

这是 CommonJS 版本。

文件开头类似：

```js
"use strict";
...
exports.version = ...;
exports.widget = ...;
```

说明它通过 `exports` 对外暴露内容。

### 适用场景

适合以下环境：

- Node.js CommonJS 项目。
- 使用 `require()` 的旧项目。
- 某些老版本 Webpack / 构建工具。
- 服务端构建阶段需要解析该包入口时。

### 使用示例

```js
const TradingView = require('./charting_library.cjs.js');

const widget = new TradingView.widget({
  container: 'tv_chart_container',
  symbol: 'AAPL',
  interval: 'D',
  library_path: '/charting_library/',
});
```

也可以解构：

```js
const { widget, version } = require('./charting_library.cjs.js');

console.log(version);
```

### 注意点

当前 `package.json` 设置了：

```json
"type": "module"
```

在严格的 Node ESM 环境中，`.js` 文件可能会被当作 ES Module 处理。虽然该文件名里带有 `.cjs.js`，但扩展名仍然是 `.js`，具体能否直接 `require()` 取决于使用方式、打包器和包解析逻辑。

一般情况下，不建议在浏览器里直接通过 `<script>` 引入这个文件，因为浏览器原生不识别 CommonJS 的 `exports`。

---

## 2. `charting_library.esm.js`

### 格式

这是 ES Module 版本。

文件结尾类似：

```js
export {
  ...,
  version,
  widget
};
```

说明它通过标准 `export` 语法对外暴露内容。

### 适用场景

适合现代前端工程：

- Vite
- Rollup
- Webpack 5+
- ESBuild
- Next.js / Nuxt 等支持 ESM 的构建流程
- 原生浏览器 `<script type="module">`

### 使用示例

```js
import { widget, version } from './charting_library.esm.js';

console.log(version);

const tvWidget = new widget({
  container: 'tv_chart_container',
  symbol: 'AAPL',
  interval: 'D',
  library_path: '/charting_library/',
});
```

如果你的构建器支持从包目录解析，也可能直接写：

```js
import { widget } from './charting_library';
```

具体是否可行取决于项目的模块解析配置。

### 优点

- 使用标准模块语法。
- 更适合现代构建器分析依赖。
- 与 TypeScript / Vite / Rollup 等工具链配合更自然。

### 注意点

这个文件不是给普通 `<script>` 标签使用的。如果直接写：

```html
<script src="charting_library.esm.js"></script>
```

浏览器会报错，因为里面包含 `export` 语法。

如果确实要在浏览器中直接使用，需要：

```html
<script type="module">
  import { widget } from './charting_library.esm.js';

  new widget({
    container: 'tv_chart_container',
    symbol: 'AAPL',
    interval: 'D',
    library_path: '/charting_library/',
  });
</script>
```

---

## 3. `charting_library.js`

### 格式

这是 UMD 版本。

文件开头类似：

```js
(function (global, factory) {
  if (typeof exports === 'object' && typeof module !== 'undefined') {
    factory(exports);
  } else if (typeof define === 'function' && define.amd) {
    define(['exports'], factory);
  } else {
    factory(global.TradingView = {});
  }
})(this, function (exports) {
  ...
});
```

UMD 的特点是会自动识别当前运行环境：

- 如果是 CommonJS，则走 `exports`。
- 如果是 AMD，则走 `define()`。
- 如果是普通浏览器环境，则挂载到全局变量 `TradingView`。

### 适用场景

适合需要兼容多种加载方式的场景：

- 直接用 `<script>` 标签引入。
- 老项目里使用 AMD / RequireJS。
- 部分 CommonJS 构建环境。
- 不确定最终运行环境时的通用版本。

### 浏览器直接使用示例

```html
<div id="tv_chart_container"></div>

<script src="/charting_library/charting_library.js"></script>
<script>
  new TradingView.widget({
    container: 'tv_chart_container',
    symbol: 'AAPL',
    interval: 'D',
    library_path: '/charting_library/',
  });
</script>
```

### 优点

- 兼容性最好。
- 普通浏览器直接引入即可得到 `window.TradingView`。
- 同时兼容 AMD 和 CommonJS。

### 注意点

如果你已经在现代工程中使用 Vite / Webpack / Rollup，通常优先选 `charting_library.esm.js`，而不是 UMD 文件。

---

## 4. `charting_library.standalone.js`

### 格式

这是 Standalone / 自执行函数版本。

文件开头类似：

```js
var TradingView = (function (exports) {
  "use strict";
  ...
  exports.version = ...;
  exports.widget = ...;
  return exports;
})({});
```

它不走 CommonJS、AMD 或 ESM 判断，而是直接创建一个 `TradingView` 变量。

### 适用场景

适合最简单的浏览器直接引入场景：

- 静态 HTML 页面。
- 不使用任何模块系统。
- 不使用构建器。
- 希望引入后直接得到 `TradingView` 全局对象。

### 使用示例

```html
<div id="tv_chart_container"></div>

<script src="/charting_library/charting_library.standalone.js"></script>
<script>
  new TradingView.widget({
    container: 'tv_chart_container',
    symbol: 'AAPL',
    interval: 'D',
    library_path: '/charting_library/',
  });
</script>
```

### 和 `charting_library.js` 的区别

二者都适合浏览器直接引入，但有细微区别：

| 文件 | 特点 |
|---|---|
| `charting_library.js` | UMD，能兼容浏览器全局变量、AMD、CommonJS 等多种环境 |
| `charting_library.standalone.js` | 只面向普通浏览器全局变量场景，逻辑更直接 |

如果你的项目没有 AMD / CommonJS 需求，只是普通 HTML 页面，`standalone` 更直观。

如果你希望一个文件同时兼容更多加载方式，选 `charting_library.js`。

---

## 四个文件功能是否一样？

基本一样。

从代码结构看，四个文件都包含同一批核心逻辑和导出内容：

- `widget`
- `version`
- `ActionId`
- `ChartStyle`
- `ConnectionStatus`
- `SeriesType`
- `LineStyle`
- `MarketStatus`
- 其他图表、订单、价格轴、标记、通知相关枚举

它们的主要差异是打包壳不同：

- `cjs`：CommonJS 壳。
- `esm`：ES Module 壳。
- `js`：UMD 壳。
- `standalone`：浏览器全局变量壳。

可以理解为：里面的“库内容”基本相同，外面的“包装方式”不同。

---

## 如何选择

### 现代前端项目

例如 Vite / Webpack / Rollup / TypeScript 项目：

```js
import { widget } from './charting_library.esm.js';
```

推荐使用：

```text
charting_library.esm.js
```

---

### Node.js / CommonJS 项目

如果项目仍然使用：

```js
require(...)
```

推荐使用：

```text
charting_library.cjs.js
```

---

### 普通 HTML 页面

如果是最简单的页面：

```html
<script src="/charting_library/charting_library.standalone.js"></script>
```

推荐使用：

```text
charting_library.standalone.js
```

---

### 需要兼容 AMD / RequireJS / 浏览器全局变量

推荐使用：

```text
charting_library.js
```

---

## 推荐决策表

| 项目类型 | 推荐文件 |
|---|---|
| Vite / Vue / React / Rollup / Webpack 现代工程 | `charting_library.esm.js` |
| TypeScript 工程 | `charting_library.esm.js` + `charting_library.d.ts` |
| Node CommonJS / 老项目 | `charting_library.cjs.js` |
| 静态 HTML 页面 | `charting_library.standalone.js` |
| 需要最大兼容性的浏览器引入 | `charting_library.js` |
| 不确定使用哪一个 | 浏览器页面选 `standalone`，工程化项目选 `esm` |

---

## 文件大小参考

当前文件大小约为：

| 文件 | 大小 |
|---|---:|
| `charting_library.cjs.js` | 59 KB |
| `charting_library.esm.js` | 57 KB |
| `charting_library.js` | 59 KB |
| `charting_library.standalone.js` | 58 KB |

大小接近也说明它们主要是同一份逻辑的不同格式输出。

---

## 常见误区

### 误区 1：四个文件是四套不同功能的库

不是。

它们是同一个库的不同模块格式，不是四套不同能力的实现。

---

### 误区 2：浏览器里可以直接引入 `charting_library.esm.js`

不能用普通 `<script>` 直接引入。

错误写法：

```html
<script src="charting_library.esm.js"></script>
```

正确写法：

```html
<script type="module">
  import { widget } from './charting_library.esm.js';
</script>
```

或者直接使用：

```html
<script src="charting_library.standalone.js"></script>
```

---

### 误区 3：`charting_library.js` 和 `charting_library.standalone.js` 完全没有区别

二者在普通浏览器里效果很接近，但包装方式不同：

- `charting_library.js` 是 UMD，会自动兼容多种模块系统。
- `charting_library.standalone.js` 是纯浏览器全局变量版本。

---

## 一句话总结

- `charting_library.cjs.js`：给 CommonJS / `require()` 用。
- `charting_library.esm.js`：给现代 ES Module / 打包器用。
- `charting_library.js`：UMD 通用版，兼容浏览器、AMD、CommonJS。
- `charting_library.standalone.js`：纯浏览器全局变量版，适合静态页面直接 `<script>` 引入。
