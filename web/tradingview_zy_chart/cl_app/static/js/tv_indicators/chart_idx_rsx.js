var TvIdxRSX = (function () {
  return {
    idx: function (PineJS) {
      return {
        name: "Jurik RSX",
        metainfo: {
          _metainfoVersion: 53,
          id: "CustomIndicatorsRSX@tv-basicstudies-1",
          description: "东@RSX",
          shortDescription: "RSX",
          is_price_study: false,
          isCustomIndicator: true,
          plots: [
            { id: "plot_rsx", type: "line" },
            { id: "plot_trend", type: "line" },
            { id: "plot_oblevel", type: "line" },
            { id: "plot_oslevel", type: "line" },
            { id: "plot_midline", type: "line" },
            { id: "plot_ob_fill", type: "histogram" },
            { id: "plot_os_fill", type: "histogram" },
          ],
          defaults: {
            palettes: {},
            styles: {
              plot_rsx: {
                linestyle: 0,
                linewidth: 2,
                plottype: 0,
                trackPrice: false,
                transparency: 0,
                visible: true,
                color: "#C0C0C0", // 灰色
              },
              plot_trend: {
                linestyle: 0,
                linewidth: 1,
                plottype: 0,
                trackPrice: false,
                transparency: 0,
                visible: true,
                color: "#FFD700", // 金色 - 趋势线
              },
              plot_oblevel: {
                linestyle: 1, // 虚线
                linewidth: 1,
                plottype: 0,
                trackPrice: false,
                transparency: 0,
                visible: true,
                color: "#FF6B6B", // 红色
              },
              plot_oslevel: {
                linestyle: 1, // 虚线
                linewidth: 1,
                plottype: 0,
                trackPrice: false,
                transparency: 0,
                visible: true,
                color: "#90EE90", // 绿色
              },
              plot_midline: {
                linestyle: 2,
                linewidth: 1,
                plottype: 0,
                trackPrice: false,
                transparency: 50,
                visible: true,
                color: "#808080", // 灰色 - 中线50
              },
              plot_ob_fill: {
                plottype: 1,
                transparency: 70,
                visible: true,
                color: "#FF6B6B", // 浅红色
                linewidth: 1,
                histogramBase: 70,
              },
              plot_os_fill: {
                plottype: 1,
                transparency: 70,
                visible: true,
                color: "#90EE90", // 浅绿色
                linewidth: 1,
                histogramBase: 30,
              },
            },
            inputs: {
              LENGTH: 14,
              OBLEVEL: 70,
              OSLEVEL: 30,
              EMA_PERIOD: 5,
            },
          },
          palettes: {},
          styles: {
            plot_rsx: { title: "RSX", histogramBase: 0 },
            plot_trend: { title: "趋势线", histogramBase: 0 },
            plot_oblevel: { title: "超买线", histogramBase: 0 },
            plot_oslevel: { title: "超卖线", histogramBase: 0 },
            plot_midline: { title: "中线", histogramBase: 0 },
            plot_ob_fill: { title: "超买区域", histogramBase: 70 },
            plot_os_fill: { title: "超卖区域", histogramBase: 30 },
          },
          inputs: [
            {
              id: "LENGTH",
              name: "RSX周期",
              type: "integer",
              defval: 14,
              min: 1,
              max: 100,
            },
            {
              id: "OBLEVEL",
              name: "超买线",
              type: "integer",
              defval: 70,
              min: 50,
              max: 90,
            },
            {
              id: "OSLEVEL",
              name: "超卖线",
              type: "integer",
              defval: 30,
              min: 10,
              max: 50,
            },
            {
              id: "EMA_PERIOD",
              name: "趋势线EMA周期",
              type: "integer",
              defval: 5,
              min: 2,
              max: 20,
            },
          ],
          format: {
            type: "price",
            precision: 2,
          },
        },
        constructor: function () {
          this.main = function (context, inputCallback) {
            this._context = context;
            this._input = inputCallback;

            // 获取输入参数
            var LENGTH = this._input(0);
            var OBLEVEL = this._input(1);
            var OSLEVEL = this._input(2);
            var EMA_PERIOD = this._input(3);

            // 获取价格数据
            const h = this._context.new_var(PineJS.Std.high(this._context));
            const l = this._context.new_var(PineJS.Std.low(this._context));
            const c = this._context.new_var(PineJS.Std.close(this._context));

            // ===== RSX 计算 =====
            // SRC := (H+L+C)/3;
            const src = this._context.new_var(
              (h.get(0) + l.get(0) + c.get(0)) / 3.0
            );

            // F8 := 100 * SRC;
            const f8 = this._context.new_var(100.0 * src.get(0));

            // F18 := 3 / (LENGTH + 2);
            const f18 = 3.0 / (LENGTH + 2.0);

            // F10 := REF(F8,1);
            const f10 = this._context.new_var(f8.get(1));

            // V8 := F8 - F10;
            const v8 = this._context.new_var(f8.get(0) - f10.get(0));

            // DMA函数: DMA(X, A) = A*X + (1-A)*REF(DMA(X,A),1)
            function dma(value, alpha) {
              // 固定顺序分配序列；同一根K线重算时始终读取上一根已完成值。
              const state = context.new_var();
              const prevValue = state.get(1);
              const nextValue = isNaN(prevValue)
                ? value
                : alpha * value + (1 - alpha) * prevValue;
              state.set(nextValue);
              return nextValue;
            }

            // F28 := DMA(V8, F18);
            const f28 = dma(v8.get(0), f18);

            // F30 := DMA(F28, F18);
            const f30 = dma(f28, f18);

            // VC := F28 * 1.5 - F30 * 0.5;
            const vc = f28 * 1.5 - f30 * 0.5;

            // F38 := DMA(VC, F18);
            const f38 = dma(vc, f18);

            // F40 := DMA(F38, F18);
            const f40 = dma(f38, f18);

            // V10 := F38 * 1.5 - F40 * 0.5;
            const v10 = f38 * 1.5 - f40 * 0.5;

            // F48 := DMA(V10, F18);
            const f48 = dma(v10, f18);

            // F50 := DMA(F48, F18);
            const f50 = dma(f48, f18);

            // V14 := F48 * 1.5 - F50 * 0.5;
            const v14 = f48 * 1.5 - f50 * 0.5;

            // F58 := DMA(ABS(V8), F18);
            const f58 = dma(Math.abs(v8.get(0)), f18);

            // F60 := DMA(F58, F18);
            const f60 = dma(f58, f18);

            // V18 := F58 * 1.5 - F60 * 0.5;
            const v18 = f58 * 1.5 - f60 * 0.5;

            // F68 := DMA(V18, F18);
            const f68 = dma(v18, f18);

            // F70 := DMA(F68, F18);
            const f70 = dma(f68, f18);

            // V1C := F68 * 1.5 - F70 * 0.5;
            const v1c = f68 * 1.5 - f70 * 0.5;

            // F78 := DMA(V1C, F18);
            const f78 = dma(v1c, f18);

            // F80 := DMA(F78, F18);
            const f80 = dma(f78, f18);

            // V20 := F78 * 1.5 - F80 * 0.5;
            const v20 = f78 * 1.5 - f80 * 0.5;

            // V4_ := IF(V20 > 0, (V14 / V20 + 1) * 50, 50);
            let v4_ = v20 > 0 ? (v14 / v20 + 1) * 50 : 50;

            // RSX_ := IF(V4_ > 100, 100, IF(V4_ < 0, 0, V4_));
            let rsx_ = v4_;
            if (rsx_ > 100) rsx_ = 100;
            if (rsx_ < 0) rsx_ = 0;

            // ===== 趋势线 EMA(RSX, EMA_PERIOD) =====
            const emaAlpha = 2.0 / (EMA_PERIOD + 1);
            const trend = dma(rsx_, emaAlpha);

            // ===== 填充区域 =====
            const ob_fill = rsx_ > OBLEVEL ? rsx_ : NaN;
            const os_fill = rsx_ < OSLEVEL ? rsx_ : NaN;

            // 返回结果
            return [
              rsx_, // 0: RSX主线
              trend, // 1: 趋势线
              OBLEVEL, // 2: 超买线
              OSLEVEL, // 3: 超卖线
              50, // 4: 中线
              ob_fill, // 5: 超买区域填充
              os_fill, // 6: 超卖区域填充
            ];
          };
        },
      };
    },
  };
})();
