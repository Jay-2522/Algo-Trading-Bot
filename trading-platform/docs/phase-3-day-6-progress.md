# Phase 3 Day 6 - Broker Compatibility Foundation

## Purpose

Day 6 adds a simulation-only broker compatibility foundation for the client broker environment:

- STARTRADER
- FxPro
- Vantage

The module prepares broker-specific symbol mapping, demo-readiness checks, and future read-only MT5/MT4-MT5 integration planning. It does not connect to brokers and does not place orders.

## Broker Registry

The registry exposes static metadata for each supported broker:

- broker id and display name
- platform family
- supported account modes: `DEMO`, `LIVE_DISABLED`, `READ_ONLY`
- supported market categories
- compatibility notes

## Symbol Mapping

Canonical client symbols are mapped conservatively:

- `EURUSD` -> `EURUSD`
- `XAUUSD` -> `XAUUSD`
- `NIFTY50` -> marked unsupported/conditional pending broker demo terminal verification

NIFTY50 is intentionally not claimed as supported for STARTRADER, FxPro, or Vantage until the actual demo terminal symbol list confirms availability.

## Demo Readiness

Demo readiness checks confirm:

- broker metadata exists
- platform type is documented
- EURUSD/XAUUSD are theoretical demo candidates
- NIFTY50 needs verification
- live execution remains disabled
- safety mode remains simulation-only

## API Routes

- `GET http://127.0.0.1:8000/brokers/status`
- `GET http://127.0.0.1:8000/brokers`
- `GET http://127.0.0.1:8000/brokers/STARTRADER`
- `GET http://127.0.0.1:8000/brokers/FXPRO`
- `GET http://127.0.0.1:8000/brokers/VANTAGE`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/symbols`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/symbols/EURUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/demo-readiness`

## Safety

This module is metadata and readiness only. It does not call MT5, does not call `mt5.order_send`, does not construct broker order payloads, and keeps `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day6_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
