# Phase 10 Day 6 Incident Response Guide

This guide defines first-response actions for operational incidents. It is intended to preserve service safety, collect evidence, and restore analysis-only operation.

## API Outage

1. Check `GET /health` and `GET /status`.
2. Review `logs/platform.log` and `/monitoring/logs/errors`.
3. Confirm backend runtime status with `scripts/runtime_status.ps1`.
4. Restart backend only after logs are captured.
5. Validate `/deployment/readiness`, `/monitoring/health`, `/security/status`, and `/backup/status`.

## MT5 Unavailable

1. Capture current platform and MT5 notes before restarting anything.
2. Restart MT5 manually.
3. Confirm demo account login only.
4. Verify XAUUSD symbol visibility.
5. Check `/monitoring/mt5` and `/mt5/status`.
6. Keep broker execution disabled.

## Deployment Failure

1. Stop the rollout.
2. Archive logs and deployment command output.
3. Run `/backup/status` and `/deployment/readiness`.
4. Roll back using `docs/deployment-rollback-guide.md`.
5. Re-run regression and active phase verification before resuming deployment work.

## High Error Rate

1. Review `/monitoring/logs/errors`, `/monitoring/metrics`, and backend logs.
2. Pause further deployment changes.
3. Identify the failing route, service, or dependency.
4. Roll back if the error rate is tied to the current release.
5. Preserve logs for root cause analysis.

## Security Incident

1. Preserve logs and active process state.
2. Rotate affected secrets outside the repository.
3. Confirm `.env.production` remains outside source control.
4. Run `/security/status` and `/security/secrets-audit`.
5. Keep live execution and broker execution disabled.

## Safety Baseline

- `simulation_only=true`
- `demo_execution=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
- no autonomous trading
- no order placement
