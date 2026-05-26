# Phase 2 Day 8: Multi-Timeframe Institutional Alignment Engine

## Purpose

Day 8 converts the existing institutional confluence assessment into a top-down narrative across four trading timeframes. It is a read-only analysis module: it evaluates market evidence and does not place, route, or enable orders.

## Timeframe Hierarchy

| Timeframe | Institutional Role | Alignment Weight |
| --- | --- | ---: |
| H4 | Macro structure authority | 40 |
| H1 | Directional structure confirmation | 30 |
| M15 | Execution structure confirmation | 20 |
| M5 | Precision timing confirmation | 10 |

Each timeframe is evaluated through the Phase 2 Day 7 confluence context, including structure bias, sweeps, imbalances, order blocks, breaker blocks, BOS/CHOCH/MSS events, dealing-range position, displacement, session quality, and risk readiness.

## Alignment Logic

- Four matching bullish or bearish confluence directions produce `FULLY_ALIGNED`.
- Compatible H4 and H1 direction with no opposing lower-timeframe direction produces `STRONGLY_ALIGNED`.
- Supporting but incomplete evidence produces `PARTIALLY_ALIGNED`.
- Neutral or sparse directional evidence produces `MIXED`.
- Material bullish/bearish disagreement, especially H4 versus M15/M5, produces `CONFLICTED`.

The alignment score is deterministic. It sums confidence-weighted agreement using the hierarchy weights and applies an explicit penalty when conflicting evidence exists.

## Bias Resolution

H4 is the top-down authority when it supplies meaningful directional confidence. H1, M15, and M5 strengthen that view when aligned. A strongly confirmed lower-timeframe MSS can flag a temporary reversal against weak H4 evidence; the output remains cautious and exposes the warning for downstream simulation decisions.

## Conflict Detection

The conflict detector reports:

- bullish versus bearish disagreement across timeframes;
- lower-timeframe direction that opposes H4 macro flow;
- neutral H4 evidence with aggressive lower-timeframe conviction;
- opposing H1 and M15 confluence;
- MSS reversal pressure against the prevailing macro direction.

Conflicts lower confidence and are returned directly for dashboard visibility.

## Narrative System

The narrative builder returns macro, directional, execution, and precision stories plus a summary, bullish factors, bearish factors, and warnings. This preserves the chain of institutional reasoning rather than exposing only a numeric rank.

## API Routes

- `GET http://127.0.0.1:8000/institutional/alignment/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/alignment/narrative/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/alignment/conflicts/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/alignment/timeframes/XAUUSD`

## Safety Boundaries

- Analysis-only and simulation-only output.
- No order placement or broker execution path is introduced.
- Existing execution safety boundaries remain unchanged.
- Missing market-terminal data degrades to neutral, JSON-safe alignment output.
- New endpoints are included in system readiness route auditing.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day8_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
