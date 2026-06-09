# Phase 18 Day 6 - Historical vs Live Performance Validation

## Purpose

Phase 18 Day 6 adds a read-only validation engine that compares closed MT5 demo outcomes against stored historical backtest expectations. The goal is to detect strategy drift without modifying execution behavior.

## Architecture

- `backend/analytics/performance_validation_service.py` reads:
  - closed demo trades from `PersistentTradeJournalService`
  - stored backtest results from `BacktestStorage`
- `backend/api/analytics_routes.py` exposes validation and drift routes under `/analytics/performance-validation`.
- `backend/client_analytics/reporting_engine_service.py` generates a V4 performance validation report.
- `frontend/components/dashboard/DashboardShell.tsx` displays the DEMO Validation Panel.

The service does not import MT5 and never places, closes, or modifies orders.

## Comparison Methodology

The engine compares historical and live demo metrics:

- win rate
- average RR
- net PnL
- expectancy
- average duration
- average trade frequency

For each metric it returns:

- live value
- historical value
- variance
- percent deviation

If either side lacks enough real data, the response is `INSUFFICIENT_DATA`.

## Drift Classification

Drift score is derived from weighted deviations:

- win rate deviation
- RR deviation
- PnL deviation
- frequency deviation

Classifications:

- `NORMAL`
- `MINOR_DRIFT`
- `MODERATE_DRIFT`
- `MAJOR_DRIFT`

The drift response includes a reason, contributing metrics, and a suggested action.

## Dashboard Integration

The DEMO Validation Panel shows:

- Historical Win Rate
- Live Win Rate
- Historical Avg RR
- Live Avg RR
- Historical Net PnL
- Live Net PnL
- Drift Status
- Confidence Score

The drift status is color-coded. Empty states remain honest and show `INSUFFICIENT_DATA`.

## Reporting V4

The V4 report includes:

- live vs historical comparison
- drift explanation
- confidence summary
- strategy health score

It returns `INSUFFICIENT_DATA` when closed demo trades or historical backtests are missing.

## Safety Restrictions

- No order placement.
- No order closing.
- No MT5 order submission path.
- No live trading enablement.
- No broker execution enablement.
- No fake trades.
- No fake PnL.

All responses include safety flags confirming demo-only, read-only analytics.
