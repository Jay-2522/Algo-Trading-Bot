# Phase 2 Day 17: Institutional Performance Analytics and Optimization Engine

## Purpose

The Institutional Performance Analytics and Optimization Engine measures simulation-only institutional decisions and paper outcomes over recorded analytical history. It produces research recommendations only; it does not alter thresholds automatically or authorize execution.

## Metrics

Setup metrics track validation totals, approval and rejection rates, average setup score, strongest and weakest setup types, and recurring rejection reasons.

Decision metrics track simulation action distribution, block rate, confidence, common final action, and recurring block reasons.

Paper-trade metrics track deduplicated candidate and position records, closed wins/losses/breakeven results, win rate, average realized R, average simulated points, and best/worst R results.

Position-management metrics track partial take profits, break-even moves, trailing adjustments, structural exits, emergency exits, management-decision confidence, and common exit reasons.

## Optimization Recommendations

The engine identifies recurring analytical themes including session timing restrictions, confluence conflicts, risk geometry issues, high setup rejection, inactive paper candidates, weak closed outcomes, and emergency exits.

Recommendations are evidence-led review suggestions. They never modify strategy configuration or activate trading.

## Insufficient Data Behavior

The context builder accepts collections of historical orchestration contexts. Fewer than three samples, or no measured observations, produce `INSUFFICIENT_DATA` with safe data-collection guidance. The API reports the current available snapshot conservatively and does not claim longitudinal confidence without historical observations.

## API Routes

- `GET /institutional/performance/{symbol}`
- `GET /institutional/performance/setups/{symbol}`
- `GET /institutional/performance/decisions/{symbol}`
- `GET /institutional/performance/paper-trades/{symbol}`
- `GET /institutional/performance/position-management/{symbol}`
- `GET /institutional/performance/recommendations/{symbol}`

Manual checks:

```text
http://127.0.0.1:8000/institutional/performance/XAUUSD
http://127.0.0.1:8000/institutional/performance/setups/XAUUSD
http://127.0.0.1:8000/institutional/performance/decisions/XAUUSD
http://127.0.0.1:8000/institutional/performance/paper-trades/XAUUSD
http://127.0.0.1:8000/institutional/performance/position-management/XAUUSD
http://127.0.0.1:8000/institutional/performance/recommendations/XAUUSD
```

## Safety Boundary

- This engine consumes analytical and paper-simulation records only.
- `simulation_only` remains true and `live_execution_enabled` remains false.
- No broker order path or MT5 trade submission is created.
- Missing market data or historical samples returns safe insufficient-data analytics.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day17_verification.py
python tests/phase2_day16_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
