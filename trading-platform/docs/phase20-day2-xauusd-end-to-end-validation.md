# Phase 20 Day 2 - XAUUSD End-to-End Validation

## Scope

This phase validates XAUUSD across the read-only market-data layer, strategy signal engine, approval workflow, guarded sender boundary, and client dashboard.

No live execution was enabled. No broker execution was enabled. No XAUUSD order was placed.

## Market Data Status

XAUUSD is supported by the MT5 demo market-data service alongside EURUSD. Before reading tick or candle data, the service calls `symbol_select(symbol, True)` so a visible XAUUSD chart or Market Watch symbol can be read safely.

Validated routes:

- `GET /mt5-demo/market-data/status`
- `GET /mt5-demo/market-data/tick/XAUUSD`
- `GET /mt5-demo/market-data/spread/XAUUSD`
- `GET /mt5-demo/history/XAUUSD/M5/summary`
- `GET /mt5-demo/history/XAUUSD/H1/summary`

Honest classifications:

- `OK` with `freshness=READY` only when MT5 returns usable bid, ask, spread, and a fresh tick timestamp.
- `STALE_OR_MARKET_CLOSED` when the symbol exists but the feed is stale or not updating.
- `SYMBOL_NOT_AVAILABLE` or `SYMBOL_UNAVAILABLE` when MT5 cannot select or read XAUUSD.
- `MT5_UNAVAILABLE` when the terminal or Python package is unavailable.

The service does not fabricate bid, ask, spread, candle data, or freshness.

## Strategy Signal Status

XAUUSD is exposed through:

- `GET /client-signals-engine/XAUUSD`

The AI strategy signal engine only normalizes existing strategy output. It emits:

- `BUY` or `SELL` only when the existing strategy pipeline explicitly produces that action with numeric confidence.
- `WAIT` when there is no confirmed setup.
- `INSUFFICIENT_DATA` when the MT5 strategy feed cannot provide enough data.
- `BLOCKED` when execution is unsafe.

Confidence is `null` for `WAIT` signals.

## Approval Workflow Status

The approval workflow accepts XAUUSD validation payloads with:

- `environment=DEMO`
- `symbol=XAUUSD`
- `lot=0.01`
- valid entry, stop loss, and take profit
- manual confirmation and no-live-trading acknowledgements

It runs the normal authorization, dry-run, preflight, simulator, readiness, test plan, and final approval chain without placing an order.

If MT5 data or readiness is unavailable, the workflow returns explicit blockers instead of fabricating approval.

## Execution Readiness

The guarded sender still allows runtime sending only for EURUSD:

- `allowed_symbols = {"EURUSD", "XAUUSD"}`
- `runtime_symbols = {"EURUSD"}`

That means XAUUSD can be prepared and reviewed for a future guarded demo test, but it is blocked today by `RUNTIME_SYMBOL_NOT_ENABLED`.

The filling-mode lookup is symbol-aware for future readiness, but this does not enable XAUUSD runtime sending.

## Dashboard Status

The dashboard now classifies XAUUSD as one of:

- `Market Ready`
- `Market Closed / Feed Offline`
- `Symbol Not Available`
- `Waiting for Strategy Setup`
- `Ready for Future Demo Test`

XAUUSD is not shown as currently tradable. The execution panel remains restricted to EURUSD guarded demo execution.

## Remaining Blocker

XAUUSD runtime demo sending remains intentionally disabled until a future explicit guarded test request.

## Safety Restrictions

- No live trading.
- No broker execution.
- No unrestricted `mt5.order_send`.
- No XAUUSD order placement in verification.
- No fake XAUUSD bid/ask.
- No fake BUY/SELL signals.
- No fake P&L.
