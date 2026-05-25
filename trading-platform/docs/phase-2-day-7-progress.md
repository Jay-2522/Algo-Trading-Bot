# Phase 2 Day 7 Progress

## Institutional Confluence Scoring Engine

Phase 2 Day 7 introduces an analysis-only aggregation layer that ranks institutional market quality from the prior Phase 2 engines. It does not generate orders or activate trading. Its purpose is to supply a transparent dashboard and future simulation research layer with a directional score, quality label, readiness label, and explanation.

## Component Weights

Every response includes ten `ConfluenceComponentScore` records. Weighted scores are deterministic and bounded; the allocations total `100`:

| Component | Weight |
| --- | ---: |
| Structure bias | 15 |
| Liquidity sweep | 15 |
| Fair Value Gap | 15 |
| Order block | 15 |
| Breaker block | 10 |
| BOS / CHOCH / MSS structure shift | 15 |
| Premium / discount zone | 5 |
| Displacement | 5 |
| Session quality | 2.5 |
| Risk readiness | 2.5 |

The requested combined session/risk placeholder budget is represented as two visible `2.5` point components so each dashboard input remains inspectable without exceeding the `100` point total.

## Directional Scoring

- Bullish structure bias contributes bullish quality; bearish bias contributes bearish quality.
- Validated liquidity sweeps contribute in their detected direction.
- Fresh FVGs, order blocks, and breaker blocks carry more weight than mitigated zones.
- MSS is prioritized over BOS, and BOS over CHOCH, when selecting structure-shift evidence.
- Discount positioning supports bullish setups; premium positioning supports bearish setups.
- The most recent valid displacement contributes in its direction.
- High-liquidity sessions and operational risk controls contribute neutral readiness quality.

`bullish_score` and `bearish_score` therefore expose directional evidence separately. `neutral_score` reports supporting conditions that do not decide direction, such as session quality or risk readiness.

## Conflict And Confidence

The engine computes a dominant direction only when one directional evidence set meaningfully prevails. When substantial bullish and bearish evidence are closely balanced, the result is `CONFLICTED`, confidence is reduced, and the setup is classified `NO_TRADE`.

Missing component data never crashes scoring. Missing evidence contributes zero quality and is reported as an explanatory weakness.

## Setup Quality

- `A_PLUS`: score `>= 85`, confidence `>= 80`, and no major directional conflict.
- `A`: score `>= 75`.
- `B`: score `>= 65`.
- `C`: score `>= 55`.
- `LOW_QUALITY`: score `>= 40`.
- `NO_TRADE`: score below `40` or severe directional conflict.

## Trade Readiness

- `READY_FOR_SIMULATION`: `A_PLUS` or `A` assessment.
- `WAIT_FOR_CONFIRMATION`: `B` or `C` assessment.
- `AVOID`: `LOW_QUALITY` assessment.
- `NO_SETUP`: `NO_TRADE` assessment.
- `BLOCKED_BY_RISK`: risk readiness reports a block, regardless of technical quality.

These labels govern analysis and simulated research only. They are not execution permission.

## Explanation Output

The explanation engine generates:

- a one-line assessment summary
- detected strengths, such as aligned bullish structure or fresh zones
- weaknesses, such as missing directional confirmation or mitigated zones
- warnings, including conflict, confirmation requirements, or blocked risk readiness

## Delivered Components

- `confluence_models.py`: component, aggregate score, and full context contracts.
- `confluence_scorer.py`: weighted deterministic directional scoring.
- `setup_quality_classifier.py`: quality and simulation-readiness classification.
- `confluence_explainer.py`: dashboard summary, strengths, weaknesses, and warnings.
- `confluence_context_builder.py`: resilient orchestration of all Phase 2 contexts.
- Updated SMC service, institutional API routes, readiness registry, route audit, regression coverage, and README.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/confluence/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/score/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/explanation/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/components/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/readiness/XAUUSD?timeframe=M15`

## Safety Protections

- Confluence processing consumes candle-derived contexts, session metadata, and risk status only.
- No broker order submission capability is introduced.
- No autonomous trading activation is introduced.
- `simulation_only` remains `true`.
- `live_execution_enabled` remains `false`.
- Component failure returns a typed empty sub-context and continues available scoring.
- MT5 unavailability returns a safe JSON-ready assessment.
- Earlier Phase 1 and Phase 2 routes remain protected.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day7_verification.py
python tests/phase2_day6_verification.py
python tests/phase2_day5_verification.py
python tests/phase2_day4_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

## Next Direction

A subsequent phase can add multi-timeframe confluence alignment and historical calibration of simulation-only ranking outcomes, preserving the current non-executable boundary.
