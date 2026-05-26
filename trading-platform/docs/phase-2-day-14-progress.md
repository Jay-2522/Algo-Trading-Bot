# Phase 2 Day 14: Institutional Position Management Engine

## Purpose

The Institutional Position Management Engine manages active paper positions after simulated entry. It produces analytical lifecycle decisions only and does not send orders, construct broker payloads, or enable live execution.

## Position Management Flow

The management context consumes active positions from the Paper Trade Lifecycle Engine. Each active paper position is evaluated in priority order:

1. Emergency simulation-integrity and risk shutdown checks.
2. Opposing structural invalidation checks.
3. Session and time-based exit checks.
4. Partial profit realization.
5. Break-even capital protection.
6. Structure-aware trailing-stop adjustment.

## State Machine

Supported states are `PENDING`, `ACTIVE`, `PARTIAL_TP_1`, `PARTIAL_TP_2`, `BREAK_EVEN`, `TRAILING`, `CLOSING`, `CLOSED`, `INVALIDATED`, and `EMERGENCY_EXIT`.

The standard protected runner path is:

```text
ACTIVE -> PARTIAL_TP_1 -> BREAK_EVEN -> TRAILING -> PARTIAL_TP_2
```

Any active management state may transition to `INVALIDATED` or `EMERGENCY_EXIT` when a critical simulation safety condition occurs. Invalid routine transitions are rejected deterministically.

## Partial Profit And Protection Logic

- TP1 occurs at 1R and reduces the original simulated size by 50 percent.
- TP2 occurs at 2R and reduces the original simulated size by 25 percent.
- The remaining 25 percent is retained as a runner by default.
- TP3 at 3R is configurable and may close the runner when explicitly enabled.
- After TP1, stop protection may improve to entry; it can never worsen risk.
- Trailing only tightens protection after TP2 and uses protected recent candle structure with continuation support.

## Institutional Exits

Structural exits are raised for strong opposing MSS or CHOCH events and opposing high-quality breaker blocks. Session exits are raised when a tagged entry killzone has ended, timing quality deteriorates, liquidity becomes poor, or the New York closing risk window approaches.

Emergency exits fail closed when risk status blocks management, reward-to-risk geometry is impossible, structure becomes directly contradictory, abnormal volatility is observed, or simulation integrity is violated.

## API Routes

- `GET /institutional/position-management/{symbol}`
- `GET /institutional/position-management/active/{symbol}`
- `GET /institutional/position-management/exits/{symbol}`
- `GET /institutional/position-management/emergency/{symbol}`
- `GET /institutional/position-management/state/{symbol}`
- `GET /institutional/position-management/context/{symbol}`

Example checks:

```text
http://127.0.0.1:8000/institutional/position-management/XAUUSD
http://127.0.0.1:8000/institutional/position-management/active/XAUUSD
http://127.0.0.1:8000/institutional/position-management/exits/XAUUSD
http://127.0.0.1:8000/institutional/position-management/emergency/XAUUSD
http://127.0.0.1:8000/institutional/position-management/state/XAUUSD
http://127.0.0.1:8000/institutional/position-management/context/XAUUSD
```

## Safety Boundary

- Every management decision remains `simulation_only = true`.
- Context and state responses preserve `live_execution_enabled = false`.
- No MT5 order placement or broker execution integration is introduced.
- Missing market data returns a safe empty management context.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day14_verification.py
python tests/phase2_day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
