# Phase 2 Day 15: Institutional Orchestration Engine

## Purpose

The Institutional Orchestration Engine coordinates all Phase 2 intelligence and paper-management modules into one report and one resolved institutional system state. It remains an analysis and simulation-orchestration layer only.

## Pipeline Order

The runner executes fourteen ordered stages:

1. Institutional market context.
2. Liquidity sweep context.
3. Fair Value Gap context.
4. Order block context.
5. Breaker block context.
6. BOS, CHOCH, and MSS structure-shift context.
7. Institutional confluence context.
8. Multi-timeframe alignment.
9. Session and killzone intelligence.
10. Institutional entry models.
11. Setup validation.
12. Simulation decision.
13. Paper trade lifecycle.
14. Position management.

Each step records status, completion duration, summary, and any safe error. A failed stage does not terminate report construction; the system returns partial context and enters safe mode.

## Final State Resolution

The resolver emits one of:

- `MANAGING_POSITION` when active paper positions are under management.
- `READY_FOR_SIMULATION` after an approved simulation decision.
- `WAITING_FOR_CONFIRMATION` for conditional or waiting validated setups.
- `BLOCKED` for timing, risk, emergency, or exit restrictions.
- `NO_TRADE` when no qualified setup exists.
- `ERROR_SAFE_MODE` when a pipeline stage fails.

The system state also reports market state, institutional bias, setup state, simulation state, position state, risk state, and confidence.

## Report And Health

The report contains every available Phase 2 context, pipeline telemetry, final state, executive summary, strengths, weaknesses, and warnings.

The health checker confirms:

- fourteen-step module availability,
- failed-stage visibility,
- JSON-safe report serialization,
- `simulation_only = true`,
- `live_execution_enabled = false`.

## API Routes

- `GET /institutional/orchestration/{symbol}`
- `GET /institutional/orchestration/state/{symbol}`
- `GET /institutional/orchestration/report/{symbol}`
- `GET /institutional/orchestration/summary/{symbol}`
- `GET /institutional/orchestration/health/{symbol}`

Manual checks:

```text
http://127.0.0.1:8000/institutional/orchestration/XAUUSD
http://127.0.0.1:8000/institutional/orchestration/state/XAUUSD
http://127.0.0.1:8000/institutional/orchestration/report/XAUUSD
http://127.0.0.1:8000/institutional/orchestration/summary/XAUUSD
http://127.0.0.1:8000/institutional/orchestration/health/XAUUSD
```

## Safety Boundary

- The engine creates reports and paper-management state only.
- It adds no broker API call and no MT5 order submission path.
- All final outputs state that live execution is disabled.
- Missing data or failed steps produce safe non-executable outcomes.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day15_verification.py
python tests/phase2_day14_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
