# Phase 7 Day 4 Progress - DXY & US10Y Macro Bias Engine

## Summary

Phase 7 Day 4 adds a manual DXY and US10Y macro bias engine for XAUUSD.

This is macro analysis only. The system accepts manually supplied DXY and US10Y values, builds direction and momentum context, derives gold macro bias, evaluates alignment with XAUUSD strategy direction, and adjusts confluence confidence.

## Added

- `backend/news_intelligence/macro_models.py`
- `backend/news_intelligence/macro_bias_engine.py`
- `backend/news_intelligence/macro_context_store.py`
- `backend/news_intelligence/macro_strategy_filter.py`
- `tests/phase7_day4_verification.py`

## Updated

- `backend/news_intelligence/news_service.py`
- `backend/api/news_routes.py`
- `backend/strategy_engine/confluence_score_engine.py`
- `backend/strategy_engine/xauusd_strategy_engine.py`
- `backend/strategy_engine/signal_reason_builder.py`
- `tests/regression_routes_verification.py`
- `README.md`

## Macro Rules

- DXY down and US10Y down: bullish support for gold.
- DXY up and US10Y up: bearish pressure on gold.
- DXY and US10Y mixed: mixed macro context and reduced confidence.
- Missing data: unknown macro bias.

## API

- `GET /news/macro/status`
- `POST /news/macro/context`
- `GET /news/macro/context`
- `GET /news/macro/xauusd-bias`
- `POST /news/macro/xauusd-bias/evaluate`

## Strategy Integration

XAUUSD strategy metadata now includes:

- `macro_context`
- `macro_alignment`
- `macro_confidence_adjustment`

Aligned macro context can add confidence. Conflicting macro context reduces confidence and degrades trade quality by one level.

## Safety

- No external API calls
- No scraping
- No execution
- No MT5 order placement
- `execution_allowed=false`
- `simulation_only=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
