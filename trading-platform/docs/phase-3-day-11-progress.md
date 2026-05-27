# Phase 3 Day 11 Progress - Broker Candle Stream & Multi-Timeframe Feed Engine

## Purpose

Day 11 adds a read-only broker candle stream layer for AI-ready OHLC market data. It supports the client brokers `STARTRADER`, `FXPRO`, and `VANTAGE`, and the client symbols `EURUSD`, `XAUUSD`, and `NIFTY50`.

## Architecture

- `canonical_candle_models.py` defines canonical OHLC candle and multi-timeframe feed report models.
- `mt5_candle_fetcher.py` attempts read-only MT5 candle reads when available and falls back to deterministic simulated candles.
- `candle_normalizer.py` normalizes raw candles into canonical records.
- `candle_stream_quality_checker.py` validates OHLC integrity and feed quality.
- `multi_timeframe_feed_engine.py` builds M5, M15, H1, and H4 feeds.
- `canonical_candle_feed_service.py` exposes service-level status and feed access.

## Supported Timeframes

- `M5`
- `M15`
- `H1`
- `H4`

## Safety

This layer is market-data only. It does not place orders, does not build broker trade payloads, and does not enable live execution. Every returned candle/report keeps:

- `simulation_only = true`
- `live_execution_enabled = false`

## Routes

- `GET /brokers/candles/status`
- `GET /brokers/candles/all`
- `GET /brokers/{broker_id}/candles/{symbol}`
- `GET /brokers/{broker_id}/candles/{symbol}/{timeframe}`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day11_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
