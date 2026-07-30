var SafeDomApi = (function (root) {
  if (root && root.SafeDom) {
    return root.SafeDom;
  }
  if (typeof module === "object" && module.exports) {
    return require("./safe_dom.js");
  }
  throw new Error("safe_dom.js must be loaded before zixuan.js");
})(typeof globalThis !== "undefined" ? globalThis : this);

function renderZixuanCodeCell(data) {
  const color = SafeDomApi.safeCssColor(data.color);
  const style = color === "" ? "" : ' style="color:' + color + '"';
  return (
    "<div" +
    style +
    ' class="layui-font-14">' +
    SafeDomApi.escapeHtml(data.name) +
    "</div>" +
    '<div class="layui-font-12 layui-font-gray">' +
    SafeDomApi.escapeHtml(data.code) +
    "</div>"
  );
}

function renderZixuanRateCell(data) {
  return (
    '<div class="code_rate" data-code="' +
    SafeDomApi.escapeHtml(data.code) +
    '"><div class="layui-font-14">' +
    SafeDomApi.escapeHtml(data.rate) +
    "%</div>" +
    '<div class="layui-font-12">' +
    SafeDomApi.escapeHtml(data.price) +
    "</div></div>"
  );
}


function sanitizeSearchItems(items) {
  if (!Array.isArray(items)) {
    return [];
  }
  return items.map(function (item) {
    const source = item || {};
    const rawName = SafeDomApi.toText(
      source.raw_name === undefined ? source.name : source.raw_name
    );
    return Object.assign({}, source, {
      raw_name: rawName,
      name: SafeDomApi.escapeHtml(rawName),
      value: SafeDomApi.toText(source.value),
    });
  });
}

function updateZixuanRateElements(tick, color) {
  const code = SafeDomApi.toText(tick.code);
  document.querySelectorAll(".code_rate").forEach(function (element) {
    if (element.dataset.code !== code) {
      return;
    }
    element.style.color = color;
    element.replaceChildren();

    const rate = document.createElement("div");
    rate.className = "layui-font-14";
    rate.style.color = color;
    SafeDomApi.setText(rate, SafeDomApi.toText(tick.rate) + "%");

    const price = document.createElement("div");
    price.className = "layui-font-12";
    SafeDomApi.setText(price, tick.price);

    element.append(rate, price);
  });
}

