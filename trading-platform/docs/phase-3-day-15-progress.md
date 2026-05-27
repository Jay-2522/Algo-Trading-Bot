# Phase 3 Day 15 Progress - Multi-Account Routing Foundation

## Purpose

Day 15 adds a simulation-only foundation for previewing how validated signals could route across multiple broker demo accounts.

This is routing preview only. It does not create orders, does not call brokers, and does not enable live execution.

## Default Accounts

Enabled Forex/CFD demo profiles:

- `STARTRADER_DEMO_1`
- `FXPRO_DEMO_1`
- `VANTAGE_DEMO_1`

Future Indian broker placeholders:

- `ZERODHA_PLACEHOLDER`
- `ANGELONE_PLACEHOLDER`
- `UPSTOX_PLACEHOLDER`

Indian placeholders are disabled, not demo-ready, and live execution is disabled.

## Account Groups

- `FOREX_CFD_GROUP`: STARTRADER, FXPRO, Vantage demo profiles
- `INDIAN_BROKER_GROUP`: Zerodha, AngelOne, Upstox placeholders

## Routing Policy

Default policy:

- `routing_mode = COPY_TO_ALL`
- `require_demo_ready = true`
- `require_read_only_verified = true`
- `max_accounts_per_signal = 3`
- `live_execution_enabled = false`

## Routing Behavior

- `EURUSD` routes to all three Forex/CFD demo account profiles.
- `XAUUSD` routes to all three Forex/CFD demo account profiles.
- `NIFTY50` stays not routing-ready until Indian broker integration is implemented.

## Routes

- `GET /accounts/status`
- `GET /accounts`
- `GET /accounts/{account_id}`
- `GET /accounts/groups`
- `GET /accounts/policy/default`
- `POST /accounts/route-preview`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day15_verification.py
```
