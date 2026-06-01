# Windows VPS Service Guide

## PowerShell Startup

Use:

```powershell
scripts/restart_all.ps1
```

This opens backend and frontend scripts in separate PowerShell windows. It does not kill existing processes.

## Task Scheduler Option

Create two scheduled tasks:

- Backend: run `scripts/restart_backend.ps1` at login.
- Frontend: run `scripts/restart_frontend.ps1` at login.

Set the working directory to the project root.

## NSSM Option

NSSM may be used to wrap the backend and frontend scripts as Windows services. Keep the command paths fixed and keep environment flags set to demo/simulation mode.

## Logs

- Application logs: `logs/platform.log`
- Keep `logs/` writable by the VPS user.

## Healthcheck

```powershell
scripts/vps_healthcheck.ps1
```

## Safety

Live trading and broker execution remain disabled. MT5 should use a demo account only.
