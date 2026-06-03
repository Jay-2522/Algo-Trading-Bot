# NIFTY50 Broker Architecture

## Purpose

This architecture prepares the project for the NIFTY50 production layer without connecting to live broker APIs or placing orders.

## Broker Candidates

Supported candidates:

- Dhan
- Angel One
- Fyers
- Upstox
- Zerodha

Dhan and Angel One are recommended candidates for the next evaluation step because they are suitable for Indian market automation and typically offer accessible API workflows. The final broker remains configurable and is not selected in Phase 12 Day 1.

## Safety Boundary

Phase 12 Day 1 does not configure:

- API keys
- broker credentials
- live market data
- paper trading sessions
- live order permissions
- broker execution

The adapter base returns placeholders only. `place_order` returns `ORDER_EXECUTION_DISABLED`.

## Market Data

The NIFTY50 market data service returns a placeholder snapshot with no generated price values.

The snapshot uses:

- `placeholder=true`
- `data_source=PLACEHOLDER`
- `last_price=null`
- `open=null`
- `high=null`
- `low=null`
- `previous_close=null`
- `volume=null`

## Session Context

The NSE session service provides architecture-only session labels:

- `PRE_OPEN_PLACEHOLDER`
- `REGULAR_SESSION_PLACEHOLDER`
- `POST_MARKET_PLACEHOLDER`
- `CLOSED_PLACEHOLDER`

The exact NSE holiday calendar is pending.

## Next Steps

1. Select broker candidate.
2. Add sandbox/manual market data ingestion.
3. Build NIFTY50 strategy layer.
4. Add paper/demo validation.
5. Keep live and broker execution disabled until explicitly approved.
