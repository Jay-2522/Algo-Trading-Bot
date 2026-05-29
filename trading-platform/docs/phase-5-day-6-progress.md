# Phase 5 Day 6 - Execution Risk Enforcement

## Added

- `backend/execution_risk` package for execution-time demo risk enforcement.
- Default risk policy allowing EURUSD only, blocking XAUUSD/NIFTY50, capping per-account lot at `0.01`, limiting target accounts to three, and keeping live/broker execution disabled.
- Risk evaluator for single-account, multi-account, and trade-copy requests.
- In-memory risk decision and audit event store.
- `/execution-risk` API routes for status, policy, evaluation, decisions, and audit events.

## Integrated

- `MT5DemoExecutionGuard` calls the risk evaluator before allowing guarded demo execution.
- `MultiAccountExecutionGuard` calls the risk evaluator before allowing per-account demo routing.
- `TradeCopierService` calls the risk evaluator before copy batch creation proceeds.

## Safety

- Demo execution only.
- `simulation_only=true`, `demo_execution=true`, `live_execution_enabled=false`, and `broker_execution_enabled=false`.
- No new order placement path.
- `mt5.order_send` remains isolated to the guarded demo executor.
