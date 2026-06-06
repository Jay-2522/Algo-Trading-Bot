# Phase 16 Day 6 Demo Order Test Plan

## Goal Of The First Demo Trade

The first future demo trade should prove that a single, tightly controlled DEMO-only order can move through the full safety pipeline without enabling live trading or broker production execution. The recommended future test is one `EURUSD` order with max lot `0.01`.

## Required Approvals

- Operator confirms the environment is DEMO.
- Operator confirms max lot size is `0.01`.
- Operator confirms manual confirmation is present.
- Operator confirms live trading is disabled.
- Operator confirms broker execution is disabled until a future guarded execution phase.

## Test Sequence

1. Confirm MT5 and demo account connectivity.
2. Confirm EURUSD and XAUUSD are available.
3. Confirm market data and historical data are available.
4. Confirm strategy feed and strategy consumption are available.
5. Confirm risk qualification and execution gate validation.
6. Grant explicit demo authorization.
7. Complete dry-run builder.
8. Pass preflight validation.
9. Pass execution simulator.
10. Run readiness audit.
11. Require final manual operator confirmation before any future guarded sender is considered.

## Failure Response

If MT5 disconnects, market data is unavailable, spread is invalid, risk is invalid, authorization is revoked, execution gate blocks, or strategy is unavailable:

- stop trade
- do not execute
- notify operator

## Rollback Procedure

1. Disable authorization.
2. Disable demo testing.
3. Clear pending request.
4. Reset execution gate.
5. Return system to simulation mode.

## Safety Restrictions

The test plan keeps:

- `execution_allowed = false`
- `simulation_only = true`
- `live_execution_enabled = false`
- `broker_execution_enabled = false`

## Why Execution Remains Disabled

Phase 16 Day 6 is planning only. It creates the official controlled demo-trade checklist and response plan, but it does not place demo orders, call `mt5.order_send`, enable live trading, or enable broker execution.
