# Phase 18 Day 7 - Strategy Health Monitoring and Risk Alerts

## Purpose

Phase 18 Day 7 adds read-only strategy health monitoring and automated risk alerts for MT5 demo performance. The system warns when real demo outcomes show degradation, but it never places, closes, or modifies trades.

## Architecture

- `backend/analytics/strategy_health_monitor_service.py`
  - reads closed demo trades from the persistent journal
  - reads drift state from the performance validation engine
  - calculates health components and an overall health score
- `backend/analytics/risk_alert_service.py`
  - reads the same real demo analytics
  - emits deterministic risk alerts when rules are breached
- `backend/api/analytics_routes.py`
  - exposes strategy health and risk alert routes
- `backend/client_analytics/reporting_engine_service.py`
  - builds the Strategy Health V5 report
- `frontend/components/dashboard/DashboardShell.tsx`
  - displays the Strategy Health Panel and Risk Alerts Panel

## Scoring Model

Health components:

- win rate health
- RR health
- PnL health
- drawdown health
- execution quality health
- drift health

The service averages component scores into `health_score` from 0 to 100.

Classifications:

- `EXCELLENT`
- `GOOD`
- `WATCHLIST`
- `DEGRADED`
- `CRITICAL`

If there are not enough closed demo trades, the service returns `INSUFFICIENT_DATA`.

## Alert Rules

The risk alert engine detects:

- consecutive losses
- win rate deterioration
- drawdown threshold breach
- strategy drift escalation
- excessive trade frequency
- negative expectancy

Alert severities:

- `INFO`
- `WARNING`
- `HIGH`
- `CRITICAL`

Each alert includes an ID, type, severity, reason, recommendation, and timestamp.

## Dashboard Integration

The Strategy Health Panel displays:

- Health Score
- Health Status
- Win Rate Health
- RR Health
- Drift Health
- Drawdown Health

The Risk Alerts Panel displays active alert severity and recommendations. If there are no active alerts, it shows: `No active strategy alerts.`

## Reporting V5

The Strategy Health V5 report includes:

- overall health score
- health trend
- active alerts
- drift status
- drawdown status
- recommendations

The report returns `INSUFFICIENT_DATA` when the journal does not contain enough closed demo trades.

## Safety Restrictions

- No order placement.
- No order closing.
- No MT5 trade submission.
- No live trading enablement.
- No broker execution enablement.
- No fake trades.
- No fake PnL.

All monitoring and alert outputs are derived from persistent journal records and analytics services only.
