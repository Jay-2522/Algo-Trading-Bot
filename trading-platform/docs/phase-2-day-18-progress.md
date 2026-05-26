# Phase 2 Day 18: Unified Institutional Dashboard Context Engine

## Purpose

The Unified Institutional Dashboard Context Engine turns existing Phase 2 analytical reports into stable backend sections for a future dashboard. It summarizes evidence already produced by orchestration, AI reasoning, and performance analytics; it does not add a presentation UI or any execution capability.

## Card Schema

Each `DashboardCard` provides a title, state, display value, subtitle, severity, typed source data, and warnings. The consolidated response includes:

- Market overview and institutional bias
- Confluence score and multi-timeframe alignment
- Session and killzone intelligence
- Entry model and setup validation state
- Simulation decision and paper-trade lifecycle
- Position management and performance analytics
- AI reasoning narrative
- Warnings/risk and final recommendation cards

Cards are JSON-safe summaries of existing institutional contexts. Missing evidence produces inactive or warning cards instead of failures.

## Alerts

`DashboardAlertBuilder` raises client-facing notices for simulation safety status, blocked readiness, failed pipeline steps, directional conflicts, and insufficient analytics history. Alerts communicate operational or quality constraints; they never authorize execution.

## Recommendation Logic

`DashboardSummaryBuilder` resolves a final dashboard action from the institutional system state:

- `BLOCKED` becomes `AVOID`.
- `WAITING_FOR_CONFIRMATION` becomes `WAIT`.
- `READY_FOR_SIMULATION` becomes `READY_FOR_SIMULATION`.
- `MANAGING_POSITION` becomes `MANAGE_POSITION`.
- Missing setups become `MONITOR`.
- Pipeline or safety inconsistencies become `REVIEW_SYSTEM`.

Only the simulation-ready state can set `simulation_allowed` to true, and that permission remains paper/simulation scope only.

## Dashboard Status

`DashboardStatusResolver` returns `CRITICAL` for safety inconsistencies or error-safe mode, `BLOCKED` for institutional blocks, `WAITING` for confirmation states, `ACTIVE` for managed paper positions, and `HEALTHY` when safe analytical operation is preserved. Multiple elevated card warnings produce a dashboard warning state.

## API Routes

- `GET /institutional/dashboard/{symbol}`
- `GET /institutional/dashboard/cards/{symbol}`
- `GET /institutional/dashboard/alerts/{symbol}`
- `GET /institutional/dashboard/recommendation/{symbol}`
- `GET /institutional/dashboard/status/{symbol}`

Manual checks:

```text
http://127.0.0.1:8000/institutional/dashboard/XAUUSD
http://127.0.0.1:8000/institutional/dashboard/cards/XAUUSD
http://127.0.0.1:8000/institutional/dashboard/alerts/XAUUSD
http://127.0.0.1:8000/institutional/dashboard/recommendation/XAUUSD
http://127.0.0.1:8000/institutional/dashboard/status/XAUUSD
```

## Safety Boundary

- This is a backend dashboard context layer only.
- Every context retains `simulation_only = true` and `live_execution_enabled = false`.
- No broker order or MT5 trade submission path is introduced.
- Unavailable data and failed analytical steps return restrained fallback output.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day18_verification.py
python tests/phase2_day17_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
