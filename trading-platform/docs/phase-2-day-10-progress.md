# Phase 2 Day 10: Institutional Entry Model Engine

## Purpose

Day 10 translates institutional observations into structured, ranked setup models for simulation assessment. It consumes existing intelligence and never submits, routes, or enables orders.

## Entry Model Types

| Model | Detection Basis |
| --- | --- |
| `SWEEP_FVG_CONTINUATION` | Directional liquidity sweep plus fresh same-direction FVG |
| `ORDER_BLOCK_RETRACEMENT` | Fresh directional order block aligned with confluence |
| `BREAKER_RETEST` | Fresh breaker aligned with confirmed structure transition |
| `MSS_REVERSAL` | MSS with sweep or imbalance confirmation and no HTF opposition |
| `LIQUIDITY_REVERSAL` | Liquidity raid plus fresh order-block reversal zone |
| `NO_TRADE` | Conflict, timing/risk block, or insufficient qualified evidence |

## Zone Geometry

Actionable candidate zones are obtained from fresh FVG, order-block, or breaker boundaries. For a bullish candidate, invalidation is one zone width below its low and the target is two zone widths above its high. Bearish geometry is mirrored. This provides deterministic analysis levels rather than execution instructions.

## Validation Rules

An actionable model must have:

- a directional bias;
- a valid entry-zone range;
- an invalidation level;
- a target level;
- at least two institutional supporting factors;
- no blocked session/news timing;
- no risk block;
- no opposing or conflicted multi-timeframe direction.

Passing models are either `READY_FOR_SIMULATION` or `WAIT_FOR_CONFIRMATION`. Blocked candidates and explicit no-trade outcomes are marked `AVOID` or `NO_SETUP`.

## Scoring Weights

| Evidence Category | Maximum Score |
| --- | ---: |
| Multi-timeframe alignment | 20 |
| Institutional confluence | 25 |
| Session/killzone quality | 15 |
| Structure event quality | 15 |
| Risk readiness | 10 |
| Zone freshness | 15 |
| Total | 100 |

All scoring is bounded and deterministic. Missing geometry reduces score; risk or session blocks prevent simulation readiness.

## Explanation Output

Every model contains a concise dashboard explanation in its metadata, along with supporting factors, blocking factors, warnings, validation rationale, and score breakdown. A no-trade result explains which institutional gates prevented qualification.

## API Routes

- `GET http://127.0.0.1:8000/institutional/entry-models/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/entry-models/best/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/entry-models/ready/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/entry-models/waiting/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/entry-models/avoided/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/entry-models/explanation/XAUUSD`

## Safety Protections

- Analysis-only and simulation-only.
- No broker order placement.
- No autonomous trading activation.
- No live execution flag changes.
- Safe `NO_TRADE` context is returned when MT5 or supporting evidence is unavailable.
- System route auditing and readiness monitoring include the new entry-model module.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day10_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
