# Phase 10 Day 6 Deployment Rollback Guide

Rollback restores the previous known-good platform state when deployment validation fails. This guide does not enable trading execution.

## Rollback Checklist

- Record the current commit hash, branch, operator, and timestamp.
- Save current `/deployment/readiness`, `/monitoring/health`, `/security/status`, and `/backup/status` output.
- Archive `logs/platform.log` and recent error logs.
- Confirm `.env.production` is available in the secure operator vault.
- Identify the previous known-good commit, Docker image, or release folder.

## Previous Release Restore

1. Stop the current backend and frontend processes or containers.
2. Checkout the previous known-good commit or restore the previous release folder.
3. Restore `.env.production` from the secure operator vault.
4. Reinstall dependencies only when the previous release requires it.
5. Restart backend and frontend manually.
6. Keep the current failed release artifacts until incident review is complete.

## Health Validation

- `GET /health`
- `GET /status`
- `GET /deployment/readiness`
- `GET /monitoring/health`
- `GET /security/status`
- `GET /backup/status`
- `python tests/regression_routes_verification.py`
- `python tests/phase10_day6_verification.py`
- `npm run build`

## Safety Validation

- `simulation_only=true`
- `demo_execution=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
- no newly introduced `mt5.order_send`

Live execution must remain disabled after rollback.
