# Client-Scoped AI Trading Dashboard

## Client Scope

The client dashboard is restricted to three instruments:

- EURUSD
- XAUUSD
- NIFTY50

Generic multi-market wording and unrelated symbols are not part of the client view.

## AI Signal Center

The AI Signal Center shows one card per scoped instrument. Each card displays signal, confidence, reason, entry, stop loss, take profit, risk/reward, risk status, and execution status.

EURUSD and XAUUSD signals are normalized from the existing MT5 demo strategy pipeline. If no confirmed setup exists, the dashboard shows `WAIT` with no invented confidence.

NIFTY50 is shown honestly as pending Indian market integration:

- signal: `WAIT`
- risk status: `INTEGRATION_PENDING`
- execution status: `BLOCKED`

## Signal-Based Execution Flow

Client execution is based on the selected AI signal:

1. Client selects a signal card.
2. The Signal Execution Panel displays symbol, direction, entry, SL, TP, lot, and risk/reward from that signal.
3. Client clicks Preview Signal Trade.
4. Backend runs the existing approval workflow.
5. If approved, client confirms demo execution.
6. The order is sent only through the existing guarded sender.

Manual direction and manual symbol controls are hidden from the client dashboard.

## Demo-Only Restrictions

The dashboard does not enable live trading or unrestricted broker execution. Guarded execution remains DEMO-only, and the existing guarded sender is still the only MT5 order path.

The client dashboard does not:

- call `mt5.order_send`
- bypass approval workflow
- place orders automatically
- create fake P&L
- create fake trades
- create fake BUY/SELL signals
- invent confidence values

## XAUUSD Market Data Handling

Before reading XAUUSD tick data, the MT5 market data service selects the symbol in Market Watch with `mt5.symbol_select(symbol, True)`. It then reads `mt5.symbol_info_tick(symbol)` and falls back to `symbol_info` bid/ask only when tick data is missing or zero.

Statuses remain honest:

- `OK` when bid, ask, spread, timestamp, and freshness are valid
- `STALE_OR_MARKET_CLOSED` when values or freshness are not valid
- `SYMBOL_NOT_AVAILABLE` when the broker cannot select the symbol

No XAUUSD prices are fabricated.

## NIFTY50 Pending Integration

NIFTY50 appears in market scope and signal scope, but it is disabled until Indian market data and broker integration are implemented. The dashboard shows Integration Pending instead of a fake price or signal.
