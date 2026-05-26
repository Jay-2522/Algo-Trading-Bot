# Phase 2 Day 13: Institutional Paper Trade Lifecycle Engine

## Purpose

The Paper Trade Lifecycle Engine converts an approved simulation decision into a traceable, simulation-only paper position lifecycle. It never constructs a broker request and never enables live execution.

## Lifecycle

1. An approved `SIMULATE_BUY` or `SIMULATE_SELL` decision with complete price geometry creates a `PENDING` candidate.
2. A candidate becomes an `ACTIVE` paper position only when an observed candle intersects its entry zone.
3. Entry is recorded deterministically at the midpoint of the proposed entry zone.
4. Subsequent observed candles are evaluated against invalidation and target levels.
5. A position is recorded as `CLOSED` with `WIN`, `LOSS`, or `BREAKEVEN` outcome. Pending candidates may become `EXPIRED` or `CANCELLED`.

## Entry And Outcome Logic

For a BUY candidate, a candle enters the zone when its range overlaps `entry_low` through `entry_high`. The position loses when price reaches or crosses below the invalidation level and wins when price reaches or crosses above the target.

For a SELL candidate, the same overlap activates the position. The position loses when price reaches or crosses above invalidation and wins when price reaches or crosses below the target.

When both invalidation and target are crossed in one candle, invalidation is evaluated first. This prevents optimistic intrabar assumptions in paper results.

## Risk Outcome

Simulated points are directional:

- BUY: `close_price - entry_price`
- SELL: `entry_price - close_price`

The realized R result is simulated points divided by initial price risk. Missing or zero-risk geometry returns a safe zero result. Candidate creation rejects incomplete or directionally invalid geometry.

## Storage

`PaperTradeStorage` is an isolated in-memory paper lifecycle store with candidate, position, and event-log records. It is deliberately independent from execution and broker layers. If a durable paper-trade table is introduced later, it can replace this store without changing lifecycle rules or API contracts.

A deterministic intent signature prevents repeated dashboard reads from creating duplicate lifecycle records for the same unchanged simulated setup.

## API Routes

- `GET /institutional/paper-trades/{symbol}`
- `GET /institutional/paper-trades/candidates/{symbol}`
- `GET /institutional/paper-trades/active/{symbol}`
- `GET /institutional/paper-trades/closed/{symbol}`
- `GET /institutional/paper-trades/latest/{symbol}`
- `GET /institutional/paper-trades/summary/{symbol}`

Example manual checks:

```text
http://127.0.0.1:8000/institutional/paper-trades/XAUUSD
http://127.0.0.1:8000/institutional/paper-trades/candidates/XAUUSD
http://127.0.0.1:8000/institutional/paper-trades/active/XAUUSD
http://127.0.0.1:8000/institutional/paper-trades/closed/XAUUSD
http://127.0.0.1:8000/institutional/paper-trades/latest/XAUUSD
http://127.0.0.1:8000/institutional/paper-trades/summary/XAUUSD
```

## Safety Boundary

- All candidates and positions carry `simulation_only = true`.
- Dashboard summaries expose `live_execution_enabled = false`.
- No broker order function or MT5 order placement is introduced.
- Missing market data fails closed and creates no candidate.
- The system tracks paper observations only; it does not trigger execution.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
