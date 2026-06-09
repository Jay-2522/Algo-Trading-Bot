# Phase 18 Final - Client Operating Dashboard

## Dashboard Structure

The client dashboard is organized into clean operating sections:

1. Header / Account Status
2. Account Health
3. Floating P&L
4. Last Trade
5. Forex Sessions
6. Market Status
7. Quick Trade Panel
8. Open Demo Positions
9. Closed Demo Trades
10. Performance Summary
11. Safety / Mode Status

Developer-oriented route names, workflow IDs, audit IDs, sync IDs, raw execution flags, and verification details are kept out of the client view. The developer dashboard remains available separately at `/dashboard/developer`.

The previous readiness checklist has been replaced by a compact Trade Status card. It shows only actionable client states such as Market Open, Trade Ready, Market Closed, Stop Loss Required, Take Profit Required, Existing Demo Position Active, or Check SL / TP Placement. Approval workflow internals remain hidden.

## Client Workflow

The client can:

- monitor the MT5 DEMO account
- review margin level, free margin, and used margin when MT5 provides them
- see current floating P&L from open demo positions
- see the latest completed trade result
- check Sydney, Tokyo, London, and New York forex session status based on UTC
- check EURUSD and XAUUSD feed status
- review open demo positions
- review closed demo trades
- open `/dashboard/history` to search, sort, and page through completed journal trades
- view performance summary
- preview a guarded demo trade
- confirm and send a single guarded MT5 DEMO order
- manually refresh positions or sync lifecycle state

## Order Placement Flow

The dashboard uses the existing safe backend path only:

Market status -> Approval workflow -> Guarded sender -> MT5 demo execution -> Position sync -> Journal -> Lifecycle -> Analytics

Preview calls:

- `POST /mt5-demo/demo-approval-workflow/run`

Send calls:

- `POST /mt5-demo/guarded-demo-order/send`

The send payload includes explicit demo-only acknowledgements and the guarded sender final flag. The UI never calls direct MT5 order routes.

## Safety Protections

The trade button is disabled when:

- the EURUSD feed is closed or offline
- a demo position is already open
- SL or TP is missing or invalid
- lot is not fixed at `0.01`
- the approval workflow has not approved the preview

The confirmation modal repeats the order details before the guarded send call.

## Demo-Only Restrictions

The client cannot:

- enable live trading
- enable broker execution
- bypass the approval workflow
- bypass the guarded sender
- place unrestricted orders
- close trades from the dashboard
- create fake trades
- create fake P&L

Manual sync buttons are read-only synchronization controls and do not place or close orders.

## Trade History

The trade history page reads completed trades from:

- `GET /trade-journal/persistence/recent`

It displays Date, Symbol, Direction, Lot, Entry, Exit, P&L, Result, and Duration. Dates are formatted for clients in UTC instead of raw ISO strings. The page supports symbol search, date sorting, pagination, and responsive horizontal scrolling for smaller screens.

Empty states remain honest:

- open positions: `Waiting for the next trade opportunity.`
- completed trades: `Completed trades will appear here.`
- unavailable feed data: `Market feed unavailable.`
