# Phase 2 Day 12: Institutional Simulation Decision Pipeline

## Purpose

Day 12 converts validated institutional setup approval into a final simulation-only decision and analytical intent. It never constructs or submits a broker request.

## Decision Pipeline

1. Consume the Day 11 setup-validation context.
2. Select the highest-scoring approved setup, otherwise the strongest conditional setup.
3. Re-check global risk, news blackout, and session restriction status.
4. Build an analytical `BUY`, `SELL`, or `NONE` simulation intent.
5. Estimate reward-to-risk from the approved analytical levels.
6. Emit final action, readiness, quality, and reasoning.

## Simulation Intent Structure

`SimulationOrderIntent` includes:

- symbol and timeframe;
- analytical `BUY`, `SELL`, or `NONE` direction;
- entry zone, invalidation level, and target level;
- estimated reward-to-risk and risk quality;
- source setup-validation and entry-model identifiers;
- an explicit `simulation_only = true` marker.

Blocked decisions retain source identifiers for auditing but clear actionable levels and direction to `NONE`.

## Reward-To-Risk Logic

RR is calculated from the midpoint of the candidate entry zone:

| Estimated RR | Risk Quality |
| ---: | --- |
| `>= 3.0` | `EXCELLENT` |
| `>= 2.0` | `GOOD` |
| `>= 1.5` | `ACCEPTABLE` |
| `< 1.5` | `POOR` |
| Invalid geometry | `INVALID` |

Division-by-zero and directionally invalid geometry return `INVALID` without raising an error.

## Final Actions

- `SIMULATE_BUY`: approved bullish setup with acceptable risk geometry.
- `SIMULATE_SELL`: approved bearish setup with acceptable risk geometry.
- `WAIT`: strongest setup is conditional and needs confirmation.
- `AVOID`: safety, risk, news, session, or critical rejection prevents simulation.
- `NO_TRADE`: no valid institutional setup is available.

All decisions set `live_execution_enabled = false` and remain simulation-only.

## API Routes

- `GET http://127.0.0.1:8000/institutional/simulation-decision/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/simulation-decision/action/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/simulation-decision/intent/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/simulation-decision/explanation/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/simulation-decision/readiness/XAUUSD`

## Safety Boundaries

- Analysis plus simulation intent only.
- No broker execution path is introduced.
- No live trading activation is introduced.
- Rejected and unavailable-data paths return `NONE` intent.
- System readiness and route auditing include the new pipeline.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day12_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
