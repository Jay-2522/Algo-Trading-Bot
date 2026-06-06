# Phase 15 Day 2 - MT5 Market Data Retrieval

## Scope

Phase 15 Day 2 validates read-only MT5 demo market-data retrieval from the backend.

This phase does not place real orders or demo broker orders. It does not enable broker execution, live trading, strategy changes, risk changes, or credential storage.

## What Was Tested

- MT5 market-data status endpoint
- EURUSD latest tick retrieval
- XAUUSD latest tick retrieval
- EURUSD M5 and H1 candle retrieval
- XAUUSD M5 and H1 candle retrieval
- EURUSD spread retrieval
- XAUUSD spread retrieval
- Invalid symbol handling
- Invalid timeframe handling
- Safety flags across all market-data responses

## Supported Symbols

- `EURUSD`
- `XAUUSD`

## Supported Timeframes

- `M1`
- `M5`
- `M15`
- `H1`
- `H4`
- `D1`

## API Routes

- `GET /mt5-demo/market-data/status`
- `GET /mt5-demo/market-data/tick/{symbol}`
- `GET /mt5-demo/market-data/candles/{symbol}/{timeframe}`
- `GET /mt5-demo/market-data/spread/{symbol}`

## Safety Restrictions

All responses preserve:

- `simulation_only=true`
- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

The service uses MT5 only for read-only functions such as symbol information, tick retrieval, and historical candle retrieval.

## Known Limitations

- MT5 must be installed and terminal access must be available for live demo data.
- If MT5 is unavailable, endpoints return safe unavailable payloads instead of crashing.
- If a symbol is unavailable or hidden, the service attempts Market Watch selection and reports any failure honestly.
- Data availability depends on the connected MT5 demo server.

## No Execution Statement

No order placement is implemented in this phase. No new `mt5.order_send`, buy, sell, or position-opening code is added.
