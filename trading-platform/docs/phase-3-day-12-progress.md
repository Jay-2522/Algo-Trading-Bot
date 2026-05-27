# Phase 3 Day 12 Progress - TradingView Webhook Foundation

## Purpose

Day 12 adds the first safe ingestion layer for the client TradingView workflow:

TradingView Alerts -> Webhook Handler -> AI Orchestration Preparation -> Broker Routing Later -> MT5 Execution Later.

This day stops at webhook ingestion and normalized signal creation.

## Components

- `webhook_models.py` defines raw payloads, normalized TradingView signals, and webhook event records.
- `tradingview_webhook_auth.py` validates webhook secrets without storing or exposing secret values.
- `tradingview_payload_validator.py` rejects malformed or unsupported payloads.
- `tradingview_signal_normalizer.py` normalizes aliases, actions, timeframes, and broker target metadata.
- `tradingview_signal_classifier.py` classifies `FOREX`, `COMMODITY_CFD`, and `INDIAN_INDEX`.
- `webhook_event_store.py` stores safe in-memory webhook event metadata.
- `webhook_monitoring_service.py` exposes monitoring state and recent events.
- `tradingview_webhook_service.py` coordinates auth, validation, normalization, and storage.

## Supported Symbols

- `EURUSD`
- `XAUUSD`
- `NIFTY50`

Accepted aliases include `EUR/USD`, `XAU/USD`, `GOLD`, `NIFTY`, and `NIFTY 50`.

## Routes

- `POST /webhooks/tradingview`
- `GET /webhooks/status`
- `GET /webhooks/events`
- `GET /webhooks/events/{event_id}`

## Safety

This is webhook ingestion only. It does not route orders, does not call broker APIs, and does not place trades.

- `simulation_only = true`
- `live_execution_enabled = false`
- no `mt5.order_send`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day12_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'webhook' in r.path or 'webhooks' in r.path])"
```
