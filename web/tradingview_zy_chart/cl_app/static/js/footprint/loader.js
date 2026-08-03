/**
 * Volume Footprint 渲染模块入口（M2 spike 阶段）。
 *
 * 本文件由 charting_library 补丁注入到图表 iframe 中（先于 bundle 执行），
 * 在 window 上注册 __FootprintPaneView。library bundle 的 case 17 分支
 * 检测到它存在时，用它替代内置的窄蜡烛 SeriesCandlesPaneView。
 *
 * 当前为 spike 验证版：包装原蜡烛 PaneView，并在 CompositeRenderer 上
 * 追加一个画紫色矩形的 dummy renderer，用于验证：
 *   1. 注入与替换通道是否生效（图表左上角出现紫色半透明矩形）
 *   2. IPaneRenderer.draw 的真实参数签名（console 打印一次）
 */
(function () {
  "use strict";

  var loggedDrawArgs = false;

  function makeSpikeRenderer() {
    return {
      draw: function (ctx) {
        try {
          if (!loggedDrawArgs) {
            loggedDrawArgs = true;
            var args = Array.prototype.slice.call(arguments);
            console.log(
              "[fp-spike] draw 参数个数:", args.length,
              "参数值:", args.map(function (a) {
                if (a && a.constructor) return a.constructor.name;
                return typeof a;
              })
            );
            console.log("[fp-spike] draw 第2个参数内容:", args[1]);
          }
          ctx.save();
          ctx.fillStyle = "rgba(255, 0, 255, 0.35)";
          ctx.fillRect(8, 8, 120, 40);
          ctx.restore();
          window.__fpSpikeDrawCount = (window.__fpSpikeDrawCount || 0) + 1;
        } catch (err) {
          console.error("[fp-spike] draw 异常:", err);
        }
      },
      drawBackground: function () {},
      hitTest: function () {
        return null;
      },
    };
  }

  /**
   * 构造时返回一个 Proxy：除 renderer() 外全部委托给内置蜡烛 PaneView，
   * renderer() 在原 CompositeRenderer 上追加 spike renderer。
   */
  window.__FootprintPaneView = function (source, model, CandlesPaneView) {
    var inner = new CandlesPaneView(source, model, 0.2);
    return new Proxy(inner, {
      get: function (target, prop, receiver) {
        if (prop === "renderer") {
          return function () {
            var composite = target.renderer.apply(target, arguments);
            if (composite && typeof composite.append === "function") {
              composite.append(makeSpikeRenderer());
            } else if (!loggedDrawArgs) {
              console.warn("[fp-spike] renderer() 返回值不支持 append:", composite);
            }
            return composite;
          };
        }
        var value = Reflect.get(target, prop, target);
        return typeof value === "function" ? value.bind(target) : value;
      },
    });
  };

  console.log("[fp-spike] footprint loader 已加载");
})();
