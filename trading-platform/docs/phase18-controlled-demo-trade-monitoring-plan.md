# Phase 18 Controlled Demo Trade Monitoring Plan

## Purpose

Phase 18 monitors the first controlled MT5 demo trade after the guarded Phase 17 runtime sender is explicitly approved and manually triggered. It does not enable live trading, broker execution, automatic strategy orders, or trade copier execution.

## First Demo Trade Monitoring

- Confirm the guarded sender returned a demo-only result with `mt5_order_sent`, `retcode`, `ticket`, `account_login`, `server`, `symbol`, `lot`, `sl`, and `tp`.
- Confirm the account remains DEMO and the MT5 server or trade mode indicates a demo account.
- Confirm only EURUSD and 0.01 lot are used for the first runtime send.
- Confirm no second send attempt is permitted after the single-attempt lock is set.

## MT5 Ticket Verification

- Record the MT5 ticket returned by the guarded sender.
- Check that the ticket is visible in the MT5 demo account history or open positions.
- If MT5 rejects the request, capture the retcode and comment without retrying automatically.

## Journal Recording

- Write an explicit persistent journal record only after a real guarded sender result exists.
- Use `record_order_sent` for accepted MT5 order-send attempts.
- Use `record_order_rejected` for MT5 rejections or safety-gate rejections that should be tracked.
- Do not create synthetic trades, synthetic P&L, or placeholder execution history.

## Lifecycle Tracking

- Track the trade as `SENT`, `OPEN`, and `CLOSED` only when those lifecycle states are observed.
- Record `opened_at`, `closed_at`, `close_price`, `profit_loss`, and `result` only from real demo account observations.
- Keep unknown values empty until verified.

## Dashboard Reflection

- The dashboard reads persistent journal, strategy dashboard, Reports V2, and copier readiness endpoints.
- If no completed demo trades exist, it must show `No completed demo trades yet.`
- Reports must show `Reports will populate after demo trades are recorded.`
- Copier readiness must show `Trade copier is architecture-ready but execution-disabled.`

## Report Generation

- Daily, weekly, monthly, and symbol reports are derived from persistent journal records only.
- Empty reports must contain zero totals and headers for CSV export.
- Report exports must not invent win rate, P&L, or execution history.

## Copier Queue Simulation

- Copier queue simulation can create a master signal, queue items, and batches.
- Queue items remain `SIMULATION_ONLY` or `FUTURE_EXECUTION_REQUIRED`.
- No copier workflow may call MT5, broker APIs, or client account execution.

## Failure Handling

- If MT5 is stale, offline, rejects the order, or returns an unexpected result, record the failure without retrying automatically.
- If journal persistence fails, preserve the MT5 result payload and rerun only the journal write step after fixing storage.
- If dashboard/report sync fails, verify backend endpoints first, then frontend rendering.

## Rollback

- Keep the Phase 17 single-attempt lock intact.
- Do not delete real demo journal records during rollback.
- Disable only newly added dashboard/report/copier foundation routes if they break presentation; do not alter guarded sender safety gates.
- Live trading and broker execution remain disabled throughout rollback.
