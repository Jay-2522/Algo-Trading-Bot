# Phase 14 Day 7 - Demo Soak Testing Preparation

## Purpose

Phase 14 Day 7 prepares the platform for multi-hour demo soak testing. The goal is to monitor stability, readiness, and safety locks over time before any demo broker order testing begins.

No trades are placed in this phase.

## Duration Options

- 2 hours: short smoke soak for route stability and repeated health checks.
- 6 hours: session-length soak for monitoring backend stability through normal operation.
- 24 hours: extended soak for restart, memory, logging, and long-running readiness observation.

## What To Monitor

- `/health`
- `/status`
- `/demo-environment/status`
- `/mt5-demo/status`
- `/demo-validation/xauusd/status`
- `/demo-validation/eurusd/status`
- `/demo-validation/nifty50/status`
- `/demo-validation/e2e/status`
- `/demo-validation/soak/readiness`
- `/demo-validation/soak/preflight`
- `/monitoring/status`
- `/security/status`

## Recommended Check Frequency

- Every 5 minutes for health and status endpoints.
- Every 15 minutes for demo-validation status endpoints.
- Every 30 minutes for E2E preview preflight.
- Immediately after backend restart or deployment restart.

## Failure Conditions

The soak test fails if any of the following occur:

- Backend crashes or returns repeated 5xx errors.
- Any validation route becomes unavailable.
- `execution_allowed=true` appears anywhere.
- `live_execution_enabled=true` appears anywhere.
- `broker_execution_enabled=true` appears anywhere.
- `preview_only=false` appears on preview validation routes.
- Fake trades or fake P&L are created.
- A new order placement path is introduced.

## Pass Conditions

The soak test passes if:

- Backend remains available for the selected duration.
- Demo, MT5, validation, E2E, monitoring, and safety endpoints remain available.
- Safety flags remain locked.
- No broker execution occurs.
- No fake P&L or fake trade history is created.
- Logs remain available for review.

## Why No Trades Are Placed

Phase 14 Day 7 is a soak-preparation phase. It validates operational readiness and safety protections only.

Trading remains blocked by design:

- `simulation_only=true`
- `execution_allowed=false`
- `preview_only=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
