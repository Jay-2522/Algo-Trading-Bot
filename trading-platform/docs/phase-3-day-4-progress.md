# Phase 3 Day 4 - Replay Scenario Comparison Engine

## Purpose

Day 4 adds comparison analytics across historical replay scenarios. It ranks replay reports, compares timeframe behavior, compares calibration filter restrictiveness, and produces dashboard-ready recommendations for deeper simulation research.

## Components

- `replay_comparison_models.py`: typed scenario, timeframe, and filter comparison models.
- `replay_scenario_ranker.py`: bounded 0-100 scenario quality score.
- `replay_scenario_comparator.py`: ranks replay scenarios and summarizes strengths, weaknesses, and recommendations.
- `replay_timeframe_comparator.py`: groups replay reports by timeframe and identifies strongest/weakest timeframe.
- `replay_filter_comparator.py`: compares calibration gate counts and identifies restrictive filters.
- `replay_comparison_report_builder.py`: combines scenario, timeframe, and filter comparisons.

## Ranking Factors

Scenario score is bounded from 0 to 100 and uses:

- Net R: 25 points
- Win rate: 20 points
- Block rate: 20 points
- Average confidence: 15 points
- Trade activity: 10 points
- Drawdown safety: 10 points

No-trade scenarios are capped at a low score so they cannot outrank productive replay scenarios.

## API Routes

- `GET http://127.0.0.1:8000/replay/compare/recent`
- `POST http://127.0.0.1:8000/replay/compare`
- `GET http://127.0.0.1:8000/replay/compare/timeframes/XAUUSD`
- `GET http://127.0.0.1:8000/replay/compare/filters`

## Safety

The comparison engine is historical analytics only. It reads stored replay reports and calibration reports, never changes thresholds automatically, never creates broker payloads, and preserves `simulation_only = true` with `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day3_verification.py
python tests/phase3_day4_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```
