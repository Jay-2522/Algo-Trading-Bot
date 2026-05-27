# Phase 3 Day 13 Progress - Webhook Signal Orchestration Bridge

## Purpose

Day 13 bridges normalized TradingView webhook signals into the AI orchestration preparation layer.

Flow:

TradingView Alert -> Webhook Handler -> Signal Validation -> Institutional Context Check -> Risk Gate -> Broker Routing Preview -> Simulation Decision.

## Components

- `webhook_orchestration_models.py` defines orchestration decisions, broker routing previews, institutional context checks, and risk gate results.
- `webhook_institutional_context_checker.py` compares the signal with available institutional dashboard context.
- `webhook_risk_gate.py` blocks invalid, low-confidence, or unsafe signals.
- `webhook_broker_routing_preview.py` maps Forex/CFD signals to STARTRADER, FXPRO, and VANTAGE while keeping NIFTY50 conditional.
- `webhook_orchestration_engine.py` generates simulation-only decisions.
- `webhook_orchestration_store.py` stores decisions in memory.
- `webhook_orchestration_service.py` exposes orchestration status and decision retrieval.

## Decision Values

- `SIMULATION_ACCEPTED`
- `WAIT_FOR_CONFIRMATION`
- `REJECTED`
- `BLOCKED`
- `INVALID`

## Routes

- `GET /webhooks/orchestration/status`
- `GET /webhooks/orchestration/decisions`
- `GET /webhooks/orchestration/decisions/{decision_id}`
- `POST /webhooks/orchestration/test`

`POST /webhooks/tradingview` remains backward-compatible and can store an orchestration preview when `orchestrate: true` is included.

## Safety

This layer creates decisions only. It does not execute orders, place broker trades, or call MT5 order functions.

- `simulation_only = true`
- `live_execution_enabled = false`
- no `mt5.order_send`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day13_verification.py
```
