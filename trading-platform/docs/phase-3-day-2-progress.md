# Phase 3 Day 2 - Replay Trade Analytics & Historical Report Engine

## Purpose

Day 2 extends the historical replay engine with analytics and reporting. Replay runs now produce professional post-run diagnostics for simulated trade outcomes, decision quality, equity progression, and recurring weaknesses.

## Components

- `replay_report_models.py`: typed report, trade, decision, equity, and weakness models.
- `replay_trade_analyzer.py`: win/loss/breakeven, R-multiple, expectancy, and holding-step analytics.
- `replay_decision_analyzer.py`: replay action distribution, block rate, confidence, and common action analytics.
- `replay_equity_curve.py`: deterministic equity curve from closed simulated paper outcomes.
- `replay_weakness_detector.py`: detects no-trade samples, high block rates, weak RR, low win rate, and data gaps.
- `replay_report_builder.py`: combines all analytics into a JSON-safe `ReplayHistoricalReport`.

## API Routes

- `GET http://127.0.0.1:8000/replay/report/{replay_id}`
- `GET http://127.0.0.1:8000/replay/report/latest`
- `GET http://127.0.0.1:8000/replay/analytics/trades/{replay_id}`
- `GET http://127.0.0.1:8000/replay/analytics/decisions/{replay_id}`
- `GET http://127.0.0.1:8000/replay/equity/{replay_id}`
- `GET http://127.0.0.1:8000/replay/weaknesses/{replay_id}`

## Safety

The engine remains historical analytics only. It does not connect execution APIs, does not place broker orders, does not call `mt5.order_send`, and always reports `simulation_only = true` with `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day1_verification.py
python tests/phase3_day2_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```
