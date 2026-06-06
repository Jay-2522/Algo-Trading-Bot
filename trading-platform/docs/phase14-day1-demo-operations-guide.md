# Phase 14 Day 1 Demo Operations Guide

This guide defines how demo testing will operate. It does not authorize live trading or broker execution.

## 1. MT5 Demo Setup

- Install MT5 on the Windows VPS.
- Create or obtain a demo account only.
- Verify login manually in MT5.
- Confirm demo market data is visible.
- Do not configure live account credentials.
- Do not store broker credentials in the repository.

## 2. Backend Startup

- Confirm Python dependencies are installed.
- Start backend using the approved script:

```powershell
scripts/start_backend.ps1
```

- Verify:

```text
GET /health
GET /status
GET /demo-environment/status
GET /monitoring/status
```

## 3. Dashboard Startup

- Confirm Node dependencies are installed.
- Start frontend using:

```powershell
scripts/start_frontend.ps1
```

- Verify dashboard pages:

```text
/dashboard
/dashboard/developer
```

## 4. Monitoring Startup

- Confirm logs are writing.
- Confirm health endpoint is active.
- Confirm monitoring endpoints are available.
- Confirm alerting channel is planned before any demo execution test.

## 5. Daily Validation Process

Before any demo-session review:

- Run backend health checks.
- Run monitoring checks.
- Run security checks.
- Confirm `simulation_only=true`.
- Confirm `live_execution_enabled=false`.
- Confirm `broker_execution_enabled=false`.
- Confirm `/demo-environment/readiness` still reports safe blockers until demo approval gates are complete.

## 6. Trade Review Process

Demo trade review must use recorded demo execution records only.

Review:

- Strategy signal
- News and macro context
- Risk decision
- Demo approval decision
- Execution confirmation record
- Trade journal record
- Dashboard analytics

No real-money trade review is in scope.

## 7. Shutdown Procedure

- Stop frontend.
- Stop backend.
- Confirm no processes are stuck.
- Archive logs for the day.
- Record readiness findings.
- Keep MT5 demo terminal closed if not actively validating.

## Safety Locks

Required state:

- `simulation_only=true`
- `execution_allowed=false` until explicit demo approval workflow is completed
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

Phase 14 Day 1 is planning and readiness only.
