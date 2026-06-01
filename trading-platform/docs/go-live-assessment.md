# Go-Live Assessment

## Deployment Gates

- Production readiness report is non-blocked.
- Route regression passes.
- Active phase verification passes.
- Frontend build passes.
- Backup status score is calculated.
- Security readiness is non-blocked.
- Monitoring health is available.

## Acceptance Criteria

- `GET /production-readiness/report` returns a readiness score.
- `GET /production-readiness/assessment` returns next actions.
- `GET /production-readiness/blockers` lists any deployment blockers.
- `GET /production-readiness/recommendations` returns operator guidance.
- All safety flags remain demo-only and live-disabled.

## Blockers

Any of the following block demo VPS go-live:

- live execution enabled
- broker execution enabled
- unresolved security blockers
- missing backup or recovery documentation
- missing critical route registration
- frontend build failure
- newly introduced `mt5.order_send`

## Post-Deployment Checks

1. Run `scripts/production_readiness_check.ps1`.
2. Run `scripts/vps_healthcheck.ps1`.
3. Run `scripts/backup_status.ps1`.
4. Validate dashboard access.
5. Validate monitoring and security endpoints.
6. Confirm strategy outputs keep `execution_allowed=false`.

## Safety Statement

This assessment supports demo VPS deployment readiness only. It does not approve live trading or broker execution.
