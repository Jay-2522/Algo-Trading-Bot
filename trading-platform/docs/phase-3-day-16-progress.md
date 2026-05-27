# Phase 3 Day 16 Progress - Account Allocation & Risk Distribution

## Purpose

Day 16 completes account-level allocation preview for multi-broker preparation.

This is allocation preview only. It does not create orders, call broker execution APIs, or enable live trading.

## Components

- `allocation_models.py` defines account risk profiles, balance snapshots, lot allocations, and allocation decisions.
- `account_risk_profile.py` maintains simulated account risk profiles.
- `account_balance_snapshot.py` provides JSON-safe simulated balances.
- `symbol_risk_rules.py` defines symbol-level risk limits.
- `broker_lot_constraints.py` enforces min/max/step lot constraints.
- `exposure_validation_engine.py` validates account and symbol exposure.
- `lot_allocation_engine.py` calculates account-level lots.
- `risk_distribution_engine.py` summarizes portfolio risk.
- `allocation_decision_builder.py` builds complete allocation previews.
- `allocation_monitoring_service.py` exposes allocation monitoring and preview methods.

## Symbol Rules

- `EURUSD`: max total lot `3.0`, max risk `1.0%`
- `XAUUSD`: max total lot `1.0`, max risk `0.75%`
- `NIFTY50`: blocked until Indian broker integration is implemented

## Expected Behavior

- `EURUSD` allocates across STARTRADER, FXPRO, and Vantage demo profiles.
- `XAUUSD` allocates across STARTRADER, FXPRO, and Vantage with lower risk.
- `NIFTY50` is rejected safely because Indian broker accounts are placeholders.

## Routes

- `GET /accounts/allocation/status`
- `GET /accounts/risk-profiles`
- `GET /accounts/balance-snapshots`
- `GET /accounts/symbol-rules/{symbol}`
- `POST /accounts/allocation/preview`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day15_verification.py
python tests/phase3_day16_verification.py
```
