# Strategy signal and trade-operation boundary

`StrategySignal` and backtesting `Operation` are intentionally different domain
models. Selection and monitoring describe an observed event; an operation
contains execution-specific position size, stop price and idempotency keys.
They must not be passed across domains by copying dictionaries or interpreting a
signal score as a position size.

Cross-scenario reuse is opt-in through `tradingview_zy.strategy_bridge`:

1. A monitoring signal must use `buy`, `sell`, `open` or `close` and include a
   JSON `metadata.trade` object with `position_rate`, `signal` and `key`.
2. `signal_to_trade_decision()` validates the versioned signal and creates a
   versioned `TradeDecision`; no execution value is inferred.
3. `trade_decision_to_operation()` embeds the full bridge snapshot in
   `Operation.info["strategy_bridge"]`.
4. `operation_to_strategy_signal()` only accepts that snapshot and rejects any
   operation whose code, action, size, stop, message or idempotency fields were
   changed afterwards.
5. Selection/watch/ignore signals and arbitrary legacy Operations are not
   executable conversions. Single-scenario strategies remain valid and need no
   bridge dependency.

The bridge creates an intent for paper/backtest execution. It does not enable
live trading or bypass the persisted Order/Fill reconciliation requirement.
