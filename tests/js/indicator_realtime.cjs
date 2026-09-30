const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {createIndicator, createRunner} = require('./indicator_runtime.cjs');

function bars(seed, count, interval = 300000) {
  let randomState = seed;
  const random = () => ((randomState = (Math.imul(randomState, 1664525) + 1013904223) >>> 0) / 2 ** 32);
  let previous = 100;
  return Array.from({length: count}, (_, index) => {
    const phase = index % 180;
    const normal = 110 + 0.009 * index + 8 * Math.sin(index / 12) + 2 * Math.sin(index / 3);
    const crash = phase >= 125 && phase < 150 ? 0.57 + (phase - 125) / 150 : 1;
    const close = normal * crash * (0.985 + 0.03 * random());
    const range = phase >= 125 && phase < 153 ? 0.08 : 0.015;
    const bar = {
      time: 1704067200000 + index * interval,
      open: previous, high: Math.max(previous, close) * (1 + range * random()),
      low: Math.min(previous, close) * (1 - range * random()), close, volume: 1000 + 2000 * random(),
    };
    previous = close;
    return bar;
  });
}

const cases = [
  ['rsx', [14, 70, 30, 5]], ['rsx', [1, 85, 15, 2]], ['rsx', [100, 60, 40, 20]],
  ['hdly', []],
  ['ama', [10, 2, 30, 0]], ['ama', [10, 2, 30, 1]],
  ['ama', [1, 1, 100, 0]], ['ama', [1, 1, 100, 1]],
  ['cdbb', []],
  ['macdbl', [12, 26, 9, true, true, true, true]],
  ['macdbl', [3, 9, 3, false, false, true, true]],
];

// SHA256 of sequential historical outputs recorded before the B20 implementation.
// NaN/Infinity are encoded explicitly (JSON alone would collapse them to null).
const historicalDigests = {
  0: '8891061e1cafc83eb753e388714aec77bc21da9e9f81eedf2498f126f9966a14',
  1: '6bb0d93053af0d7b709b664fc91cbf5ce8664eada9d6afa4d0a0d149399f0700',
  2: '51070023fad5fe6b09f31514fe1cba9dcf76385440b50f6aaee7cf01a7c51bb1',
  3: '71a9dbf46960b3b396be4d8ea9e2a3c08c88257998c946c9abca8ac22c991cf5',
  4: 'a80fbae01f3cddc0b272d1611142ea16278fbc6de2f96d682605a657739dbad6',
  5: '2f8e813935bb48e2534ba663bf63e7c2b0293adbede7c6bb52eb2ce23b39b5dc',
  6: '55b2bf62392d6f39676890129a283f9cc51d0ce8cc45fce6ebe9bd241fe078a3',
  // N=1/type=1 has a dedicated mathematical oracle below, not the old all-NaN digest.
  8: '0dabb072d4684a0dd358a0edf8e142eee1dc45c577cd027c25589207973464a7',
  9: '03e0ee3a57fb923486db6a1e6708ca4fa54f405e885485d6b95a5dd807fc22f5',
  10: '9a5c71b52193f6e5b4c4619a9dfdd1a54eadf81c86ae5abde6edd7e7da423bba',
};
function digest(values) {
  return crypto.createHash('sha256').update(JSON.stringify(values, (_, value) => {
    if (typeof value === 'number' && !Number.isFinite(value)) return String(value);
    return value;
  })).digest('hex');
}
function equal(actual, expected, message) {
  assert.equal(actual.length, expected.length, message);
  actual.forEach((value, index) => {
    assert.ok(Object.is(value, expected[index]) || value === expected[index], `${message}, plot=${index}: ${value} != ${expected[index]}`);
  });
}

