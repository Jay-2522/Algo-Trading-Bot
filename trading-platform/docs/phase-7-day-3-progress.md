# Phase 7 Day 3 Progress - News Risk Filter & Strategy Blocking Engine

## Summary

Phase 7 Day 3 adds an active News Risk Filter for XAUUSD strategy analysis.

The filter converts normalized calendar risk context into a strategy gating decision. It can block confidence and action during high-impact or extreme USD news windows, reduce confidence before medium-risk events, and pause during post-news stabilization.

## Added

- `backend/news_intelligence/news_filter_models.py`
- `backend/news_intelligence/news_strategy_filter.py`
- `backend/news_intelligence/news_block_reason_builder.py`
- `tests/phase7_day3_verification.py`

## Updated

- `backend/news_intelligence/news_service.py`
- `backend/api/news_routes.py`
- `backend/strategy_engine/confluence_score_engine.py`
- `backend/strategy_engine/xauusd_strategy_engine.py`
- `backend/strategy_engine/signal_reason_builder.py`
- `tests/regression_routes_verification.py`
- `README.md`

## Filter Behavior

- Active `EXTREME` events block with confidence cap `0`.
- Active `HIGH` events block with confidence cap `20`.
- Upcoming `EXTREME` USD events within 60 minutes block with confidence cap `0`.
- Upcoming `HIGH` USD events within 30 minutes block with confidence cap `20`.
- Upcoming `MEDIUM` events within 15 minutes reduce confidence by `20`.
- Post-event stabilization windows block with `WAIT_FOR_STABILIZATION` and confidence cap `30`.
- No relevant event allows analysis normally.

## API

- `GET /news/filter/status`
- `POST /news/filter/evaluate`
- `GET /news/filter/current/xauusd`

## Strategy Integration

The XAUUSD strategy engine now:

- Builds news risk context from the calendar store.
- Runs the `NewsStrategyFilter`.
- Applies the filter decision to confluence confidence.
- Forces `WAIT` when the news filter blocks.
- Includes `news_filter_decision` in signal metadata.
- Adds client and technical news explanations.

## Safety

- No execution
- No MT5 order placement
- No scraping
- No external API calls
- `execution_allowed=false`
- `simulation_only=true`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`