var ZiXuan = (function () {
  var zx_group = "我的关注";

  return {
    render_zixuan_opts: function () {
      $.ajax({
        type: "GET",
        url:
          "/get_stock_zixuan/" +
          encodeURIComponent(Utils.get_market()) +
          "/" +
          encodeURIComponent(Utils.get_code().replace("/", "__")),
        dataType: "json",
        success: function (res) {
          let data = [];
          layui.each(res, function (i, e) {
            const groupName = SafeDomApi.toText(e["zx_name"]);
            const checked = e["exists"] === 0 ? "" : " checked";
            const templet =
              '<span><input type="checkbox"' +
              checked +
              " /> " +
              SafeDomApi.escapeHtml(groupName) +
              "</span>";
            data.push({
              // Layui renders title/templet as HTML. Only escaped display values go in
              // those fields; group_name keeps the original value for the API call.
              title: SafeDomApi.escapeHtml(groupName),
              group_name: groupName,
              id: i,
              templet: templet,
              exists: e["exists"],
              code: SafeDomApi.toText(e["code"]),
            });
          });
          // 再重新请求一遍自选列表，刷新
          $("#zixuan_groups").change();
          layui.dropdown.reloadData("add_zixuan", {
            data: data,
          });
        },
      });
    },
    stocks_update_rate: function () {
      // 更新展示的股票列表涨跌幅
      let codes = [];
      $(".code_rate").each(function () {
        codes.push($(this).data("code"));
      });
      if (codes.length === 0) {
        return true;
      }
      $.ajax({
        type: "POST",
        url: "/ticks",
        data: { market: Utils.get_market(), codes: JSON.stringify(codes) },
        dataType: "json",
        success: function (ticks) {
          for (let i = 0; i < ticks["ticks"].length; i++) {
            const tick = ticks["ticks"][i];
            let color = tick["rate"] > 0 ? "#ff5722" : "#16baaa";
            if (tick["rate"] === 0) {
              color = "";
            }
            updateZixuanRateElements(tick, color);
          }
          const now_trading = ticks["now_trading"];
          if (now_trading !== true) {
            clearInterval(interval_update_rates);
          }
        },
      });
    },
    render_zixuan_stocks: function () {
      // 自选列表渲染与操作
      layui.use(["table", "dropdown", "util"], function () {
        let table = layui.table;
        let dropdown = layui.dropdown;
        // 创建自选列表渲染实例
        table.render({
          elem: "#table_zixuan_list",
          defaultContextmenu: false,
          url:
            "/get_zixuan_stocks/" +
            encodeURIComponent(Utils.get_market()) +
            "/" +
            encodeURIComponent(ZiXuan.zx_group),
          page: false,
          className: "layui-font-12",
          size: "sm",
          lineStyle: "height: 52px;",
          loading: true,
          cols: [
            [
              {
                field: "code",
                title: "标的",
                sort: false,
                templet: function (d) {
                  return renderZixuanCodeCell({
                    color: d.color,
                    name: d.name,
                    code: d.code,
                  });
                },
              },
              {
                field: "zf",
                title: "涨跌幅",
                sort: false,
                width: 70,
                templet: function (d) {
                  return renderZixuanRateCell({
                    code: d.code,
                    price: "-",
                    rate: "-",
                  });
                },
              },
            ],
          ],
          done: function () {
            ZiXuan.stocks_update_rate();
          },
        });
        // 行单击事件( 双击事件为: rowDouble )
        table.on("row(table_zixuan_list)", function (obj) {
          const data = obj.data; // 获取当前行数据
          const code = data.code;
          change_chart_ticker(Utils.get_market(), code);
          $("#ai_code").val(code);
          table.setRowChecked("table_zixuan_list", {
            index: "all", // 所有行
            checked: false,
          });
          table.setRowChecked("table_zixuan_list", {
            index: obj.index, // 选中行的下标。 0 表示第一行
          });
        });
        // 右键菜单
        table.on("rowContextmenu(table_zixuan_list)", function (obj) {
          let data = obj.data; // 获取当前行数据
          // 右键操作
          let menu_data = [
            { title: "删除", id: "del" },
            { title: "置顶", id: "sort_1", direction: "top" },
            { title: "置底", id: "sort_2", direction: "bottom" },
            {
              title: "色彩",
              id: "color_1",
              color: "#ff5722",
              templet: function () {
                return '<div class="layui-bg-red">红色</div>';
              },
            },
            {
              title: "色彩",
              id: "color_2",
              color: "#ffb800",
              templet: function () {
                return '<div class="layui-bg-orange">橙色</div>';
              },
            },
            {
              title: "色彩",
              id: "color_3",
              color: "#16baaa",
              templet: function () {
                return '<div class="layui-bg-green">绿色</div>';
              },
            },
            {
              title: "色彩",
              id: "color_4",
              color: "#1e9fff",
              templet: function () {
                return '<div class="layui-bg-blue">蓝色</div>';
              },
            },
            {
              title: "色彩",
              id: "color_5",
              color: "#a233c6",
              templet: function () {
                return '<div class="layui-bg-purple">紫色</div>';
              },
            },
            {
              title: "色彩",
              id: "color_6",
              color: "",
              templet: function () {
                return '<div class="layui-bg-gray">清除颜色</div>';
              },
            },
          ];
          if (Utils.get_market() === "a") {
            menu_data.splice(3, 0, { title: "操盘必读", id: "dfcf" });
          }
          dropdown.render({
            trigger: "contextmenu",
            show: true,
            data: menu_data,
            click: function (menuData, othis) {
              if (menuData["id"] === "del") {
                $.ajax({
                  type: "POST",
                  url: "/set_stock_zixuan",
                  data: {
                    opt: "DEL",
                    market: Utils.get_market(),
                    group_name: ZiXuan.zx_group,
                    code: data.code,
                    color: "",
                    direction: "",
                  },
                  dataType: "json",
                  success: function (res) {
                    if (res["ok"]) {
                      layer.msg("删除成功");
                      obj.del();
                    } else {
                      layer.msg("删除失败");
                    }
                  },
                });
              } else if (menuData["title"] === "色彩") {
                $.ajax({
                  type: "POST",
                  url: "/set_stock_zixuan",
                  data: {
                    opt: "COLOR",
                    market: Utils.get_market(),
                    group_name: ZiXuan.zx_group,
                    code: data.code,
                    color: menuData["color"],
                    direction: "",
                  },
                  dataType: "json",
                  success: function (res) {
                    obj.update(
                      {
                        color: menuData["color"],
                      },
                      true
                    );
                  },
                });
              } else if (
                menuData["id"] === "sort_1" ||
                menuData["id"] === "sort_2"
              ) {
                $.ajax({
                  type: "POST",
                  url: "/set_stock_zixuan",
                  data: {
                    opt: "SORT",
                    market: Utils.get_market(),
                    group_name: ZiXuan.zx_group,
                    code: data.code,
                    color: "",
                    direction: menuData["direction"],
                  },
                  dataType: "json",
                  success: function (res) {
                    // 再重新请求一遍自选列表，刷新
                    ZiXuan.render_zixuan_stocks();
                  },
                });
              } else if (menuData["id"] === "dfcf") {
                window.open(
                  "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html?type=web&code=" +
                    encodeURIComponent(data.code.replace(".", ""))
                );
              }
            },
          });
        });
      });
    },
    init_zixuan_opts: function () {
      // 自选操作下拉菜单
      layui.use(function () {
        var layer = layui.layer;
        var dropdown = layui.dropdown;
        var form = layui.form;

        // 获取自选组
        $.ajax({
          type: "GET",
          url: "/get_zixuan_groups/" + Utils.get_market(),
          dataType: "json",
          success: function (res) {
            let zixuan_groups = $("#zixuan_groups");
            zixuan_groups.empty();
            layui.each(res, function (i, r) {
              SafeDomApi.appendOption(
                zixuan_groups[0],
                r.name,
                r.name
              );
            });
            layui.form.render($(zixuan_groups));
            $(zixuan_groups)
              .siblings("div.layui-form-select")
              .find("dl")
              .find("dd")[0]
              .click();
          },
        });

        dropdown.render({
          elem: "#add_zixuan",
          data: [],
          click: function (data, othis) {
            let opt = "ADD";
            if (data["exists"] === 1) {
              opt = "DEL";
            }
            $.ajax({
              type: "POST",
              url: "/set_stock_zixuan",
              data: {
                opt: opt,
                market: Utils.get_market(),
                group_name: data["group_name"],
                code: data["code"],
                color: "",
                direction: "",
              },
              dataType: "json",
              success: function (res) {
                if (data["group_name"] === ZiXuan.zx_group) {
                  ZiXuan.render_zixuan_opts();
                  ZiXuan.render_zixuan_stocks();
                }
              },
            });
            return false;
          },
        });
        // 自选组变化
        form.on("select(select_zx_group)", function (data) {
          ZiXuan.zx_group = data.value;
          ZiXuan.render_zixuan_stocks();
        });
        // 刷新自选操作
        $("#refresh_zixuan").click(function () {
          ZiXuan.render_zixuan_stocks();
        });

        // 代码搜索
        const searchSelect = xmSelect.render({
          el: "#code_search",
          filterable: true,
          remoteSearch: true,
          radio: true,
          clickClose: true,
          tips: "商品代码搜索",
          empty: "没有搜索商品",
          theme: {
            color: "#e54d42",
            // hover: '#e54d42',
          },
          delay: 1000,
          remoteMethod: function (val, cb, show) {
            if (val) {
              $.ajax({
                type: "GET",
                url:
                  "/tv/search?limit=30&type=&query=" +
                  encodeURIComponent(val) +
                  "&exchange=" +
                  encodeURIComponent(Utils.get_market()),
                dataType: "json",
                success: function (res) {
                  let lst = [];
                  layui.each(res, function (i, r) {
                    const rawName =
                      SafeDomApi.toText(r["symbol"]) +
                      ":" +
                      SafeDomApi.toText(r["description"]);
                    lst.push({
                      raw_name: rawName,
                      name: SafeDomApi.escapeHtml(rawName),
                      value: SafeDomApi.toText(r["symbol"]),
                    });
                  });
                  cb(lst);
                },
              });
            } else {
              // 远程搜索时，文本框内物搜索关键字，使用缓存的历史记录展示
              let storedItems =
                JSON.parse(
                  localStorage.getItem(Utils.get_market() + "_selectedItems")
                ) || [];
              cb(sanitizeSearchItems(storedItems));
            }
          },
          show: function () {
            // 展开折叠面板加载历史记录
            let storedItems =
              JSON.parse(
                localStorage.getItem(Utils.get_market() + "_selectedItems")
              ) || [];
            searchSelect.update({
              data: sanitizeSearchItems(storedItems),
            });
          },
          on: function (data) {
            if (data.arr.length > 0) {
              change_chart_ticker(Utils.get_market(), data.arr[0]["value"]);
              Utils.add_to_cache(data);
            }
          },
          data: [],
        });
      });
    },
  };
})();

if (typeof module === "object" && module.exports) {
  module.exports = {
    SafeDomApi: SafeDomApi,
    renderZixuanCodeCell: renderZixuanCodeCell,
    renderZixuanRateCell: renderZixuanRateCell,
    updateZixuanRateElements: updateZixuanRateElements,
    sanitizeSearchItems: sanitizeSearchItems,
    ZiXuan: ZiXuan,
  };
}
