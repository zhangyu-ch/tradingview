var AI = (function () {
  function showUnavailable() {
    layui.use(["layer"], function () {
      layui.layer.msg("AI 分析入口已不可用，请改用自定义策略接口。", { time: 2500 });
    });
  }

  return {
    get_ai_analyse_records: showUnavailable,
    init_ai_opts: function () {
      $("#ai_analyse_btn").click(showUnavailable);
    },
  };
})();
