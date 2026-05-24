# Day 8 Progress

## AI Engine Overview

Day 8 introduces an advisory AI Decision & Signal Scoring Layer. It evaluates setup quality using structured rules and existing platform controls; it does not submit orders or authorize live execution.

## Signal Scoring Architecture

The `SignalScorer` produces normalized `0-100` quality measurements for:

- Trend alignment
- Liquidity context
- Structure confirmation
- Trading session quality
- Volatility suitability
- Spread quality
- Risk status

## Confidence Scoring

`ConfidenceEngine` applies weighted scoring:

- Trend: `20%`
- Liquidity: `15%`
- Structure: `20%`
- Session: `10%`
- Volatility: `10%`
- Spread: `10%`
- Risk: `15%`

Aligned setup factors receive a small reward, while weak volatility, spread, or risk quality reduces confidence.

## Market Regime Classification

`RegimeClassifier` assigns one of:

- `TRENDING`
- `RANGING`
- `VOLATILE`
- `LOW_LIQUIDITY`
- `NEWS_RISK`

Unsafe regimes prevent advisory approval even if individual factors appear attractive.

## Why AI Does Not Trade

The AI layer produces `BUY`, `SELL`, `WAIT`, or `AVOID` quality decisions for review and future controlled workflows. It does not communicate with a broker, submit orders, or enable live execution. Risk controls override advisory approval.

## Persistence Integration

Requests for an AI decision or full analysis persist:

- Decision and explanation details in system audit logs.
- Signal score, regime, confidence, and decision metadata in strategy snapshot records.

This creates inspectable decision history for later analytics and training research.

## API Routes Added

- `GET /ai/status`
- `GET /ai/regime/{symbol}`
- `GET /ai/signal-score/{symbol}`
- `GET /ai/decision/{symbol}`
- `GET /ai/full-analysis/{symbol}`
- `GET /ai/confidence/{symbol}`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/day8_verification.py
```

Testing requires no external AI API, GPU, internet connection, or live MT5 terminal.

## Pending Day 9 Work

- Feed persisted strategy and market snapshots into replayable analysis.
- Add explicit input schemas for enriched multi-timeframe AI context.
- Add database queries for decision-history review.
- Add authenticated human approval workflow before any future execution consideration.