// Independent N=1/type=1 recurrence: ER is the current range divided by true
// range (including gaps), and the first available close seeds the moving average.
function amaN1Expected(data, inputs) {
  let previous = NaN;
  return data.map((bar, index) => {
    const priorClose = index ? data[index - 1].close : NaN;
    const range = bar.high - bar.low;
    const tr = Number.isNaN(priorClose) ? range
      : Math.max(range, Math.abs(bar.high - priorClose), Math.abs(bar.low - priorClose));
    const sc = Math.pow((range / tr) * (2 / (inputs[1] + 1) - 2 / (inputs[2] + 1)) + 2 / (inputs[2] + 1), 2);
    const current = Number.isNaN(previous) || Number.isNaN(sc)
      ? bar.close : previous + sc * (bar.close - previous);
    const result = [current, current > previous ? 0 : 1];
    previous = current;
    return result;
  });
}

const mode = process.argv[2];
const selected = process.argv.find(argument => argument.startsWith('--indicator='))?.split('=')[1];
let checked = 0;
let configurations = 0;
for (let caseIndex = 0; caseIndex < cases.length; caseIndex++) {
  const [name, inputs] = cases[caseIndex];
  if (selected && name !== selected) continue;
  configurations++;
  const definition = createIndicator(name);
  const data = bars(20260929, 1800);
  const runner = createRunner(definition, inputs);
  const historical = data.map(bar => runner.run(bar));
  if (mode === '--record') {
    console.log(`${caseIndex}: '${digest(historical)}', // ${name} ${JSON.stringify(inputs)} finite=${historical.reduce((n, row) => n + row.filter(Number.isFinite).length, 0)}`);
    if (name === 'macdbl') console.log('divergences', historical.filter(row => Number.isFinite(row[5])).length, historical.filter(row => Number.isFinite(row[6])).length);
    continue;
  }
  if (name === 'ama' && inputs[0] === 1 && inputs[3] === 1) {
    const expected = amaN1Expected(data, inputs);
    assert.ok(historical.every(row => Number.isFinite(row[0])), 'AMA N=1 must not remain NaN');
    historical.forEach((row, index) => equal(row, expected[index], `AMA N=1 formula ${index}`));
  } else {
    assert.equal(digest(historical), historicalDigests[caseIndex], `${name}: historical outputs changed`);
  }
  if (name === 'cdbb') assert.equal(historical.filter(row => Number.isFinite(row[0])).length, 4);
  if (name === 'macdbl') {
    assert.ok(historical.some(row => Number.isFinite(row[5])), 'Fixture must exercise bullish divergence');
    assert.ok(historical.some(row => Number.isFinite(row[6])), 'Fixture must exercise bearish divergence');
  }
  const realtime = createRunner(definition, inputs);
  let historyCapacity;
  data.forEach((bar, index) => {
    equal(realtime.run(bar), historical[index], `${name} next bar ${index}`);
    const capacity = realtime.context._vars.reduce((sum, series) => sum + series._hist.length, 0);
    if (index === 0) historyCapacity = capacity;
    assert.equal(capacity, historyCapacity, `${name}: history must remain bounded`);
    for (let repeat = 0; repeat < 4; repeat++) equal(realtime.run(bar, false), historical[index], `${name} repeat ${index}/${repeat}`);
    if (index % 67 === 0) {
      const changed = {...bar, close: bar.close * 1.04, high: bar.high * 1.06};
      const reference = createRunner(definition, inputs);
      for (const earlier of data.slice(0, index)) reference.run(earlier);
      const expected = reference.run(changed);
      equal(realtime.run(changed, false), expected, `${name} changed bar ${index}`);
      equal(realtime.run(changed, false), expected, `${name} changed repeat ${index}`);
      equal(realtime.run(bar, false), historical[index], `${name} reverted bar ${index}`);
    }
    checked += historical[index].length * 5;
  });
  // Library rebuilds the context on symbol/interval/input changes; reusing the body
  // must not carry hand-written arrays or scalar state into the new context.
  for (const interval of [60000, 86400000]) {
    const other = bars(42, 400, interval);
    const changedInputs = name === 'ama' ? [20, 4, 60, 1 - inputs[3]] : inputs;
    const reused = createRunner(definition, changedInputs, realtime.body);
    const fresh = createRunner(definition, changedInputs);
    other.forEach((bar, index) => equal(reused.run(bar), fresh.run(bar), `${name} reset ${interval}/${index}`));
  }
  // Zero/flat prices and missing warmup values must keep series slots/depth stable.
  const edge = createRunner(definition, inputs);
  for (let index = 0; index < 140; index++) {
    const price = index < 2 ? NaN : index < 70 ? 0 : 10;
    const bar = {time: index * 60000, open: price, high: price, low: price, close: price, volume: 0};
    const value = edge.run(bar);
    equal(edge.run(bar, false), value, `${name} edge repeat ${index}`);
  }
}
// Exercise non-unit smoothing, gaps, missing warmup, zero range, and context
// rebuilds back INTO N=1. Expectations never come from another indicator run.
if (mode !== '--record' && (!selected || selected === 'ama')) {
  const definition = createIndicator('ama');
  for (const inputs of [[1, 1, 100, 1], [1, 2, 30, 1]]) {
    const data = [
      [NaN, NaN, NaN], [NaN, NaN, NaN], [12, 8, 10],
      [16, 12, 14], [15, 11, 12], [12, 12, 12], [0, 0, 0], [0, 0, 0], [5, 1, 3],
    ].map(([high, low, close], index) => ({time: index * 60000, open: close, high, low, close, volume: 0}));
    const expected = amaN1Expected(data, inputs);
    assert.ok(Number.isNaN(expected[0][0]) && Number.isNaN(expected[1][0]));
    assert.equal(expected[2][0], 10);
    assert.ok(expected.slice(2).every(row => Number.isFinite(row[0])));
    assert.ok(expected[3][0] > 10 && expected[3][0] < 14, 'Gap ER must retain genuine smoothing');
    const runner = createRunner(definition, inputs);
    let layout;
    const check = (bar, isNew, wanted, label) => {
      equal(runner.run(bar, isNew), wanted, label);
      const depths = Array.from(runner.context._vars, series => series._hist.length);
      if (!layout) layout = depths;
      assert.deepEqual(depths, layout, `${label}: per-slot history depths changed`);
    };
    data.forEach((bar, index) => {
      check(bar, true, expected[index], `AMA N=1 warmup/history ${index}`);
      check(bar, false, expected[index], `AMA N=1 duplicate ${index}`);
      const changed = {...bar, high: 22, low: 14, close: 18};
      const changedExpected = amaN1Expected([...data.slice(0, index), changed], inputs)[index];
      check(changed, false, changedExpected, `AMA N=1 changed ${index}`);
      check(changed, false, changedExpected, `AMA N=1 changed repeat ${index}`);
      check(bar, false, expected[index], `AMA N=1 reverted ${index}`);
    });
    // Commit a changed tick and verify the next bar reads that final value.
    const committed = {...data.at(-1), high: 24, low: 14, close: 20};
    const next = {...committed, time: committed.time + 60000, high: 26, low: 18, close: 22};
    const committedExpected = amaN1Expected([...data.slice(0, -1), committed, next], inputs);
    check(committed, false, committedExpected.at(-2), 'AMA N=1 changed close commit');
    check(next, true, committedExpected.at(-1), 'AMA N=1 after changed close');
    for (const interval of [60000, 86400000]) {
      const switched = createRunner(definition, [10, 4, 60, 0], runner.body);
      bars(99, 40, interval).forEach(bar => switched.run({...bar, tickerid: 'OTHER'}));
      const reset = createRunner(definition, inputs, switched.body);
      const other = bars(42, 80, interval).map(bar => ({...bar, tickerid: 'N1'}));
      const resetExpected = amaN1Expected(other, inputs);
      other.forEach((bar, index) => {
        equal(reset.run(bar), resetExpected[index], `AMA N=1 reset ${interval}/${index}`);
        equal(reset.run(bar, false), resetExpected[index], `AMA N=1 reset duplicate ${interval}/${index}`);
        assert.deepEqual(Array.from(reset.context._vars, series => series._hist.length), layout);
      });
    }
  }
  console.log('AMA N=1 passed: numerical oracle, warmup, changed ticks, committed close, reset and fixed slot depths');
}
assert.ok(configurations > 0, 'No indicator configuration selected');
if (mode !== '--record') console.log(`B20 passed: ${configurations} configurations, ${checked} historical/realtime plot comparisons plus changed-bar/reset/warmup checks`);
