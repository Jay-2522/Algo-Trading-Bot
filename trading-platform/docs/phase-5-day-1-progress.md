# Phase 5 Day 1 - MT5 Demo Execution Bridge

## Scope

Phase 5 Day 1 adds the first guarded bridge from execution queue items to MT5 demo execution. This is demo-account execution only and is intentionally restricted to tiny EURUSD market orders.

## Backend

- Added `backend/demo_execution/`.
- Added demo account status, request, and result models.
- Added MT5 demo account verifier.
- Added EURUSD market order builder with max `0.01` lot.
- Added demo execution guard.
- Added guarded demo executor with the only MT5 submission point.
- Added result store and service facade.
- Added `/demo-execution` API routes.

## Safety Rules

- MT5 account must be verified as demo.
- Live execution remains disabled.
- Demo execution must be explicitly confirmed.
- Max lot is `0.01`.
- EURUSD only on Day 1.
- BUY/SELL market orders only.
- Queue must be ready, not paused, and not under emergency stop placeholder.
- Every result is stored for audit.

## Routes

- `GET /demo-execution/status`
- `GET /demo-execution/account-status`
- `GET /demo-execution/results`
- `GET /demo-execution/results/{execution_id}`
- `POST /demo-execution/queue/{queue_id}/execute-demo`

## Verification

Run:

```bash
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
```
