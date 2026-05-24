# Day 4 Progress

## Objective

Build an analysis-only Risk Management Engine that defines future trading permission controls without creating, sending, or executing orders.

## Risk Engine Overview

Day 4 introduces centralized risk limits, position-size calculation, guardrails for adverse conditions, an in-memory emergency kill switch, trade-permission evaluation, and read-only monitoring APIs.

## Files Created

- `backend/risk_engine/risk_models.py`
- `backend/risk_engine/risk_config.py`
- `backend/risk_engine/position_sizer.py`
- `backend/risk_engine/drawdown_guard.py`
- `backend/risk_engine/loss_guard.py`
- `backend/risk_engine/spread_guard.py`
- `backend/risk_engine/kill_switch.py`
- `backend/risk_engine/risk_service.py`
- `backend/risk_engine/validators.py`
- `backend/api/risk_routes.py`
- `tests/day4_verification.py`
- `docs/day-4-progress.md`

## Risk Rules

- Maximum risk per trade calculation: `1.0%`.
- Maximum daily drawdown: `3.0%`.
- Maximum consecutive losses: `3`.
- Maximum allowed spread: `30`.
- Maximum expected slippage: `10`.
- Trading permission can be manually blocked by the emergency kill switch.

The position-sizing endpoint calculates exposure only. It does not represent an order request or approval to execute.

## API Endpoints

- `GET /risk/status`
- `GET /risk/config`
- `POST /risk/calculate-position-size`
- `POST /risk/check-trade`
- `POST /risk/kill-switch/activate`
- `POST /risk/kill-switch/deactivate`

## Verification

Run:

```powershell
python tests/day4_verification.py
```

The script verifies the risk modules, router registration, guard behavior, sizing calculation, kill switch lifecycle, and service status. It does not require MT5.

## Pending Day 5 Work

- Persist kill-switch status and risk events in the database.
- Add audit logging for risk permission evaluations.
- Add mocked API tests for risk scenarios.
- Define the execution-engine contract that must consult risk before any future broker request.
- Add account/equity ingestion for real drawdown monitoring without enabling execution.

