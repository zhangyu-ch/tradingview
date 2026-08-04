# Versioned strategy signal protocol

Selection and monitoring strategies must return one of:

- `None`;
- one `StrategySignal`;
- a materialized `list[StrategySignal]` containing at most 64 entries.

Generators, tuples, arbitrary iterables and raw dictionaries are rejected. Task runners must return `BatchRunResult`; the Web task layer does not accept legacy raw signal lists.

## Schema v1

Every accepted signal is canonicalized at the runner boundary and contains:

| Field | Contract |
|---|---|
| `schema_version` | Exact integer `1`; booleans and unknown versions are rejected. |
| `code`, `name`, `frequency` | Non-empty UTF-8 text and exact match for the current target. |
| `action` | `StrategyAction`, constrained by `StrategyPurpose`. |
| `score` | Finite real number; booleans, NaN and infinity are rejected. |
| `message` | Non-empty text, at most 2,000 characters, no control characters or invalid Unicode. |
| `event_time` | `datetime`; naive values are interpreted in the target market timezone, aware values are converted to it, and timestamps more than five minutes in the future are rejected. |
| `metadata` | A bounded JSON object. It is deep-copied, contains no executable Python objects or non-finite numbers, and is limited by depth, node count and UTF-8 bytes. |

`StrategySignal.to_payload()` returns a stable JSON-safe representation with an ISO-8601 event timestamp and the action serialized as its string value.

## Purpose-specific actions

Selection accepts:

- `select`
- `ignore`

Monitoring accepts:

- `watch`
- `buy`
- `sell`
- `open`
- `close`
- `ignore`

`ignore` is a deliberate miss. It is never emitted as a persisted hit.

## Failure semantics

The standard runners report failures in `BatchRunResult` using the existing stages:

- `target`
- `provider`
- `input`
- `strategy`
- `output`

A malformed signal is an `output` failure for that target. Other targets in the batch continue. Selection tasks publish a replacement snapshot only when the entire batch has no failures; monitoring tasks may persist valid hits while returning an overall failed batch for observability.

## Trust boundary

The canonical signal is data, not authorization or executable configuration. Consumers must not import modules, execute code or render untrusted HTML from `message` or `metadata`. Backtesting `Operation` remains a separate domain protocol; cross-domain conversion is intentionally deferred to the architecture item that owns Signal → Decision → Order semantics.
