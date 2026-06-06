# Phase 15 Day 3 - MT5 Market Data Pipeline

## Architecture

Phase 15 Day 3 adds a central read-only market snapshot pipeline for MT5 demo data.

The pipeline is implemented in:

- `backend/mt5_demo/mt5_market_data_service.py`
- `backend/mt5_demo/market_snapshot_service.py`
- `backend/api/mt5_demo_routes.py`

The market snapshot service calls the existing MT5 demo market-data service for:

- EURUSD latest tick
- XAUUSD latest tick
- EURUSD spread
- XAUUSD spread
- EURUSD latest M5/H1 candle timestamps
- XAUUSD latest M5/H1 candle timestamps

## Data Flow

1. Backend initializes MT5 for a read-only data request.
2. Tick and candle data are retrieved from the MT5 demo terminal.
3. Tick data is validated before being marked `OK`.
4. Candle timestamps are collected as fallback market-data availability evidence.
5. Freshness is calculated from the freshest valid tick or candle timestamp.
6. `/mt5-demo/overview` exposes a central dashboard-ready payload.
7. The frontend dashboard reads `/mt5-demo/overview` and displays demo bid, spread, availability, and freshness.

## Freshness Logic

- `READY`: newest valid market-data timestamp is under 5 minutes old.
- `STALE`: newest valid market-data timestamp is 5 to 30 minutes old.
- `OFFLINE`: newest valid market-data timestamp is over 30 minutes old or unavailable.

## Safety Controls

All market pipeline payloads preserve:

- `simulation_only=true`
- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

No trading logic, risk logic, broker execution, order sending, buy, or sell paths are added.

## Dashboard Integration

The dashboard market cards show:

- EURUSD demo bid
- EURUSD spread
- XAUUSD demo bid when available
- XAUUSD availability status when tick data is stale or unavailable
- MT5 demo market-data freshness

The dashboard does not show live trading profit, account profit, fake P&L, or broker execution values.
