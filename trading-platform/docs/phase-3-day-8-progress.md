# Phase 3 Day 8 - Broker Demo Observation Mode

## Purpose

Day 8 adds safe broker demo observation mode. The platform can now observe broker/demo symbols in read-only mode when MT5 is available, or return deterministic simulation fallback snapshots when broker data cannot be reached.

## Observation Scope

Supported broker metadata:

- STARTRADER
- FxPro
- Vantage

Supported client instruments:

- EURUSD
- XAUUSD
- NIFTY50

NIFTY50 remains conservative and unavailable unless broker terminal observation confirms a real symbol.

## Snapshot Logic

`BrokerSymbolSnapshotter` attempts:

1. broker symbol mapping lookup
2. read-only MT5 connection
3. read-only `symbol_info`
4. read-only `symbol_info_tick`
5. safe fallback snapshot if MT5 is unavailable

Fallback snapshots are marked `SIMULATION_FALLBACK`; missing or unsupported symbols are marked `UNAVAILABLE`.

## API Routes

- `GET http://127.0.0.1:8000/brokers/observation/status`
- `GET http://127.0.0.1:8000/brokers/observation/all`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/observation`
- `GET http://127.0.0.1:8000/brokers/FXPRO/observation`
- `GET http://127.0.0.1:8000/brokers/VANTAGE/observation`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/observation/EURUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/observation/XAUUSD`
- `GET http://127.0.0.1:8000/brokers/STARTRADER/observation/NIFTY50`

## Safety

Observation mode is read-only. It does not call `mt5.order_send`, does not build order payloads, does not place trades, and preserves `simulation_only = true` and `live_execution_enabled = false`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day7_verification.py
python tests/phase3_day8_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```
