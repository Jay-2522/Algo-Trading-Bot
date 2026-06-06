# Phase 16 Day 2 Demo Order Dry-Run Builder

## What Dry-Run Means

A demo order dry-run builds and validates an order preview without submitting anything to MT5. It answers what a demo order request would look like after symbol, action, lot, SL/TP, authorization, risk traceability, and execution gate checks.

## Why No Order Is Sent

Phase 16 Day 2 is still preview-only. The system is preparing the structure needed for future DEMO-only order testing, but the execution lock remains active:

- `simulation_only = true`
- `live_execution_enabled = false`
- `broker_execution_enabled = false`
- `execution_allowed = false`
- `would_send_to_mt5 = false`
- `mt5_order_sent = false`

## Max Lot Rule

The maximum allowed demo dry-run lot is `0.01`. Any lot above `0.01` is rejected. Lots less than or equal to zero are rejected.

## Required Fields

Dry-run requests must include:

- `symbol`, limited to `EURUSD` or `XAUUSD`
- `action`, limited to `BUY` or `SELL`
- `lot`, greater than `0` and no larger than `0.01`
- `entry_price`
- `stop_loss`
- `take_profit`
- `risk_decision_id`
- `gate_decision_id`
- `manual_confirmation = true`

## Safety Restrictions

Dry-runs are rejected when demo authorization is locked, the execution gate is not ready, live execution is requested, broker execution is requested, or required risk and gate traceability fields are missing. Passing validation only creates an order payload preview; it never allows execution.

## Before Real Demo Order Testing

Before controlled DEMO order testing can be considered, the system must add a separate DEMO-only sender guard, require fresh manual confirmation, re-check risk qualification and execution gate state at request time, enforce max lot at the final boundary, and keep live production execution explicitly disabled.
