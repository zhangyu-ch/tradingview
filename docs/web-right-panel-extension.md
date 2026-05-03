# Web 端右侧扩展窗口开发指南

本文说明如何在 `web/tradingview_zy_chart` 的图表页右侧添加扩展窗口。

## 目标结构

当前图表页 `web/tradingview_zy_chart/cl_app/templates/index.html` 已有右侧固定区域 `#chart_menu`，左侧图表区域为 `#chart_container`，TradingView 图表挂载在 `#tv_charts_area`。推荐把扩展窗口作为 `#chart_menu` 内的一个独立折叠项，而不是改 TradingView 图表库源码。

推荐新增或修改的文件：

```text
web/tradingview_zy_chart/cl_app/templates/index.html
web/tradingview_zy_chart/cl_app/static/js/right_panel.js
web/tradingview_zy_chart/cl_app/static/css/right_panel.css
```

## HTML 容器

在 `#chart_menu` 的 `.layui-collapse` 中添加一个折叠项，例如放在“监控提醒”后面：

```html
<div class="layui-colla-item" id="collapse-right-extension">
  <div class="layui-colla-title" data-ca-title="扩展窗口">扩展窗口</div>
  <div class="layui-colla-content" style="padding: 0">
    <div class="right-extension-panel__toolbar">
      <button id="right-extension-panel-refresh" type="button" class="layui-btn layui-btn-sm">
        刷新
      </button>
      <button id="right-extension-panel-clear" type="button" class="layui-btn layui-btn-primary layui-btn-sm">
        清空
      </button>
    </div>
    <div id="right-extension-panel-content" class="right-extension-panel__content"></div>
  </div>
</div>
```

如果要替换整个右侧菜单，可以重构 `#chart_container` 与 `#chart_menu` 的栅格宽度；默认建议先嵌入 `#chart_menu`，避免影响图表初始化尺寸。

## CSS 布局

新增 `static/css/right_panel.css`：

```css
.right-extension-panel__toolbar {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid #eeeeee;
}

.right-extension-panel__content {
  min-height: 160px;
  max-height: 420px;
  overflow: auto;
  padding: 10px;
  word-break: break-word;
}

.right-extension-panel__empty {
  color: #999999;
  font-size: 12px;
}

.right-extension-panel__item {
  padding: 8px 0;
  border-bottom: 1px solid #eeeeee;
}
```

## JavaScript 初始化

新增 `static/js/right_panel.js`。默认提供安全的文本渲染 API；只有渲染可信静态模板时才使用 HTML。

```javascript
(function () {
  function initRightPanel() {
    const content = document.getElementById('right-extension-panel-content');
    const refresh = document.getElementById('right-extension-panel-refresh');
    const clear = document.getElementById('right-extension-panel-clear');
    if (!content) {
      return;
    }

    function setText(text) {
      content.textContent = text || '';
      if (!content.textContent) {
        content.classList.add('right-extension-panel__empty');
        content.textContent = '暂无扩展内容';
      } else {
        content.classList.remove('right-extension-panel__empty');
      }
    }

    window.tradingviewZyRightPanel = {
      setText: setText,
      setTrustedHtml: function (html) {
        content.innerHTML = html;
      },
      clear: function () {
        setText('');
      }
    };

    if (refresh) {
      refresh.addEventListener('click', function () {
        document.dispatchEvent(new CustomEvent('tradingviewzy:right-panel-refresh'));
      });
    }
    if (clear) {
      clear.addEventListener('click', window.tradingviewZyRightPanel.clear);
    }

    setText('');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRightPanel);
  } else {
    initRightPanel();
  }
})();
```

`setTrustedHtml()` 只用于前端固定模板，不要把后端返回的用户文本或策略消息直接拼成 HTML。

## 页面引用

在 `index.html` 的现有 CSS 和业务 JS 附近引入：

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/right_panel.css') }}" />
<script type="text/javascript" src="{{ url_for('static', filename='js/right_panel.js') }}"></script>
```

CSS 建议放在 `app.css` 之后；JS 建议放在页面底部或现有业务脚本之前，确保业务脚本调用时 `window.tradingviewZyRightPanel` 已初始化。

## 与图表联动

业务代码可以通过全局对象更新右侧窗口：

```javascript
window.tradingviewZyRightPanel.setText('等待策略结果...');
```

如果需要根据当前标的更新内容，在 TradingView symbol change 回调中读取当前 `market`、`code`、`frequency`，请求后端接口并调用 `setText()`。

```javascript
function refreshRightPanel(market, code) {
  fetch('/panel/strategy_results/' + market + '/' + code)
    .then(function (response) { return response.json(); })
    .then(function (payload) {
      if (!window.tradingviewZyRightPanel) {
        return;
      }
      window.tradingviewZyRightPanel.setText(JSON.stringify(payload.data || [], null, 2));
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
- 默认嵌入 `#chart_menu`，避免破坏 `#chart_container` 和 `#tv_charts_area` 的尺寸计算。
- 右侧窗口需要独立处理空数据、加载中和接口错误。
- 后端接口只返回当前窗口需要的数据，不触发额外图表重算。
- 后端或策略返回的文本用 `textContent` / `setText()` 渲染；只有可信静态模板才使用 `innerHTML`。
