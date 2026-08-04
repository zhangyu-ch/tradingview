// 防抖函数
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

// 图表管理类
class ChartManager {
  constructor(id) {
    this.id = id;
    this.widget = null;
    this.udf_datafeed = null;
    this.chart = null;
    this.debouncedAutoSave = debounce(() => this.handleAutoSaveNeeded(), 1000);
  }

  // 初始化图表
  init() {
    this.udf_datafeed = new Datafeeds.UDFCompatibleDatafeed("/tv", 30000);
    this.widget = window.tvWidget = new TradingView.widget({
      debug: false,
      autosize: true,
      fullscreen: false,
      container: "tv_chart_container_" + this.id,
      symbol: Utils.get_market() + ":" + Utils.get_code(),
      interval: Utils.get_local_data(
        Utils.get_market() + "_interval_" + this.id
      ),
      datafeed: this.udf_datafeed,
      library_path: "static/charting_library/",
      theme: Utils.get_local_data("theme"),
      numeric_formatting: { decimal_sign: "." },
      time_frames: [],
      timezone: "Asia/Shanghai",
      locale: "zh",
      symbol_search_request_delay: 100,
      auto_save_delay: 5,
      study_count_limit: 100,
      disabled_features: ["go_to_date"],
      enabled_features: [
        "study_templates",
        "seconds_resolution",
        "saveload_separate_drawings_storage",
      ],
      saved_data_meta_info: {
        uid: 1,
        name: "default",
        description: "default",
      },
      charts_storage_url: "/tv",
      charts_storage_api_version: "1.1",
      client_id: "tradingview_zy_" + Utils.get_market() + "_" + this.id,
      user_id: "999",
      load_last_chart: true,
      custom_indicators_getter: this.getCustomIndicators,
    });

    this.setupEventListeners();
    return this;
  }

  // 获取自定义指标
  getCustomIndicators(PineJS) {
    return Promise.resolve([
      TvIdxAMA.idx(PineJS),
      TvIdxATR.idx(PineJS),
      TvIdxCDBB.idx(PineJS),
      TvIdxCMCM.idx(PineJS),
      TvIdxDemo.idx(PineJS),
      TvIdxFCX.idx(PineJS),
      TvIdxHDLY.idx(PineJS),
      TvIdxHeima.idx(PineJS),
      TvIdxHLBLW.idx(PineJS),
      TvIdxHLFTX.idx(PineJS),
      TvIdxKDJ.idx(PineJS),
      TvIdxLTQS.idx(PineJS),
      TvIdxMA.idx(PineJS),
      TvIdxMACDBL.idx(PineJS),
      TvIdxVegasMA.idx(PineJS),
      TvIdxVOL.idx(PineJS),
      TvIdxRSX.idx(PineJS),
    ]);
  }

  // 设置事件监听
  setupEventListeners() {
    const global_widget = this.widget;
    this.widget.headerReady().then(function () {
      const buttonReload = global_widget.createButton();
      buttonReload.textContent = "重新加载数据";
      buttonReload.addEventListener("click", function () {
        global_widget.resetCache();
        global_widget.activeChart().resetData();
      });

      const buttonHideMark = global_widget.createButton();
      buttonHideMark.textContent = "隐藏标记";
      buttonHideMark.addEventListener("click", function () {
        global_widget.activeChart().clearMarks();
      });

      const buttonDeleteMark = global_widget.createButton();
      buttonDeleteMark.textContent = "删除标记";
      buttonDeleteMark.addEventListener("click", function () {
        let symbol = global_widget.symbolInterval();
        console.log(symbol);
        $.post({
          type: "POST",
          url: "/tv/del_marks",
          dataType: "json",
          data: {
            symbol: symbol.symbol,
          },
          success: function (res) {
            if (res.status == "ok") {
              global_widget.activeChart().clearMarks();
              layer.msg("删除标记成功");
            } else {
              layer.msg("删除标记失败");
            }
          },
        });
      });
    });

    this.widget.onChartReady(() => {
      this.chart = this.widget.activeChart();
      if (!this.chart) {
        console.error("Failed to get active chart");
        return;
      }

      this.chart
        .onSymbolChanged()
        .subscribe(null, (symbol) => this.handleSymbolChange(symbol));
      this.chart
        .onIntervalChanged()
        .subscribe(null, (interval) => this.handleIntervalChange(interval));
      this.chart
        .onDataLoaded()
        .subscribe(null, () => this.handleDataLoaded(), true);
      this.widget.subscribe("onTick", () => this.handleTick());
      this.widget.subscribe("onAutoSaveNeeded", () => this.debouncedAutoSave());
      this.handleAutoSaveNeeded();
    });
  }

  // 处理标的变化
  handleSymbolChange(symbol) {
    if (!symbol?.ticker) return;

    const [market, code] = symbol.ticker.split(":");
    if (!market || !code) return;

    if (Utils.get_market() !== market) {
      Utils.set_local_data("market", market);
      location.reload();
      return;
    }

    Utils.set_local_data("market", market);
    Utils.set_local_data(`${market}_code`, code);

    console.log(`${this.id} 标的变化：${symbol.ticker}`);

    if (typeof ZiXuan.render_zixuan_opts === "function") {
      ZiXuan.render_zixuan_opts();
    }
  }

  // 处理周期变化
  handleIntervalChange(interval) {
    if (!interval) return;

    const market = Utils.get_market();
    if (!market) return;

    Utils.set_local_data(`${market}_interval_${this.id}`, interval);
    console.log(`${this.id} 周期变化: ${interval}`);
  }

  // 处理数据加载
  handleDataLoaded() {
    console.log("数据重新加载");
  }

  // 处理自动保存
  handleAutoSaveNeeded() {
    this.widget.saveChartToServer(
      null,
      (error) => console.error("保存图表失败", error),
      { defaultChartName: "default" }
    );
  }

  // 处理tick事件
  handleTick() {
    console.log("数据更新");
  }
}

var Charts = (function () {
  return {
    /**
     * Display one autosized TradingView widget in an already-sized container.
     * @param {string} id Stable chart/container identifier.
     * @returns {object} The TradingView widget instance.
     */
    show_tv_chart: function (id) {
      const chartManager = new ChartManager(id).init();
      return chartManager.widget;
    },
  };
})();
