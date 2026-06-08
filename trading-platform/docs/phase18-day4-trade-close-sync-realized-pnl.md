# Phase 18 Day 4 - Trade Close Sync And Realized P&L

## What Was Built

Phase 18 Day 4 adds a read-only MT5 demo close synchronization service that detects when a journaled open MT5 demo trade is no longer open, matches the close in MT5 history, and updates the persistent journal with realized P&L.

## Close Detection

The close sync service reads:

- journal `OPEN` trades from `PersistentTradeJournalService`
- current MT5 demo open positions via `positions_get()`
- MT5 demo history via `history_deals_get()` and `history_orders_get()`

If a journaled `OPEN` trade is still present in MT5 positions, it remains `OPEN`. If it is missing from open positions, the service searches history for a matching close deal.

## MT5 History Matching

Close history is matched by:

- `mt5_ticket` against deal `position_id`, `order`, or `ticket`
- `symbol`
- `volume`
- demo account context when available

If no matching close deal exists, the journal is left unchanged and the sync response includes `CLOSE_HISTORY_NOT_FOUND`.

## P&L Calculation

The service calculates:

- `realized_pnl` from deal profit
- `commission` from deal commission
- `swap` from deal swap
- `net_pnl` / `total_pnl` as realized profit plus commission plus swap

Result classification:

- positive net P&L: `WIN`
- negative net P&L: `LOSS`
- zero net P&L: `BREAKEVEN`

## Journal Updates

Closed trades are updated by MT5 ticket using `mark_trade_closed_by_ticket()`. The journal stores close price, close time, realized P&L, commission, swap, net P&L, result, duration, and exit reason.

## Dashboard Behavior

The dashboard position card shows floating P&L while the MT5 demo trade is open. If no open position exists and the persistent journal has a closed demo trade, the card shows realized P&L, result, close time, and exit reason.

## Safety Restrictions

- No orders are placed.
- No orders are closed.
- `mt5.order_send` is not used.
- Live trading remains disabled.
- Broker execution remains disabled.
- No fake closed trades are created.
- No fake P&L is generated.
