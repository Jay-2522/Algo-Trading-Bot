# Phase 20 Day 1 Strategy Audit

## Strategy Components Discovered

- Liquidity and sweep detection:
  - `backend/strategy_engine/liquidity_detector.py`
  - `backend/institutional_intelligence/liquidity_sweep_detector.py`
  - `backend/institutional_intelligence/sweep_context_builder.py`
- Structure detection:
  - BOS and CHOCH routes are exposed through institutional structure shift endpoints.
  - `backend/institutional_intelligence/structure_shift_validator.py`
  - `backend/institutional_intelligence/structure_shift_strength_scorer.py`
- Fair value gaps:
  - `backend/institutional_intelligence/fair_value_gap_*`
  - FVG routes under `/institutional/fvg/*`
- Order blocks:
  - `backend/institutional_intelligence/order_block_*`
  - order block routes under `/institutional/order-blocks/*`
- Session filters and killzones:
  - `backend/strategy_engine/session_manager.py`
  - `backend/institutional_intelligence/session_*`
  - routes under `/institutional/session/*`
- Regime and confidence:
  - `backend/ai_engine/regime_classifier.py`
  - `backend/ai_engine/confidence_engine.py`
  - `backend/ai_engine/signal_scorer.py`
- MT5 strategy consumption:
  - `backend/mt5_demo/mt5_strategy_feed_adapter.py`
  - `backend/mt5_demo/mt5_strategy_consumption_service.py`
- Risk qualification and execution gate:
  - `backend/mt5_demo/mt5_risk_qualification_service.py`
  - `backend/mt5_demo/mt5_execution_gate_validation_service.py`

## Current Routes

- `/ai/regime/{symbol}`
- `/ai/confidence/{symbol}`
- `/strategy/signals`
- `/strategy/confluence/xauusd`
- `/strategy/eurusd/confluence`
- `/institutional/sweeps/{symbol}`
- `/institutional/fvg/{symbol}`
- `/institutional/order-blocks/{symbol}`
- `/institutional/structure-shift/bos/{symbol}`
- `/institutional/structure-shift/choch/{symbol}`
- `/institutional/session/{symbol}`
- `/mt5-demo/strategy-feed/{symbol}`
- `/mt5-demo/strategy-consumption/{symbol}/latest`
- `/mt5-demo/risk-qualification/{symbol}/latest`
- `/mt5-demo/execution-gate/{symbol}/latest`
- `/mt5-demo/pipeline-summary`

## Available Outputs

- Strategy action where the existing strategy engine explicitly returns BUY, SELL, WAIT, or NONE.
- Confidence when the existing strategy output provides it.
- Feed readiness, strategy consumption status, warnings, and raw signal payloads.
- Risk qualification result and execution gate status.
- Institutional component contexts for sweeps, FVG, order blocks, structure shifts, and sessions.

## Missing Outputs

- A single canonical client-facing strategy signal object did not exist before this phase.
- Component booleans were not uniformly normalized into `liquidity_sweep`, `bos`, `choch`, `fvg`, `order_block`, and `session_valid`.
- Signal history persistence for client-facing signals did not exist.
- NIFTY50 strategy signal output remains pending Indian market integration.

## Safety Notes

No strategy logic was modified during this audit. Existing strategy services remain read-only for this phase, and execution remains guarded and disabled outside the proven demo sender.
