# Phase 14 Day 5 - NIFTY50 Demo Signal Validation

## Scope

Phase 14 Day 5 validates the NIFTY50 demo signal path across market data, strategy intelligence, risk qualification, analytics visibility, and execution preview safety.

This phase is validation only. It does not place broker orders, connect to real Indian broker APIs, store credentials, or enable live execution.

## Validation Flow

1. Check NIFTY50 market-data service status and health.
2. If no NIFTY50 candles exist, inject one manual validation candle.
3. Mark the injected candle as `validation_sample=true` in the validation result and `placeholder=true` in the candle store.
4. Run the existing NIFTY50 strategy snapshot builder.
5. Run the existing NIFTY50 risk engine.
6. Run trade qualification.
7. Create an execution intent and order preview through the existing preview-only bridge.
8. Verify analytics and executive dashboard include NIFTY50 but do not mark it live-ready.

## Validation Sample Policy

The validation sample is not live market data and must not be interpreted as broker data or a trading recommendation.

Sample values are used only when the backend has no NIFTY50 candles available:

- Symbol: `NIFTY50`
- Timeframe: `M15`
- Placeholder: `true`
- Validation marker: `validation_sample=true`

## API Routes

- `GET /demo-validation/nifty50/status`
- `POST /demo-validation/nifty50/run`
- `GET /demo-validation/nifty50/latest`
- `GET /demo-validation/nifty50/history`

Existing demo validation routes remain available for:

- `XAUUSD`
- `EURUSD`

## Safety Locks

NIFTY50 remains analytics and preview only:

- `preview_only=true`
- `execution_allowed=false`
- `simulation_only=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

No broker API calls are introduced in this phase. No MT5 order path is added.

## Expected Outcomes

The validation run may return `WARNING` when the risk engine rejects the candidate or the strategy remains neutral. That is acceptable because this phase validates flow safety and readiness, not trade eligibility.

A passing validation means:

- NIFTY50 market data path is reachable.
- NIFTY50 strategy path is reachable.
- NIFTY50 risk path is reachable.
- NIFTY50 execution bridge remains preview-only.
- NIFTY50 analytics integration is visible.
- XAUUSD and EURUSD demo validation routes remain preserved.
