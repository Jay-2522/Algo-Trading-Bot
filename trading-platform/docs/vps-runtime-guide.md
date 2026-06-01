# VPS Runtime Guide

## Runtime Modes

- Local runtime mode: start backend and frontend with PowerShell scripts.
- VPS runtime mode: run the same scripts manually, through Task Scheduler, NSSM, or systemd depending on OS.

## Backend

```powershell
scripts/restart_backend.ps1
```

Command:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Frontend

```powershell
scripts/restart_frontend.ps1
```

Command:

```powershell
cd frontend
npm run dev
```

## MT5

- MT5 terminal must be manually installed.
- Login only to a demo account.
- AutoTrading is needed only for guarded demo execution tests.
- Live trading remains disabled by platform policy.

## Safety

- `simulation_only=true`
- `demo_execution=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
- No API endpoint kills or restarts processes.
