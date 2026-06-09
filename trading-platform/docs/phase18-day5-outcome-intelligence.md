# Phase 18 Day 5 - Trade Outcome Intelligence

## What Was Built

Phase 18 Day 5 adds a post-trade intelligence layer that analyzes closed MT5 demo journal trades and explains outcomes without generating fake trades or fake P&L.

## Outcome Analysis

For each closed trade, the service calculates:

- result (`WIN`, `LOSS`, `BREAKEVEN`)
- realized P&L
- risk amount
- reward amount
- realized RR
- duration
- entry and exit timestamps
- market session
- symbol and side

## Attribution

Wins are attributed to TP reached, favorable move, or manual profitable close. Losses are attributed to SL reached, manual loss close, or adverse move. Breakeven trades are attributed to minimal P&L or manual breakeven exit.

## Performance Aggregation

The service aggregates performance by:

- symbol
- side
- market session

Metrics include total trades, wins, losses, win rate, net P&L, average P&L, and average RR.

## Routes

- `GET /analytics/outcomes/status`
- `GET /analytics/outcomes/latest`
- `GET /analytics/outcomes/trades`
- `GET /analytics/outcomes/symbols`
- `GET /analytics/outcomes/sessions`
- `GET /analytics/outcomes/summary`
- `GET /client-analytics/reports-v3/performance`

## Dashboard

The dashboard includes a DEMO Performance section with total closed trades, win rate, net P&L, average RR, best/worst trade, and best/worst symbol. It shows an honest empty state when no closed demo trades exist.

## Safety

This layer is analytics-only. It does not place orders, close orders, call `mt5.order_send`, enable live trading, enable broker execution, or invent performance data.
