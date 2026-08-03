(function () {
  "use strict";

  var meta = document.querySelector('meta[name="csrf-token"]');
  if (!meta || !meta.content) {
    return;
  }
  var token = meta.content;
  var headerName = "X-CSRF-Token";
  var unsafeMethods = { POST: true, PUT: true, PATCH: true, DELETE: true };

  function methodOf(value) {
    return String(value || "GET").toUpperCase();
  }

  function isSameOrigin(url) {
    try {
      return new URL(url || window.location.href, window.location.href).origin === window.location.origin;
    } catch (error) {
      return false;
    }
  }

  window.TRADINGVIEW_ZY_CSRF_TOKEN = token;

  if (window.jQuery && window.jQuery.ajaxPrefilter) {
    window.jQuery.ajaxPrefilter(function (options, originalOptions, xhr) {
      if (unsafeMethods[methodOf(options.type || options.method)] && isSameOrigin(options.url)) {
        xhr.setRequestHeader(headerName, token);
      }
    });
  }

  if (window.fetch) {
    var originalFetch = window.fetch;
    window.fetch = function (input, init) {
      var options = Object.assign({}, init || {});
      var requestMethod = options.method || (input && input.method) || "GET";
      var requestUrl = typeof input === "string" ? input : input.url;
      if (unsafeMethods[methodOf(requestMethod)] && isSameOrigin(requestUrl)) {
        var headers = new Headers(options.headers || (input && input.headers) || {});
        headers.set(headerName, token);
        options.headers = headers;
      }
      return originalFetch.call(this, input, options);
    };
  }

  if (window.XMLHttpRequest) {
    var originalOpen = XMLHttpRequest.prototype.open;
    var originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url) {
      this.__tvCsrfMethod = methodOf(method);
      this.__tvCsrfUrl = url;
      return originalOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function () {
      if (unsafeMethods[this.__tvCsrfMethod] && isSameOrigin(this.__tvCsrfUrl)) {
        this.setRequestHeader(headerName, token);
      }
      return originalSend.apply(this, arguments);
    };
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form || !unsafeMethods[methodOf(form.method)]) {
      return;
    }
    var field = form.querySelector('input[name="_csrf_token"]');
    if (!field) {
      field = document.createElement("input");
      field.type = "hidden";
      field.name = "_csrf_token";
      form.appendChild(field);
    }
    field.value = token;
  });
})();
