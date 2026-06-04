# NIFTY50 Execution Bridge

## Purpose

The NIFTY50 execution bridge converts qualified trade candidates into execution intents and order previews.

It does not place orders.

## Pipeline

1. Trade candidate
2. Execution intent
3. Validation
4. Broker order mapping placeholder
5. Order preview
6. Audit event

## Broker Mapping Placeholders

Supported placeholder templates:

- Dhan
- Angel One
- Fyers
- Upstox
- Zerodha

No broker APIs are called.

## Preview Status

Possible preview states:

- READY_FOR_REVIEW
- REJECTED
- BLOCKED_EXECUTION_DISABLED
- BROKER_NOT_SELECTED
- FAILED_SAFE

## Safety

Execution flags remain disabled:

- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
