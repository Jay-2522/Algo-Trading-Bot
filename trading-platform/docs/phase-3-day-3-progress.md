# Phase 3 Day 3 - Replay Filter Calibration & Threshold Tuning Engine

## Purpose

Day 3 adds calibration analytics for historical replay output. The engine identifies which institutional gates repeatedly block replay simulation, classifies whether filters look too restrictive or too loose, and generates safe research-mode threshold suggestions.

## Components

- `replay_calibration_models.py`: typed block metrics, threshold suggestions, and calibration reports.
- `replay_block_reason_analyzer.py`: classifies blocked replay steps into news, session, confluence, setup-validation, risk, entry-geometry, and no-trade gates.
- `replay_threshold_analyzer.py`: detects high block rate, high avoid rate, no simulated trades, low confidence, repeated confluence/session rejection, and hard-gate pressure.
- `replay_threshold_recommendation_engine.py`: creates safe suggestions while preserving hard safety gates.
- `replay_calibration_engine.py`: coordinates block analysis, strictness analysis, and suggestions.
- `replay_calibration_report_builder.py`: produces JSON-safe calibration reports.

## API Routes

- `GET http://127.0.0.1:8000/replay/calibration/latest`
- `GET http://127.0.0.1:8000/replay/calibration/{replay_id}`
- `GET http://127.0.0.1:8000/replay/calibration/block-reasons/{replay_id}`
- `GET http://127.0.0.1:8000/replay/calibration/suggestions/{replay_id}`

## Calibration Safety

Recommendations are research-mode only. The engine may suggest relaxing analytical thresholds such as confluence or session strictness, but it keeps hard gates such as risk controls, entry geometry, and news blackout behavior strict. It does not alter runtime configuration automatically.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day3_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

The module remains simulation-only with `live_execution_enabled = false`.
