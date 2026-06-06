# Phase 16 Day 1 Demo Order Authorization

## Why This Layer Exists

The demo order authorization layer creates a hard separation between strategy preview, future demo order testing, and live production trading. It is intentionally locked by default so a connected MT5 demo account, live market data, risk qualification, and execution gate validation cannot accidentally become broker execution.

## Preview vs Demo Order vs Live Order

- Simulation preview reads market data, consumes strategy output, qualifies risk, and validates the execution gate without submitting orders.
- Demo order testing is a future controlled mode for MT5 DEMO-only order checks after explicit manual authorization.
- Live order execution is production trading and remains disabled. This layer rejects live execution and broker execution flags.

## Required Safety Confirmations

Demo authorization can only be accepted when the request confirms:

- `environment = DEMO`
- `manual_confirmation = true`
- `acknowledge_no_live_trading = true`
- `acknowledge_demo_only = true`
- `max_demo_lot = 0.01`

Any request attempting to enable live execution, broker execution, or direct execution is rejected.

## Max Demo Lot Rule

The maximum demo lot is fixed at `0.01`. Larger lots are not accepted by the authorization service.

## Live Trading Remains Disabled

Even after a valid authorization request, the service returns `READY_FOR_DEMO_ORDER_TESTING` while preserving:

- `execution_allowed = false`
- `live_execution_enabled = false`
- `broker_execution_enabled = false`

## No Order Placement Today

Phase 16 Day 1 only adds authorization and checklist routes. It does not add broker execution code, does not place demo orders, and does not enable order submission.

## Day 2 Next Steps

Day 2 can build on this layer by adding a separate DEMO-only dry order request validator, re-checking risk qualification and execution gate status at request time, and requiring a fresh manual confirmation before any controlled demo order test is considered.
