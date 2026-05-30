# Phase 7 Day 2 Progress - Forex Factory Economic Calendar Integration Layer

## Summary

Phase 7 Day 2 adds the safe Forex Factory economic calendar integration foundation.

This phase does not scrape Forex Factory, call external APIs, require API keys, or alter broker execution. It adds a manual-ingestion adapter, normalized event model, in-memory calendar store, risk-window engine, API routes, and strategy metadata integration.

## Added

- `backend/news_intelligence/forex_factory_adapter.py`
- `backend/news_intelligence/economic_calendar_store.py`
- `backend/news_intelligence/news_window_engine.py`
- `tests/phase7_day2_verification.py`

## Updated

- `backend/news_intelligence/models.py`
- `backend/news_intelligence/news_service.py`
- `backend/news_intelligence/news_risk_engine.py`
- `backend/news_intelligence/news_readiness_service.py`
- `backend/api/news_routes.py`
- `backend/strategy_engine/xauusd_strategy_engine.py`
- `tests/regression_routes_verification.py`
- `README.md`

## Normalized Models

- `EconomicCalendarEvent`
- `NewsRiskContext`

## Risk Windows

- `EXTREME`: 60 minutes before, 45 minutes after, `BLOCK`
- `HIGH`: 30 minutes before, 30 minutes after, `BLOCK`
- `MEDIUM`: 15 minutes before, 15 minutes after, `REDUCE_RISK`
- `LOW`: no risk window, `ALLOW`

## API

- `POST /news/forex-factory/ingest`
- `GET /news/calendar`
- `GET /news/upcoming-events`
- `GET /news/risk-context`

Existing Phase 7 Day 1 routes remain available.

## Strategy Integration

XAUUSD strategy metadata now includes active news risk state:

- `high_impact_event_active`
- `risk_level`
- `trade_action`
- `reason`
- `upcoming_events_count`

If an active news risk window returns `BLOCK`, the strategy action is forced to `WAIT` and confidence is capped. If it returns `REDUCE_RISK`, analysis remains active but confidence is capped and the reason notes reduced-risk mode.

## Safety

- No live news fetching
- No scraping
- No external API calls
- No order placement
- `execution_allowed=false`
- `simulation_only=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
