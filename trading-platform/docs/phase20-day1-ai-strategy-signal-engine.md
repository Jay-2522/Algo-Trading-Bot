# Phase 20 Day 1 AI Strategy Signal Engine

## Architecture

The client signal engine normalizes existing strategy pipeline outputs into one client-facing signal schema. It does not create new strategy logic and does not invent BUY, SELL, confidence, prices, or risk values.

Primary files:

- `backend/strategy/client_signal_engine.py`
- `backend/strategy/signal_history_service.py`
- `backend/api/client_signal_engine_routes.py`

## Signal Generation Flow

1. EURUSD and XAUUSD read the existing scoped signal center.
2. The signal center uses the current MT5 strategy consumption, risk qualification, and execution gate services.
3. The signal engine emits BUY or SELL only when the existing strategy output explicitly supports that action.
4. Otherwise the signal engine emits WAIT with null confidence.
5. NIFTY50 emits WAIT with `Indian market integration pending.`

## Signal Execution Flow

The dashboard Signal Execution Panel reads from `/client-signals-engine/current`. It auto-fills symbol, direction, entry, stop loss, take profit, lot, and risk/reward from the selected strategy signal.

Preview and confirm remain disabled unless the selected strategy signal is actionable and the existing guarded approval flow approves it.

## WAIT State Logic

WAIT is returned when:

- strategy output is unavailable
- strategy action is not explicitly BUY or SELL
- confidence is absent for an actionable signal
- NIFTY50 integration is pending

The default client-facing reason is `No confirmed setup available.`

## Confidence Rules

Confidence is carried forward only when provided by existing strategy output. It is never fabricated. WAIT signals always return `confidence=null`.

## Signal History

`SignalHistoryService` stores lightweight generated signal entries:

- symbol
- signal
- timestamp
- confidence
- execution status

This is signal history only. It does not create trades, P&L, or broker activity.

## Safety Restrictions

The signal engine does not:

- place orders
- call `mt5.order_send`
- enable live trading
- enable broker execution
- bypass guarded sender
- fake BUY/SELL signals
- fake confidence
- fake trade history or P&L
