# Phase 4 Day 6 - Manual Override & Safety Control Panel

## Scope

Phase 4 Day 6 adds a simulation-only control center for the VPS dashboard. The operator can pause and resume simulated queue processing, cancel queued simulation items, acknowledge alerts, inspect safety lock state, and record an emergency stop placeholder for future execution phases.

## Backend

- Added `backend/control_center/` with safety state, manual override actions, and audit event models.
- Added an in-memory safety lock manager for queue pause/resume and emergency-stop placeholder state.
- Added an audit store so operator actions are visible to the dashboard.
- Added `/control-center` API routes for status, safety state, audit events, queue pause/resume, queue cancellation, alert acknowledgement, and emergency-stop placeholder.

## Frontend

- Added `ManualControlPanel`, `SafetyLockPanel`, `ControlAuditPanel`, and `ConfirmActionModal`.
- Dashboard polling now includes control-center status, safety state, and control audit events.
- Manual control buttons require confirmation and clearly label all actions as simulation-only.

## Safety

- `simulation_only` remains `true`.
- `live_execution_enabled` remains `false`.
- `broker_execution_enabled` remains `false`.
- Emergency stop is a placeholder only and does not control live broker execution.
- No broker order placement or `mt5.order_send` is introduced.

## Verification

Run:

```bash
python tests/regression_routes_verification.py
python tests/phase4_day6_verification.py
cd frontend
npm run build
```
