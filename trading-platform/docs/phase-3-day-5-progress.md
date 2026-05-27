# Phase 3 Day 5 - Multi-Symbol Replay Support

## Purpose

Day 5 adds official replay support for the client instrument universe:

- `EURUSD` / EUR/USD
- `XAUUSD` / XAU/USD / Gold
- `NIFTY50` / NIFTY 50

The replay system now normalizes aliases, exposes metadata, generates symbol-aware deterministic historical candles, and can run or compare all client symbols.

## Symbol Normalization

Supported aliases include:

- `EUR/USD`, `EUR-USD`, `eurusd` -> `EURUSD`
- `XAU/USD`, `XAU-USD`, `GOLD`, `gold` -> `XAUUSD`
- `NIFTY 50`, `NIFTY50`, `NIFTY`, `nifty` -> `NIFTY50`

Unsupported symbols return a safe resolution response and are rejected before replay execution.

## Symbol-Specific Replay Data

The deterministic fallback historical loader now uses realistic mock price scales:

- `EURUSD`: around 1.08-1.12
- `XAUUSD`: around 2300-2500
- `NIFTY50`: around 21000-23000

This is research-only synthetic replay data and does not require MT5 or internet access.

## API Routes

- `GET http://127.0.0.1:8000/replay/symbols`
- `GET http://127.0.0.1:8000/replay/symbols/EURUSD`
- `GET http://127.0.0.1:8000/replay/symbols/XAUUSD`
- `GET http://127.0.0.1:8000/replay/symbols/NIFTY50`
- `POST http://127.0.0.1:8000/replay/run-all-client-symbols`
- `GET http://127.0.0.1:8000/replay/compare/client-symbols`

## Safety

Multi-symbol replay remains simulation-only. It does not place broker orders, does not call `mt5.order_send`, does not activate live trading, and preserves `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day5_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```
