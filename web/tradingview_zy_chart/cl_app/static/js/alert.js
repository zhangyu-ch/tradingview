var SafeDomApi = (function (root) {
  if (root && root.SafeDom) {
    return root.SafeDom;
  }
  if (typeof module === "object" && module.exports) {
    return require("./safe_dom.js");
  }
  throw new Error("safe_dom.js must be loaded before alert.js");
})(typeof globalThis !== "undefined" ? globalThis : this);

var AlertSafeDom = (function (safeDom) {
  function text(value) {
    return safeDom.escapeHtml(value === null || value === undefined ? "" : value);
  }

  function recordRow(data) {
    return `
      <div class="alert-record-row">
        <div style="font-weight: bold; font-size: 14px;">
          ${text(data.name)} <span style="color: #888;">${text(data.code)}</span>
          <span style="color: #16baaa;">${text(data.frequency)}</span>
          <span style="color: #b37feb;">${text(data.event_type)}</span>
          <span style="color: #fa8c16;">${text(data.action)}</span>
          <span style="color: #52c41a;">${text(data.score)}</span>
        </div>
        <div style="font-size: 16px;">${text(data.msg)}</div>
        <div style="color: #888; font-size: 12px;">
          ${text(data.datetime_str)}
          <span style="margin-left: 10px; color: rgb(203, 243, 183);">${text(data.task_name)}</span>
        </div>
      </div>
    `;
  }

  return { text: text, recordRow: recordRow };
})(SafeDomApi);

var Alert = (function () {
  return {
    init: function () {
      layui.use(["table", "form"], function () {
        let form = layui.form;

        // 获取提醒任务列表并填充到select中
        $.get("/alert_list/" + Utils.get_market(), function (res) {
          if (res.code == 0) {
            const task_name_select = $("#task_name_select");
            task_name_select.empty();
            $("<option>", { value: "", text: "全部" }).appendTo(task_name_select);
            $.each(res.data, function (index, item) {
              $("<option>", {
                value: String(item.task_name ?? ""),
                text: String(item.task_name ?? ""),
              }).appendTo(task_name_select);
            });
            form.render("select");
          }
        });

        // 监听select选择器，选择后刷新列表
        form.on("select(task_name_select)", function (data) {
          Alert.get_alert_records();
        });
      });
    },

    get_alert_records: function () {
      layui.use(["table", "form"], function () {
        let table = layui.table;

        table.render({
          elem: "#table_alert_reocrds",
          defaultContextmenu: false,
          url:
            "/alert_records/" +
            Utils.get_market() +
            "?task_name=" +
            encodeURIComponent($("#task_name_select").val() || ""),
          page: false,
          className: "layui-font-12",
          size: "sm",
          maxHeight: 550,
          lineStyle: "height: auto;",
          cols: [
            [
              {
                field: "custom",
                title: "",
                templet: function (d) {
                  return AlertSafeDom.recordRow(d);
                },
              },
            ],
          ],
        });
        // 单击警报内容列表
        table.on("row(table_alert_reocrds)", function (obj) {
          let data = obj.data; // 获取当前行数据
          change_chart_ticker(Utils.get_market(), data.code);
        });
      });
    },

    refresh_alerts_table: function () {
      layui.use(["table", "dropdown", "util"], function () {
        let table = layui.table;
        let dropdown = layui.dropdown;

        function isPlainObject(value) {
          return value !== null && typeof value === "object" && !Array.isArray(value);
        }

        function parseStrategyConfig(row) {
          if (!row.strategy_config) {
            return {};
          }
          if (isPlainObject(row.strategy_config)) {
            return row.strategy_config;
          }
          try {
            let config = JSON.parse(row.strategy_config);
            return isPlainObject(config) ? config : {};
          } catch (e) {
            return {};
          }
        }

        function strategyKwargsText(row) {
          let config = parseStrategyConfig(row);
          let kwargs = config.strategy_kwargs || {};
          if (typeof kwargs === "string") {
            return kwargs;
          }
          return JSON.stringify(kwargs);
        }

        table.render({
          elem: "#table_alerts",
          defaultContextmenu: false,
          url: "/alert_list/" + Utils.get_market(),
          page: false,
          className: "layui-font-12",
          size: "sm",
          cols: [
            [
              {
                field: "task_name",
                title: "监控名称",
                templet: function (d) {
                  return AlertSafeDom.text(d.task_name);
                },
              },
              {
                field: "zx_group",
                title: "自选组",
                templet: function (d) {
                  return AlertSafeDom.text(d.zx_group);
                },
              },
              {
                filed: "frequency",
                title: "周期",
                templet: function (d) {
                  return AlertSafeDom.text(d.frequency);
                },
              },
              {
                filed: "interval_minutes",
                title: "运行间隔(分钟)",
                sort: true,
                templet: function (d) {
                  return AlertSafeDom.text(d.interval_minutes);
                },
              },
              {
                filed: "strategy_config",
                title: "策略路径（注册 ID）",
                templet: function (d) {
                  let config = parseStrategyConfig(d);
                  return AlertSafeDom.text(config.strategy_id || config.strategy_path || "");
                },
              },
              {
                filed: "strategy_kwargs",
                title: "策略参数",
                templet: function (d) {
                  return AlertSafeDom.text(strategyKwargsText(d));
                },
              },
              {
                filed: "strategy_memo",
                title: "策略备注",
                templet: function (d) {
                  return AlertSafeDom.text(d.strategy_memo || "");
                },
              },
              {
                filed: "is_send_msg",
                title: "发送消息",
                sort: true,
                templet: function (d) {
                  if (d.is_send_msg === 1) {
                    return "发送";
                  } else {
                    return "不发";
                  }
                },
              },
              {
                filed: "is_run",
                title: "启用",
                sort: true,
                templet: function (d) {
                  if (d.is_run === 1) {
                    return "启用";
                  } else {
                    return "禁用";
                  }
                },
              },
            ],
          ],
        });
        // 行双击事件( 双击事件为: rowDouble )
        table.on("row(table_alerts)", function (obj) {
          let data = obj.data; // 获取当前行数据
          layer.open({
            type: 2,
            title: "修改警报提醒",
            area: ["1000px", "90vh"],
            content: "/alert_edit/" + encodeURIComponent(Utils.get_market()) + "/" + encodeURIComponent(data.id),
            anim: 1,
            fixed: true, // 不固定
            shadeClose: true,
          });
        });
        // 右键菜单
        table.on("rowContextmenu(table_alerts)", function (obj) {
          let data = obj.data; // 获取当前行数据
          // 右键操作
          dropdown.render({
            trigger: "contextmenu",
            show: true,
            data: [{ title: "删除", id: "del" }],
            click: function (menuData, othis) {
              if (menuData["id"] === "del") {
                $.ajax({
                  type: "GET",
                  url: "/alert_del/" + encodeURIComponent(data.id),
                  dataType: "json",
                  success: function (res) {
                    if (res["ok"]) {
                      layer.msg("删除成功");
                    } else {
                      layer.msg("删除失败");
                    }
                    Alert.refresh_alerts_table();
                  },
                });
              }
            },
          });
        });
      });
    },
  };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = AlertSafeDom;
}
