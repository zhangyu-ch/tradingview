(function () {
  "use strict";

  if (window.TRADINGVIEW_ZY_CSRF) {
    return;
  }
  var meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta || !meta.content) {
    return;
  }
  window.TRADINGVIEW_ZY_CSRF_TOKEN = meta.content;
  var headerName = "X-CSRF-Token";
  var unsafeMethods = { POST: true, PUT: true, PATCH: true, DELETE: true };
  var installed = new WeakSet();

  function methodOf(value) {
    return String(value || "GET").toUpperCase();
  }

  function install(win) {
    var doc;
    try {
      doc = win.document;
    } catch (error) {
      return false;
    }
    if (installed.has(doc)) {
      return true;
    }

    function token() {
      return window.TRADINGVIEW_ZY_CSRF_TOKEN;
    }

    function isSameOrigin(url) {
      try {
        // TradingView 使用 blob iframe；相对地址应以它的 <base> 解析。
        return new URL(url, doc.baseURI).origin === window.location.origin;
      } catch (error) {
        return false;
      }
    }

    if (win.fetch) {
      var originalFetch = win.fetch;
      win.fetch = function (input, init) {
        var options = Object.assign({}, init || {});
        var requestMethod = options.method || (input && input.method) || "GET";
        var requestUrl = input && typeof input.url === "string" ? input.url : input;
        if (unsafeMethods[methodOf(requestMethod)] && isSameOrigin(requestUrl)) {
          var headers = new win.Headers(options.headers || (input && input.headers) || {});
          headers.set(headerName, token());
          options.headers = headers;
        }
        return originalFetch.call(this, input, options);
      };
    }

    if (win.XMLHttpRequest) {
      var prototype = win.XMLHttpRequest.prototype;
      var originalOpen = prototype.open;
      var originalSend = prototype.send;
      var originalSetRequestHeader = prototype.setRequestHeader;
      prototype.open = function (method, url) {
        var result = originalOpen.apply(this, arguments);
        this.__tvCsrfUnsafe = unsafeMethods[methodOf(method)] && isSameOrigin(url);
        this.__tvCsrfHeaderSet = false;
        return result;
      };
      prototype.setRequestHeader = function (name, value) {
        var result = originalSetRequestHeader.apply(this, arguments);
        if (String(name).toLowerCase() === headerName.toLowerCase()) {
          this.__tvCsrfHeaderSet = true;
        }
        return result;
      };
      prototype.send = function () {
        // jQuery 也走 XHR；只在这一层注入，避免同名请求头被合并为两个 token。
        if (this.__tvCsrfUnsafe && !this.__tvCsrfHeaderSet) {
          this.setRequestHeader(headerName, token());
        }
        return originalSend.apply(this, arguments);
      };
    }

    doc.addEventListener("submit", function (event) {
      var form = event.target;
      if (!form || form.tagName !== "FORM") {
        return;
      }
      var submitter = event.submitter;
      var method = (submitter && submitter.getAttribute("formmethod")) || form.method;
      var action = (submitter && submitter.getAttribute("formaction")) || form.action;
      var field = form.querySelector('input[name="_csrf_token"]');
      if (!unsafeMethods[methodOf(method)] || !isSameOrigin(action)) {
        if (field && field.hasAttribute("data-tv-csrf")) {
          field.remove();
        }
        return;
      }
      if (!field) {
        field = doc.createElement("input");
        field.type = "hidden";
        field.name = "_csrf_token";
        field.setAttribute("data-tv-csrf", "");
        form.appendChild(field);
      }
      field.value = token();
    });
    installed.add(doc);
    return true;
  }

  window.TRADINGVIEW_ZY_CSRF = { install: install };
  install(window);
})();
