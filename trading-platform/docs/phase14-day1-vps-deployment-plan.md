# Phase 14 Day 1 VPS Deployment Plan

Phase 14 starts demo trading and VPS validation planning. This plan does not enable live trading, broker execution, or production broker credentials.

## Recommended Architecture

```text
Windows VPS
  |
  +-- MT5 terminal with demo account only
  +-- Backend API
  +-- Frontend dashboard
  +-- Monitoring, logs, and health checks
```

## Minimum VPS Specs

- Windows Server 2019 or newer
- 2 vCPU
- 4 GB RAM
- 60 GB SSD
- Stable network connection
- Administrator access
- Region near broker execution infrastructure where possible

## Recommended VPS Specs

- Windows Server 2022
- 4 vCPU
- 8 GB RAM
- 100 GB SSD
- Automatic restart support
- Daily snapshot or backup support
- Low-latency location for MT5 demo validation

## Expected Monthly Cost

Estimated range: USD 25 to USD 80 per month depending on provider, region, CPU, RAM, and backup retention.

## Required Components

- MT5 installed
- MT5 demo account created
- Backend Python runtime installed
- Node.js runtime installed
- Repository deployed
- `.env` created from safe templates
- Logs directory available
- Health-check scripts available
- Recovery scripts available

## Recovery Strategy

- Keep repository and environment templates backed up.
- Keep MT5 demo login details outside source control.
- Preserve logs for daily validation.
- Use VPS snapshot before major deployment changes.
- Keep rollback guide available on the VPS.

## Restart Strategy

- Backend restart script: `scripts/restart_backend.ps1`
- Frontend restart script: `scripts/restart_frontend.ps1`
- Full restart script: `scripts/restart_all.ps1`
- Runtime status script: `scripts/runtime_status.ps1`
- Health check script: `scripts/vps_healthcheck.ps1`

## Readiness Gates

Demo execution cannot be authorized until:

- MT5 demo account is configured.
- MT5 demo connection is verified.
- VPS is reachable.
- Monitoring is active.
- Logs are active.
- Alerting path is ready.
- Risk engine is enabled.
- News engine is enabled.
- Live execution remains disabled.
- Broker execution remains disabled.

## Safety Position

- `simulation_only=true`
- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

Phase 14 Day 1 is planning and readiness only.
