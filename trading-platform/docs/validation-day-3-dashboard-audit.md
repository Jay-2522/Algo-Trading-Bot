# Validation Day 3 Dashboard Audit

Validation Day 3 focuses on dashboard integrity, visible numbers, empty states, and frontend/backend consistency. This is validation only: no broker integrations, live execution, or strategy changes are introduced.

## Main Dashboard Metric Audit

| Metric | Source endpoint | Data source | Classification |
|---|---|---|---|
| Simulated Balance | `/portfolio/exposure` | Simulated portfolio exposure summary | demo / placeholder |
| Simulated Equity | `/portfolio/exposure` | Simulated portfolio exposure summary | demo / placeholder |
| Demo P&L | `/trade-journal/recent?limit=8`, `/portfolio/pnl-summary` | Completed demo journal records only | derived / demo |
| AI Signals | `/webhooks/events?limit=4` | Analysis webhook events | demo / analysis |
| Trade History | `/trade-journal/recent?limit=8` | Completed non-legacy demo journal records | demo |
| Demo Performance | `/trade-journal/overall-performance` | Completed demo journal records | derived / demo |
| Risk Level | `/trade-journal/risk-analytics` | Trade journal risk analytics | derived |
| Demo Drawdown | `/trade-journal/risk-analytics` | Trade journal risk analytics | derived / demo |
| Demo Exposure | `/trade-journal/risk-analytics` | Trade journal risk analytics | derived / demo |
| Broker Positions | Not displayed on client dashboard | Live broker position data intentionally hidden | hidden |

## Client Analytics Findings

Every displayed metric in the client analytics section originates from backend endpoints:

- `/client-analytics/overview`
- `/client-analytics/symbols`
- `/client-analytics/sessions`
- `/client-analytics/risk`

Displayed values are labeled as demo, derived, or placeholder where appropriate. NIFTY50 remains explicitly marked as pending Indian broker integration and not production execution ready.

## Executive Dashboard Findings

Executive dashboard values originate from backend responses:

- Readiness scores: `/client-analytics/executive/readiness`
- Completion percentage: `/client-analytics/executive/summary`
- Instrument readiness: `/client-analytics/executive/instruments`
- Operational scores: `/client-analytics/executive/system-health`

The completion percentage remains below 100 and is labeled as a derived readiness score.

## Empty State Verification Targets

The dashboard is expected to show honest empty states instead of fake metrics:

- `No reportable demo trades yet`
- `No completed demo trades yet`
- `No copier activity recorded yet`
- `No strategy activity recorded yet`

Browser smoke confirmed these strings are present on `/dashboard`.

## Button Smoke Test Targets

The following dashboard buttons are included in smoke testing:

- Export JSON
- Export CSV
- Print Report
- View buttons in the trade journal when rows exist

Browser smoke confirmed Export JSON, Export CSV, and Print Report remain clickable without console errors. View buttons were not rendered because the trade journal is correctly in the empty state.

## Safety Result

Dashboard integrity validation fails if any checked backend payload reports:

- `live_execution_enabled=true`
- `broker_execution_enabled=true`
- `simulation_only=false`

NIFTY50 execution must remain `execution_allowed=false` and `preview_only=true`.
