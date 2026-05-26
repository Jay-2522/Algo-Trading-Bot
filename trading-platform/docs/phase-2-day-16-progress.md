# Phase 2 Day 16: AI Institutional Reasoning and Market Narrative Engine

## Purpose

The AI Institutional Reasoning and Market Narrative Engine transforms the complete Phase 2 orchestration report into professional trading-desk commentary for analytical and paper-trading dashboards. It reasons only from recorded orchestration fields and never creates trading authority.

## Narrative Engine

`MarketNarrativeEngine` translates the resolved system state into:

- a desk-style headline,
- market and institutional bias summary,
- recorded key drivers,
- recorded risks,
- a simulation-only recommended action.

Recommended actions are mapped conservatively:

- `READY_FOR_SIMULATION` for approved simulation evaluation,
- `WAIT` for conditional evidence,
- `AVOID` for blocked or safe-mode states,
- `MONITOR` where no qualified setup exists,
- `MANAGE_POSITION` where an active paper position is being managed.

## Reasoning Engine

`InstitutionalReasoningEngine` assembles:

- bullish evidence where bullish observations exist,
- bearish evidence where bearish observations exist,
- neutral or no-trade reasoning from final state,
- invalidation and protection observations,
- session timing observations,
- risk and safety observations.

It does not assert liquidity sweeps, FVGs, order blocks, breakers, structure shifts, alignment, or setup approval unless those facts exist in the orchestration report.

## Client And Dashboard Summaries

`ReasoningSummaryBuilder` produces:

- a concise executive statement,
- a client-facing plain-language summary,
- a compact dashboard line showing symbol, bias, action, and confidence.

All summaries retain simulation-only wording.

## Quality Checker

`ReasoningQualityChecker` validates:

- required narrative and summary sections are present,
- recommended action is consistent with final institutional state,
- safety flags remain simulation-only,
- statements do not claim active live trading or broker-order submission.

## API Routes

- `GET /institutional/reasoning/{symbol}`
- `GET /institutional/reasoning/narrative/{symbol}`
- `GET /institutional/reasoning/summary/{symbol}`
- `GET /institutional/reasoning/dashboard/{symbol}`
- `GET /institutional/reasoning/quality/{symbol}`

Manual checks:

```text
http://127.0.0.1:8000/institutional/reasoning/XAUUSD
http://127.0.0.1:8000/institutional/reasoning/narrative/XAUUSD
http://127.0.0.1:8000/institutional/reasoning/summary/XAUUSD
http://127.0.0.1:8000/institutional/reasoning/dashboard/XAUUSD
http://127.0.0.1:8000/institutional/reasoning/quality/XAUUSD
```

## Safety Boundary

- Output is analysis and paper-simulation commentary only.
- `simulation_only` remains true and `live_execution_enabled` remains false.
- The engine adds no broker connection or order-submission behavior.
- Unavailable data results in conservative safe-mode commentary.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day16_verification.py
python tests/phase2_day15_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
