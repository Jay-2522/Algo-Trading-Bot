# Docker Deployment Guide

## Scope

This Docker setup packages the backend and frontend for VPS demo deployment preparation. It does not enable live trading or broker live execution.

## Files

- `Dockerfile.backend`
- `Dockerfile.frontend`
- `docker-compose.yml`
- `docker-compose.override.yml`
- `.dockerignore`
- `.env.example`
- `.env.production.example`

## Safety Defaults

Keep these values pinned:

```env
SIMULATION_ONLY=true
DEMO_EXECUTION=true
LIVE_EXECUTION_ENABLED=false
BROKER_EXECUTION_ENABLED=false
```

`LIVE_EXECUTION_ENABLED` must remain false unless manually approved in a future production-go-live phase.

## Build

```powershell
scripts/docker_build.ps1
```

Equivalent:

```powershell
docker compose build
```

## Start

```powershell
scripts/docker_up.ps1
```

Backend:

- `http://127.0.0.1:8000`
- Health: `GET /health`

Frontend:

- `http://127.0.0.1:3000`

## Logs

```powershell
scripts/docker_logs.ps1
```

## Health Check

```powershell
scripts/docker_healthcheck.ps1
```

Checks:

- `/health`
- `/deployment/status`
- `/strategy-execution-bridge/operations/status`

## Stop

```powershell
scripts/docker_down.ps1
```

## VPS Notes

- Recommended region: Mumbai.
- Preferred providers: Vultr Mumbai, AWS Mumbai, Contabo.
- Mount `./logs:/app/logs`.
- Use `.env.production` created from `.env.production.example`.
- Keep MT5 demo-only policy active.
- Do not add any new MT5 order path.
