# Phase 18 Final - Client Operating Dashboard

## Dashboard Structure

The client dashboard is organized into seven clean operating sections:

1. Header / Account Status
2. Market Status
3. Quick Trade Panel
4. Open Demo Positions
5. Closed Demo Trades
6. Performance Summary
7. Safety / Mode Status

Developer-oriented route names, workflow IDs, audit IDs, sync IDs, raw execution flags, and verification details are kept out of the client view. The developer dashboard remains available separately at `/dashboard/developer`.

## Client Workflow

The client can:

- monitor the MT5 DEMO account
- check EURUSD and XAUUSD feed status
- review open demo positions
- review closed demo trades
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
