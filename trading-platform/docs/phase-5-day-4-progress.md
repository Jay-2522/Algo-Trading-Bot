# Phase 5 Day 4 - Demo Trade Copier Coordination

## Added

- `backend/trade_copier` package for demo-only trade copy coordination.
- `TradeCopyBatch`, `AccountCopyStatus`, and `CopySynchronizationSummary` models.
- Copy batch builder that uses Day 3 multi-account planning and preserves signal, symbol, action, and target account data.
- Duplicate guard keyed by `signal_id`, `account_id`, `symbol`, and `action`.
- Synchronization engine that classifies completed, partial, blocked, rejected, unavailable, and failed-safe copy states.
- In-memory copy status tracker for auditable dashboard/API visibility.
- `/trade-copier` API routes for status, preview, batch creation, lookup, listing, and synchronization.
- Preview responses remain non-terminal: batch status is `READY` and account statuses are `PLANNED`.

## Safety

- Demo coordination only.
- `simulation_only=true`, `demo_execution=true`, `live_execution_enabled=false`, and `broker_execution_enabled=false`.
- EURUSD only.
- XAUUSD and NIFTY50 are blocked.
- Per-account lot remains capped by the Day 3 planner at `0.01`.
- Duplicate copy attempts are blocked per signal/account/symbol/action when batches are created.
- No trade copier module places orders directly. MT5 submission remains isolated to the guarded demo executor.

## Verification

Run:

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
python tests/phase5_day4_verification.py
```
