# Phase 10 Day 6 Recovery Runbook

This runbook describes recovery actions for operators. It is read-only guidance for platform resilience and does not authorize live execution.

## Backend Failure Recovery

1. Run `scripts/runtime_status.ps1`.
2. Review `logs/platform.log` and `/monitoring/logs/errors`.
3. Confirm `.env.production` exists on the VPS and was restored from the secure vault if needed.
4. Restart the backend with `scripts/restart_backend.ps1`.
5. Verify `GET /health`, `GET /deployment/readiness`, `GET /monitoring/health`, and `GET /backup/status`.
6. Confirm `execution_allowed=false` in strategy outputs.

## Frontend Failure Recovery

1. Run `npm run build` inside `frontend`.
2. Restart frontend with `scripts/restart_frontend.ps1`.
3. Open the dashboard in a browser.
4. Confirm API connectivity to `/health`, `/monitoring/status`, and `/deployment/status`.
5. Check the browser console for runtime errors.

## MT5 Recovery

1. Capture platform logs before changing MT5 state.
2. Restart MT5 manually.
3. Confirm the terminal is logged into a demo account only.
4. Confirm XAUUSD symbol visibility and demo routing notes.
5. Check `GET /monitoring/mt5` and `GET /mt5/status`.
6. Keep live trading and broker execution disabled.

## VPS Recovery

1. Archive current logs before rebooting.
2. Confirm no deployment, backup, or restore script is mid-run.
3. Reboot only when process state is captured.
4. Start backend and frontend manually.
5. Run `scripts/vps_healthcheck.ps1`, `scripts/recovery_check.ps1`, and `scripts/backup_status.ps1`.
6. Verify monitoring and security endpoints after services return.

## Full Recovery Validation

- `GET /health`
- `GET /status`
- `GET /deployment/readiness`
- `GET /monitoring/health`
- `GET /security/status`
- `GET /backup/status`
- `python tests/regression_routes_verification.py`
- `python tests/phase10_day6_verification.py`

## Safety

Do not enable live trading, broker execution, or autonomous order placement during recovery.
