# Phase 3 Day 9 - Broker Feed Quality & Data Validation Engine

## Purpose

Day 9 validates broker observation snapshots for feed quality. It checks bid/ask availability, spread quality, tick freshness, and symbol availability, then produces broker-level feed quality reports.

## Spread Quality

Spread quality is evaluated in symbol-specific point units:

- `EURUSD`: <=2 excellent, <=5 good, <=10 acceptable, >10 wide
- `XAUUSD`: <=20 good, <=50 acceptable, >50 wide
- `NIFTY50`: <=5 good, <=15 acceptable, >15 wide

Missing, malformed, or negative spreads are invalid.

## Tick Freshness

Ticks are considered fresh only when the snapshot timestamp is present, parseable, timezone-safe, and within the configured threshold. The default threshold is 30 seconds.

## Feed Validation

The validator checks:

- snapshot availability
- bid present
- ask present
- ask >= bid
- valid spread
- fresh tick
- observation source availability

Feed quality values:

- `VALID`
- `WARNING`
- `INVALID`
- `UNAVAILABLE`

## API Routes

- `GET http://127.0.0.1:8000/brokers/feed-quality/status`
- `GET http://127.0.0.1:8000/brokers/feed-quality/all`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/feed-quality`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/feed-quality/EURUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/feed-quality/XAUUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/feed-quality/NIFTY50`

## Safety

This layer validates observed broker data only. It does not call `mt5.order_send`, does not create broker order payloads, and keeps `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day9_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
