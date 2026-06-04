# Validation Day 2 Schema Report

Validation Day 2 adds a deep endpoint schema and data consistency check. It does not add product features, change UI design, enable live trading, or enable broker execution.

## Endpoint Groups Tested

- Core: `/health`, `/status`
- Deployment: `/deployment/status`, `/deployment/readiness`, `/production-readiness/status`
- Monitoring: `/monitoring/status`, `/monitoring/health`
- Security: `/security/status`, `/security/secrets-audit`
- Strategy and execution bridge status routes
- NIFTY50 status, readiness, strategy, risk, and execution status
- Client analytics overview, symbols, sessions, risk, accounts, strategy, and executive routes
- Client reports: status, daily, weekly, JSON export, and CSV export

## Safety Schema Result

The validator fails if any checked endpoint returns:

- `live_execution_enabled=true`
- `broker_execution_enabled=true`
- `execution_allowed=true`

Execution endpoints are required to explicitly report `execution_allowed=false`. NIFTY50 execution must also report `preview_only=true` and `execution_ready=false`.

## Analytics Schema Result

The validator checks that:

- Analytics overview metrics are numeric.
- XAUUSD, EURUSD, and NIFTY50 appear in symbol analytics.
- NIFTY50 is not marked fully production-ready.
- Empty states remain valid and do not require fake profits.

## Reporting Schema Result

Daily and weekly reports must include:

- `report_id`
- `report_type`
- `period`
- `summary`
- `simulation_only`
- `live_execution_enabled=false`
- `broker_execution_enabled=false`

CSV export must return text with headers and must not crash when analytics data is empty.

## Executive Completion Result

Executive completion must remain less than or equal to 99 and must not report 100 before broker validation and VPS deployment. Pending items must include:

- Demo Broker Validation
- VPS Deployment
- Extended Stability Testing

## Known Warnings

- This validation uses FastAPI `TestClient`; browser rendering validation is reserved for a later validation day.
- Source-level fake-data scanning is covered by Validation Day 1.
- NIFTY50 remains analytics-integrated only until broker demo validation and VPS validation are complete.
