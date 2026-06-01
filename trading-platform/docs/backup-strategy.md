# Phase 10 Day 6 Backup Strategy

This strategy defines what must be preserved before deployment, recovery, rollback, or incident response work. It is operational guidance only and does not enable broker execution or live trading.

## Source Code Backup

- Commit and push source code to the approved private repository before deployment changes.
- Record the branch name, commit hash, deployment time, and operator in the release notes.
- Keep a known-good release tag or previous deployment folder for rollback.
- Preserve the verification outputs for `python tests/regression_routes_verification.py` and the active phase verification script.

## Environment Backup

- Keep `.env.production` outside source control.
- Store production environment files in a secure operator vault.
- Save a timestamped checksum for the deployed environment file.
- Never commit API keys, broker passwords, account IDs, tokens, or MT5 credentials.
- Preserve `.env.production.example` as the non-secret restoration template.

## Logs Backup

- Archive `logs/platform.log` and rotated log files before major releases.
- Preserve `/monitoring/logs/errors` and `/monitoring/logs/warnings` output during incidents.
- Keep logs writable by the VPS runtime user after restore.
- Do not delete incident logs until the review is complete.

## MT5 Config Backup

- Document the MT5 demo broker server, demo login, terminal path, and installed data folder location.
- Store MT5 passwords in the operator vault only.
- Preserve symbol visibility notes for XAUUSD and demo account routing.
- Capture screenshots or exported profile notes if terminal profile settings change.
- Confirm `live_execution_enabled=false` and `broker_execution_enabled=false` after any MT5 restoration.

## Deployment Backup

- Snapshot the VPS before major runtime or security changes.
- Preserve previous Docker image tags, release folders, or known-good Git commits.
- Save current outputs for `/deployment/readiness`, `/monitoring/health`, `/security/status`, and `/backup/status`.
- Keep rollback instructions attached to each deployment record.

## Safety

- `simulation_only=true`
- `demo_execution=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

Backup and recovery work must remain read-only from a trading perspective. No order placement is authorized by this runbook.
