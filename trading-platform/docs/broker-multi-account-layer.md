# Broker Multi-Account Layer

## Scope

The broker account foundation covers the client forex broker accounts:

- StarTrader (`STARTRADER`)
- FxPro (`FXPRO`)
- Vantage (`VANTAGE`)

All three accounts are represented as MT5 account profiles, but they are not connected yet.

## Current MetaQuotes Demo Limitation

The platform currently reads one physically connected MT5 terminal. If the connected terminal is the MetaQuotes demo account, it is shown separately as `current_terminal_account`.

The MetaQuotes demo account is not labeled as StarTrader, FxPro, or Vantage.

## Broker Account Status

The account layer exposes:

- broker id and name
- platform
- account login and server when connected
- account type
- connection status
- balance/equity/margin/free margin when available
- execution enabled flag, which remains `false`
- last sync timestamp

Pending broker accounts return honest unavailable values instead of fake balances.

## Future Connection Steps

Future work can connect broker-specific MT5 terminals or broker account sessions, then map each terminal account to the matching broker profile. Until that happens, account status remains `PENDING_CONNECTION`.

## Multi-Account Execution Plan

The execution planner accepts a signal preview containing:

- symbol
- side
- lot
- entry
- stop loss
- take profit

It returns one plan per broker with eligibility, reason, and execution status. This is a preview-only planning layer. It never sends orders.

## Safety Restrictions

The broker layer does not:

- enable live trading
- enable broker execution
- place real-money trades
- call `mt5.order_send`
- bypass the guarded sender
- fake broker connections
- fake balances, trades, or P&L

All route responses keep `live_execution_enabled=false`, `broker_execution_enabled=false`, and `execution_allowed=false`.
