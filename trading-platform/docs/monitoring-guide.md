# Monitoring Guide

## Scope

The monitoring layer provides read-only observability for deployment, system health, API health, MT5 demo readiness, process status, and logs. It does not start, stop, or execute trades.

## Logs

- Main log file: `logs/platform.log`
- Rotation: 10 MB
- Backups: 5
- Output: console and file

## Endpoints

- `GET /monitoring/status`
- `GET /monitoring/health`
- `GET /monitoring/metrics`
- `GET /monitoring/processes`
- `GET /monitoring/apis`
- `GET /monitoring/mt5`
- `GET /monitoring/logs`
- `GET /monitoring/logs/errors`
- `GET /monitoring/logs/warnings`

## Safety

- Monitoring is read-only.
- Simulation mode remains enabled.
- Demo execution remains guarded.
- Live execution remains disabled.
- Broker execution remains disabled.
- No MT5 order path is added.
