# Phase 14 Day 2 MT5 Demo Integration

Phase 14 Day 2 adds read-only MT5 demo connectivity validation. It does not enable live trading, broker execution, or order placement.

## MT5 Installation Requirements

- Install MetaTrader 5 on the Windows VPS or local demo validation machine.
- Install the Python `MetaTrader5` package from `requirements.txt`.
- Keep MT5 terminal running during connectivity checks.
- Use only demo account credentials.
- Do not store production credentials in source control.

## Demo Account Requirements

- Account must be a demo account.
- Login must be verified manually in the MT5 terminal.
- Server name must match the demo broker server.
- Market data must be visible inside MT5.
- AutoTrading should remain governed by demo-only policy and must not imply broker execution is enabled in the platform.

## Supported Symbols For Day 2

The read-only market-watch check covers:

- `XAUUSD`
- `EURUSD`

For each symbol the service reports:

- symbol existence
- visibility
- bid
- ask
- spread
- execution flags locked false

## Connectivity Workflow

1. Start MT5 terminal.
2. Log in to a demo account.
3. Start backend.
4. Call:

```text
GET /mt5-demo/status
GET /mt5-demo/account
GET /mt5-demo/symbols
GET /mt5-demo/health
GET /mt5-demo/market-watch
```

5. Confirm the account is demo-only before any later demo execution workflow is considered.

## Safety Restrictions

The MT5 demo routes are read-only.

Explicitly blocked actions:

```text
POST /mt5-demo/order-send
POST /mt5-demo/position-open
POST /mt5-demo/market-buy
POST /mt5-demo/market-sell
```

Each returns:

```json
{
  "allowed": false,
  "reason": "PHASE_14_DEMO_ONLY"
}
```

Required flags:

- `simulation_only=true`
- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

## Known Limitations

- If the MetaTrader5 Python package is missing, endpoints return safe `NOT_CONNECTED` style payloads.
- If the terminal is not running, endpoints return safe unavailable states.
- If a non-demo account is detected, `account_connected` remains false for platform readiness purposes and warnings are returned.
- No order placement is implemented in this layer.

## Phase Boundary

Day 2 is connectivity validation only. Do not proceed to demo execution until later Phase 14 readiness gates explicitly authorize it.
