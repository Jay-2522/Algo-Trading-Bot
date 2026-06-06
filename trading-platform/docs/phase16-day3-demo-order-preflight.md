# Phase 16 Day 3 Demo Order Preflight

## Purpose

The demo order preflight layer answers whether a previously built demo dry-run order would be considered safe and structurally valid if future DEMO-only submission were enabled. It does not submit an order.

## Checks Performed

Preflight validates:

- Supported symbol: `EURUSD` or `XAUUSD`
- Supported action: `BUY` or `SELL`
- Lot size greater than `0` and no more than `0.01`
- Stop loss and take profit presence
- Demo authorization has been manually granted
- Risk qualification service is available
- Execution gate service is available and still blocks execution
- MT5 demo market data is available
- Spread is available
- The request references the latest successful dry-run

## Failure Scenarios

Preflight fails if the symbol or action is invalid, the lot exceeds `0.01`, SL/TP is missing, authorization is locked, risk or gate validation is unavailable, market data cannot be read, spread is unavailable, or the latest dry-run did not pass validation.

## Safety Controls

Every response preserves:

- `simulation_only = true`
- `execution_allowed = false`
- `live_execution_enabled = false`
- `broker_execution_enabled = false`

Passing preflight only sets `would_be_allowed_in_demo = true`. It does not create a broker request, send to MT5, or unlock execution.

## Why Execution Remains Disabled

Phase 16 Day 3 is readiness validation only. Actual DEMO order submission still requires a separate DEMO-only execution guard, a fresh manual confirmation, final risk and gate re-checks, and an explicit future phase authorization. Live production trading remains disabled.
