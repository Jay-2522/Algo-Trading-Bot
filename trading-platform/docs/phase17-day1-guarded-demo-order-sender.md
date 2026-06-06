# Phase 17 Day 1 Guarded Demo Order Sender

## What Was Created

Phase 17 Day 1 adds a guarded single-demo-order sender boundary for a future MT5 DEMO order attempt. It validates the Phase 16 approval workflow, final approval, dry-run, preflight, simulator, readiness audit, account state, symbol, lot, SL/TP, and required acknowledgements before preparing an MT5-style request.

## Why The Sender Is Guarded

The sender is limited to one future DEMO order attempt, max lot `0.01`, and allowed symbols `EURUSD` or `XAUUSD`. It rejects missing manual confirmation, missing acknowledgements, live execution requests, production broker execution requests, and unapproved workflow state.

## Prepare vs Send

- `prepare` validates the payload and returns a request preview only.
- `send` also validates the payload, but without `execute_single_demo_order_now = true` it returns `PREPARED_BUT_NOT_SENT`.

Phase 17 Day 1 does not add a new unrestricted MT5 submission path.

## Required Manual Confirmations

- `manual_confirmation = true`
- `acknowledge_demo_only = true`
- `acknowledge_no_live_trading = true`
- `acknowledge_single_trade_only = true`

## Single-Trade Limit

Only one future demo send attempt is allowed by the guard. Once a guarded send attempt is recorded, later send attempts are blocked.

## Max Lot

The max lot is fixed at `0.01`.

## No Live Trading

Live trading and production broker execution remain disabled. Any request attempting to enable them is rejected.

## Verify Without Sending

Run:

```powershell
python tests\phase17_day1_guarded_demo_order_sender_verification.py
```

The verification script exercises status, prepare, send without final flag, invalid payloads, single-trade guard presence, and no-new-order-send scanning. It does not place a demo order.
