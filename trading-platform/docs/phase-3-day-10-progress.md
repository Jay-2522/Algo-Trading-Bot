# Phase 3 Day 10 - Broker Data Normalization & Canonical Market Feed

## Purpose

Day 10 converts broker observation snapshots into canonical internal market feed records that are clean, JSON-safe, and ready for downstream AI/research consumers.

## Canonical Tick Model

Each canonical tick includes:

- canonical symbol
- broker id and broker symbol
- bid, ask, mid, spread
- digits and point
- market type
- timestamp and source
- usability and quality classification
- safety flags

## Normalization Logic

`BrokerFeedNormalizer` preserves raw broker prices and calculates:

```text
mid = (bid + ask) / 2
```

Ticks are marked unusable if bid/ask are missing, the symbol is unavailable, or ask is below bid.

## Quality Resolver

`CanonicalFeedQualityResolver` reuses Day 9 feed validation:

- usable valid spreads become `GOOD`
- wide or stale ticks become `WARNING`
- bad geometry becomes `INVALID`
- unavailable symbols remain `UNAVAILABLE`

NIFTY50 remains conservative and unavailable unless actually observed.

## API Routes

- `GET http://127.0.0.1:8000/brokers/canonical-feed/status`
- `GET http://127.0.0.1:8000/brokers/canonical-feed/all`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/canonical-feed`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/canonical-feed/EURUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/canonical-feed/XAUUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/canonical-feed/NIFTY50`

## Safety

This engine only normalizes observed data. It does not call `mt5.order_send`, does not build order payloads, and keeps `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day9_verification.py
python tests/phase3_day10_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
