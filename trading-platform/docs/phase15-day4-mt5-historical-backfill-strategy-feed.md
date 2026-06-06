# Phase 15 Day 4 - MT5 Historical Backfill and Strategy Feed

## What Was Built

Phase 15 Day 4 adds a read-only historical candle backfill layer and a strategy-feed adapter for MT5 demo data.

New services:

- `backend/mt5_demo/mt5_historical_backfill_service.py`
- `backend/mt5_demo/mt5_strategy_feed_adapter.py`

New API surfaces:

- `/mt5-demo/history/*`
- `/mt5-demo/strategy-feed/*`

## Supported Symbols

- `EURUSD`
- `XAUUSD`

## Supported Timeframes

Historical backfill:

- `M5`
- `M15`
- `H1`
- `H4`
- `D1`

Strategy feed:

- `M5`
- `H1`
- `H4`

## Candle Validation Rules

Candles are normalized into:

- `time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `source=MT5_DEMO`

Validation checks:

- Prices must be positive.
- High must be greater than or equal to open and close.
- Low must be less than or equal to open and close.
- High must not be below low.
- Missing or malformed candles are rejected from normalized output.

## Gap And Staleness Handling

Gap detection compares adjacent candle timestamps against the expected timeframe interval.

Staleness is flagged when the latest candle is older than three expected timeframe intervals. During closed market hours, candles may be stale while still valid historical data.

## Strategy Feed Behavior

The strategy feed adapter prepares historical candles for strategy consumers without modifying strategy logic.

It returns:

- Full feed: `M5`, `H1`, `H4`
- HTF context: `H1`, `H4`
- LTF context: `M5`

The adapter may return `feed_ready=false` when MT5 data is unavailable. It does not fake candles, force BUY/SELL signals, or change confidence scores.

## Safety Restrictions

All responses preserve:

- `simulation_only=true`
- `execution_allowed=false`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

## No-Execution Statement

This phase performs market data and strategy feed validation only. It does not place trades, add `mt5.order_send`, enable broker execution, enable live trading, modify strategy logic, or modify risk logic.
