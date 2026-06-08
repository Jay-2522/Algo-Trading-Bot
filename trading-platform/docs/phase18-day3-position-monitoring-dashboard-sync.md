# Phase 18 Day 3 - Position Monitoring Dashboard Sync

## What Was Built

Phase 18 Day 3 adds a read-only MT5 demo position monitoring layer that joins current MT5 open positions with persistent trade journal records and exposes the result to backend analytics and the dashboard.

## Routes Added

- `GET /mt5-demo/position-monitor/status`
- `GET /mt5-demo/position-monitor/open`
- `GET /mt5-demo/position-monitor/open/{symbol}`
- `GET /mt5-demo/position-monitor/ticket/{ticket}`
- `POST /mt5-demo/position-monitor/sync`
- `GET /client-analytics/demo-positions/status`
- `GET /client-analytics/demo-positions/open`
- `GET /client-analytics/demo-positions/summary`

## Data Source

The monitor uses real MT5 demo open position data from `positions_get()` through the existing position sync service and persistent records from `PersistentTradeJournalService`.

## MT5 To Journal Mapping

Open MT5 positions are matched to journal records by:

- `mt5_ticket`
- `symbol`
- `account_login`
- `server`

The monitor returns ticket, symbol, side, lot, entry price, current price, SL, TP, floating P&L, distance to SL/TP, lifecycle status, journal status, account, server, and sync time.

## Safety Restrictions

- No orders are placed.
- No orders are closed.
- `mt5.order_send` is not used.
- Live trading remains disabled.
- Broker execution remains disabled.
- P&L is read from MT5 demo open position data only.
- Empty states are returned honestly when no open positions exist.

## Dashboard Behavior

The dashboard now includes a small `Open Demo MT5 Position` card. It displays the active DEMO position fields when present and labels the source as read-only MT5 DEMO data plus persistent journal matching.

## Empty State Behavior

When no open MT5 demo positions are returned, the dashboard shows:

`No open MT5 demo positions.`
