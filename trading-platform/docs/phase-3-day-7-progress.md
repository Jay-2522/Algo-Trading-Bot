# Phase 3 Day 7 - MT5 Demo Readiness & Broker Symbol Verification

## Purpose

Day 7 adds a read-only MT5 demo-readiness and broker symbol verification layer on top of broker compatibility metadata.

It checks whether MT5 can be reached for demo observation, attempts read-only symbol verification when possible, and produces broker-specific reports for STARTRADER, FxPro, and Vantage.

## Read-Only MT5 Readiness

`MT5DemoReadinessChecker` reports:

- terminal availability
- initialized status
- account availability
- broker server name when available
- read-only mode
- simulation-only safety state

If MT5 is unavailable, the checker returns a safe unavailable report instead of raising.

## Symbol Verification

`MT5SymbolVerifier` uses only read-only `symbol_info` behavior through the existing MT5 client path. It never places orders and never enables live execution.

Verification statuses:

- `VERIFIED`
- `NOT_FOUND`
- `CONDITIONAL`
- `MT5_UNAVAILABLE`
- `UNSUPPORTED`

## Conservative NIFTY50 Handling

`NIFTY50` remains conditional unless the actual demo terminal confirms symbol availability. The system does not claim NIFTY50 support for STARTRADER, FxPro, or Vantage without terminal evidence.

## API Routes

- `GET http://127.0.0.1:8000/brokers/mt5/readiness`
- `GET http://127.0.0.1:8000/brokers/verification/all`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/verification`
- `GET http://127.0.0.1:8000/brokers/FXPRO/verification`
- `GET http://127.0.0.1:8000/brokers/VANTAGE/verification`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/verification/EURUSD`

## Safety

This layer is read-only and demo-readiness only. It does not call `mt5.order_send`, does not prepare broker orders, does not place trades, and reports `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day7_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
