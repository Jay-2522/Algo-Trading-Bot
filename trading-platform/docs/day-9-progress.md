# Day 9 Progress

## News Engine Overview

Day 9 introduces a News Intelligence Engine foundation for macro-event risk filtering. The engine uses dynamic sample calendar events while external providers are deferred to a later integration phase.

## CPI, NFP, FOMC, And Fed Speeches

The mock economic calendar includes future UTC events for:

- US CPI
- US NFP
- FOMC rate decisions
- Federal Reserve speeches

For `XAUUSD`, USD macro events classified as gold-sensitive receive focused risk evaluation.

## Blackout Window Logic

- `HIGH` impact events create a no-trade window from 30 minutes before to 30 minutes after release.
- `MEDIUM` impact events raise caution but do not block activity on their own.
- `LOW` impact events do not create blackout windows.

The sample CPI event is generated within the active blackout window so the foundation can be tested deterministically.

## Macro Risk Scoring

`MacroRiskScorer` combines event severity, event-implied volatility, and placeholder DXY and bond-yield factors. An active high-impact blackout produces `BLOCKED`; scheduled high-impact events outside a blackout produce elevated risk.

## External Feed Placeholders

Future integrations may source normalized events from providers such as Forex Factory, Investing.com, or Financial Juice. Day 9 does not require network access or third-party credentials.

## Why News Can Block Trading

Scheduled macro releases can cause gaps, spread expansion, slippage, and abrupt price repricing. The news engine is therefore a permission filter only: it can recommend pausing trading, but it does not submit or manage orders.

## Persistence Integration

Risk-status and allow-trading API requests save macro-risk decisions as system audit logs when the persistence layer is available.

## API Routes Added

- `GET /news/status`
- `GET /news/upcoming`
- `GET /news/high-impact`
- `GET /news/risk-status/{symbol}`
- `GET /news/allow-trading/{symbol}`
- `GET /news/blackout-windows`
- `GET /news/macro-score/{symbol}`

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/day9_verification.py
```

## Pending Day 10 Work

- Integrate news-risk status into the advisory AI decision package.
- Define external feed adapter contracts and data normalization.
- Persist normalized economic events separately from risk audit outcomes.
- Add operational scheduling and refresh controls.

