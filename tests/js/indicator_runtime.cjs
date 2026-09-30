/* Runs the shipped PineJS math AND bounded-series/context implementation, not a mock.
 * Bundle upgrades must update this loader explicitly instead of silently weakening tests.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const staticRoot = path.join(root, 'web/tradingview_zy_chart/cl_app/static');
const library = fs.readFileSync(path.join(staticRoot, 'charting_library/bundles/library.257d05210b16f5ddbfc2.js'), 'utf8');
const sandbox = {self: {}, console};
for (const source of [library, fs.readFileSync(path.join(staticRoot, 'charting_library/bundles/8224.a47a4a1d886aaa664d1e.js'), 'utf8')]) {
  vm.runInNewContext(source, sandbox);
}
const factories = Object.assign({}, ...sandbox.self.webpackChunktradingview.map(chunk => chunk[1]));
const modules = {};
function webpackRequire(id) {
  if (!modules[id]) {
    assert.ok(factories[id], `Missing vendor module ${id}`);
    const module = {exports: {}};
    modules[id] = module;
    factories[id](module, module.exports, webpackRequire);
  }
  return modules[id].exports;
}
webpackRequire.d = (exports, definitions) => {
  for (const [key, get] of Object.entries(definitions)) Object.defineProperty(exports, key, {get});
};
webpackRequire.r = exports => Object.defineProperty(exports, '__esModule', {value: true});
const PineJS = webpackRequire(34414);
const classesStart = library.indexOf('class wv{');
const classesEnd = library.indexOf('function Pv(', classesStart);
assert.ok(classesStart >= 0 && classesEnd > classesStart, 'Shipped PineJS context layout changed');
const Context = vm.runInNewContext(`${library.slice(classesStart, classesEnd)}; Tv`, {
  Yf: PineJS,
  console: {error: message => {throw new Error(message);}},
});

function createIndicator(name) {
  const source = fs.readFileSync(path.join(staticRoot, `js/tv_indicators/chart_idx_${name}.js`), 'utf8');
  const exports = vm.runInNewContext(`${source}; TvIdx${name.toUpperCase()}`, {console});
  return exports.idx(PineJS);
}

function createRunner(definition, inputs, body = new definition.constructor()) {
  const symbol = {index: -1, time: NaN, open: NaN, high: NaN, low: NaN, close: NaN, volume: NaN};
  const context = new Context(symbol);
  const input = index => inputs[index];
  if (body.init) body.init(context, input);
  // TradingView performs a no-data main() to discover series slots/history depths.
  body.main(context, input);
  const slotCount = context._vars.length;
  return {
    body, context,
    run(bar, isNewBar = true, enforceLayout = true) {
      Object.assign(symbol, bar, {isNewBar});
      if (isNewBar) symbol.index++;
      context.prepare(symbol);
      const result = Array.from(body.main(context, input));
      if (enforceLayout) assert.equal(context._varsIndex, slotCount, 'Series allocation order changed after warmup');
      return result;
    },
  };
}

module.exports = {createIndicator, createRunner, PineJS};
