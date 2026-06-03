# NIFTY50 Market Data Integration

## Purpose

Phase 12 Day 3 adds manual NIFTY50 market-data ingestion architecture for candles and ticks.

## Supported Timeframes

- M1
- M5
- M15
- H1
- H4
- D1

## Ingestion

Manual ingestion endpoints accept:

- `POST /nifty50/market-data/ingest-candle`
- `POST /nifty50/market-data/ingest-tick`

No live broker feed is connected.

## Validation

Candles are accepted only when:

- `high >= low`
- `open` is within the candle range
- `close` is within the candle range
- `volume >= 0`

Malformed candles are rejected and counted in market-data health.

## Snapshot

`GET /nifty50/market-data/latest` returns:

- symbol
- session context
- latest price from latest tick or candle close
- latest timestamp
- available timeframes
- data health
- safety flags

## Safety

The market-data layer does not:

- call broker APIs
- use API keys
- fetch live prices
- place orders
- enable broker execution
