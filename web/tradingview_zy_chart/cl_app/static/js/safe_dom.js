(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    root.SafeDom = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function toText(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function escapeHtml(value) {
    return toText(value).replace(/[&<>"']/g, function (character) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[character];
    });
  }

  function safeCssColor(value) {
    const color = toText(value).trim();
    return /^#[0-9a-f]{6}$/i.test(color) ? color : "";
  }

  function setText(element, value) {
    if (!element) {
      throw new TypeError("setText requires a DOM element");
    }
    element.textContent = toText(value);
    return element;
  }

  function appendOption(selectElement, value, label) {
    if (!selectElement || !selectElement.ownerDocument) {
      throw new TypeError("appendOption requires a select DOM element");
    }
    const option = selectElement.ownerDocument.createElement("option");
    option.value = toText(value);
    option.textContent = toText(label);
    selectElement.appendChild(option);
    return option;
  }

  return {
    appendOption: appendOption,
    escapeHtml: escapeHtml,
    safeCssColor: safeCssColor,
    setText: setText,
    toText: toText,
  };
});
