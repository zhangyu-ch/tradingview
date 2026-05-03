# Web 端右侧扩展窗口开发指南

本文说明如何在 `web/tradingview_zy_chart` 的图表页右侧添加扩展窗口。

## 目标结构

右侧扩展窗口应作为图表页面的独立区域，不修改 TradingView 图表库源码。推荐结构：

```text
web/tradingview_zy_chart/cl_app/templates/index.html
web/tradingview_zy_chart/cl_app/static/js/right_panel.js
web/tradingview_zy_chart/cl_app/static/css/right_panel.css
```

## HTML 容器

在 `index.html` 的图表容器旁添加：

```html
<div id="main-layout">
  <div id="tv-chart-container"></div>
  <aside id="right-extension-panel" class="right-extension-panel">
    <div class="right-extension-panel__header">
      <span>扩展窗口</span>
      <button id="right-extension-panel-toggle" type="button">收起</button>
    </div>
    <div id="right-extension-panel-content" class="right-extension-panel__content"></div>
  </aside>
</div>
```

如果现有页面已经有外层布局容器，只需要保留 `aside#right-extension-panel`，并把图表区域和右侧窗口放在同一个 flex 容器下。

## CSS 布局

新增 `static/css/right_panel.css`：

```css
#main-layout {
  display: flex;
  width: 100%;
  height: 100vh;
}

#tv-chart-container {
  flex: 1 1 auto;
  min-width: 0;
}

.right-extension-panel {
  flex: 0 0 360px;
  border-left: 1px solid #d9d9d9;
  background: #ffffff;
  overflow: hidden;
}

.right-extension-panel.is-collapsed {
  flex-basis: 40px;
}

.right-extension-panel__header {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  border-bottom: 1px solid #eeeeee;
}

.right-extension-panel__content {
  height: calc(100% - 40px);
  overflow: auto;
  padding: 12px;
}
```

## JavaScript 初始化

新增 `static/js/right_panel.js`：

```javascript
(function () {
  function initRightPanel() {
    const panel = document.getElementById('right-extension-panel');
    const toggle = document.getElementById('right-extension-panel-toggle');
    const content = document.getElementById('right-extension-panel-content');
    if (!panel || !toggle || !content) {
      return;
    }

    toggle.addEventListener('click', function () {
      panel.classList.toggle('is-collapsed');
      toggle.innerText = panel.classList.contains('is-collapsed') ? '展开' : '收起';
    });

    window.tradingviewZyRightPanel = {
      setContent: function (html) {
        content.innerHTML = html;
      },
      clear: function () {
        content.innerHTML = '';
      }
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRightPanel);
  } else {
    initRightPanel();
  }
})();
```

## 页面引用

在 `index.html` 中引入：

```html
<link rel="stylesheet" href="/static/css/right_panel.css">
<script src="/static/js/right_panel.js"></script>
```

CSS 建议放在页面主样式之后，便于覆盖尺寸；JS 建议放在页面底部或现有业务脚本之前，确保业务脚本调用时 `window.tradingviewZyRightPanel` 已初始化。

## 与图表联动

业务代码可以通过全局对象更新右侧窗口：

```javascript
window.tradingviewZyRightPanel.setContent('<h3>策略结果</h3><p>等待信号...</p>');
```

如果需要根据当前标的更新内容，在 TradingView symbol change 回调中读取当前 `market`、`code`、`frequency`，请求后端接口并调用 `setContent()`。

```javascript
function refreshRightPanel(market, code) {
  fetch('/panel/strategy_results/' + market + '/' + code)
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      if (!window.tradingviewZyRightPanel) {
        return;
      }
      window.tradingviewZyRightPanel.setContent(JSON.stringify(payload.data || []));
    });
}
```

## 后端接口建议

新增接口时保持右侧窗口与图表低耦合：

```python
@app.route('/panel/strategy_results/<market>/<code>')
@login_required
def panel_strategy_results(market, code):
    return {"code": 0, "data": []}
```

接口返回普通 JSON，由 `right_panel.js` 或业务脚本渲染，不把 HTML 拼接逻辑放到后端。

## 开发注意事项

- 不修改 TradingView 图表库源码，只在外层页面组合扩展区域。
- 右侧窗口需要独立处理空数据、加载中和接口错误。
- 后端接口只返回当前窗口需要的数据，不触发额外图表重算。
- 扩展窗口内如需渲染用户输入内容，应先做转义，避免把未处理字符串直接拼进 `innerHTML`。
