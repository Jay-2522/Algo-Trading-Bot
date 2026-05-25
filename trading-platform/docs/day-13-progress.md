# Day 13 Progress

## Background Loop Overview

Day 13 adds a controlled Background Trading Loop foundation. It repeatedly invokes the existing trading orchestration pipeline for monitored symbols while maintaining explicit lifecycle state, counters, latest decisions, and audit events.

## Simulation-Only Boundary

The loop cannot place live trades. It delegates only to the Day 10 orchestrator, which may invoke simulated execution after its advisory, news, and risk gates pass. The loop configuration rejects any attempt to disable simulation-only operation or enable live execution.

## Scheduler Behavior

- A single asyncio task is created by `POST /trading-loop/start`.
- Duplicate starts are rejected safely.
- A cycle evaluates at most the configured maximum symbols.
- The default interval is 10 seconds and validation enforces a minimum interval of 5 seconds.
- The task waits one configured interval before its first automatic cycle, sleeps between later cycles, records failures without crashing the application, and is cancelled cleanly on stop or application shutdown.

## Lifecycle Controls

- `start`: starts one rate-limited monitoring task.
- `pause`: retains the task while suspending orchestration cycles.
- `resume`: resumes cycles after a pause.
- `stop`: cancels and clears the task safely.
- `run-once`: executes one manual, simulation-only cycle without starting continuous monitoring.

## API Endpoints

- `GET /trading-loop/status`
- `GET /trading-loop/config`
- `POST /trading-loop/start`
- `POST /trading-loop/stop`
- `POST /trading-loop/pause`
- `POST /trading-loop/resume`
- `POST /trading-loop/run-once`
- `GET /trading-loop/symbols`
- `POST /trading-loop/symbols/{symbol}`
- `DELETE /trading-loop/symbols/{symbol}`

## Safety Protections

- No live execution capability is introduced.
- No broker order submission is implemented.
- Rate limiting prevents runaway cycles.
- Only one scheduler task can be active.
- Per-symbol errors are isolated into JSON-safe results.
- Lifecycle and cycle events are stored in audit logs when persistence is available.
- Existing API routers stay registered on the single FastAPI application.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'trading-loop' in r.path])"
```

Manual API checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/trading-loop/status
Invoke-RestMethod http://127.0.0.1:8000/trading-loop/config
Invoke-RestMethod http://127.0.0.1:8000/trading-loop/symbols
Invoke-RestMethod -Method Post http://127.0.0.1:8000/trading-loop/run-once
```

## Pending Day 14 Work

- Build an operational dashboard for monitoring loop and streaming health.
- Add protected runtime configuration updates with authorization controls.
- Add loop freshness, duration, and alerting metrics.
- Define paper-trading governance before any broader automation is considered.
