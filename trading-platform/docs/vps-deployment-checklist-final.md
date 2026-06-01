# Final VPS Deployment Checklist

## Backend Ready

- `GET /health` returns healthy.
- `GET /deployment/readiness` returns a non-blocked status.
- Backend dependencies are installed from `requirements.txt`.
- Logs write to `logs/platform.log`.

## Frontend Ready

- `npm run build` passes inside `frontend`.
- Dashboard loads successfully.
- Frontend API base URL points to the intended backend.

## Docker Ready

- `Dockerfile.backend` exists.
- `Dockerfile.frontend` exists.
- `docker-compose.yml` exists.
- `docker-compose.override.yml` exists.
- `.env.production.example` exists without real secrets.

## Monitoring Ready

- `GET /monitoring/status`
- `GET /monitoring/health`
- `GET /monitoring/metrics`
- `GET /monitoring/apis`
- `GET /monitoring/logs/errors`

## Security Ready

- `GET /security/status`
- `GET /security/secrets-audit`
- `.env.production` remains outside source control.
- Real secrets are not committed.

## Backup Ready

- `GET /backup/status`
- `docs/backup-strategy.md`
- `docs/recovery-runbook.md`
- `docs/deployment-rollback-guide.md`
- `docs/incident-response-guide.md`

## MT5 Ready

- MT5 terminal is installed on the VPS if demo execution testing is planned.
- Demo account login only.
- XAUUSD symbol visibility confirmed.
- Live account execution remains blocked.

## Simulation-Only Confirmed

- `simulation_only=true`
- `demo_execution=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
- no new `mt5.order_send`
