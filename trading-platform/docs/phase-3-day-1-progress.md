# Phase 3 Day 1: Advanced Historical Replay Engine

## Purpose

The Advanced Historical Replay Engine replays deterministic historical candle windows through the completed Phase 2 institutional pipeline. It is designed for historical simulation, validation, and replay observability only.

## Architecture

- `HistoricalReplayLoader` loads historical candles or deterministic local fallback data.
- `ReplayClock` creates rolling step indexes.
- `ReplayWindowBuilder` exposes only candles visible at the replay step.
- `AdvancedHistoricalReplayEngine` runs institutional orchestration, simulation decision, paper lifecycle, and position management per step.
- `ReplayEventLogger` stores step and event observations for the run.
- `ReplayMetricsCalculator` summarizes decisions, paper outcomes, net R, and placeholder drawdown.
- `ReplayStorage` keeps replay summaries in a safe in-memory fallback store.
- `ReplayService` exposes API-facing operations.

## No-Lookahead Logic

Replay steps begin only after `window_size` candles are available. Each step passes a window ending at the current replay index. Future candles are never included in the visible window.

## API Routes

- `GET /replay/status`
- `POST /replay/run/{symbol}`
- `GET /replay/recent`
- `GET /replay/result/{replay_id}`
- `GET /replay/metrics/{replay_id}`

Manual checks:

```text
http://127.0.0.1:8000/replay/status
http://127.0.0.1:8000/replay/recent
```

Run replay:

```text
POST http://127.0.0.1:8000/replay/run/XAUUSD
```

## Safety Boundary

- Historical replay is simulation-only.
- No broker order path is introduced.
- No MT5 live execution is required.
- `simulation_only` remains true and `live_execution_enabled` remains false.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day1_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```
