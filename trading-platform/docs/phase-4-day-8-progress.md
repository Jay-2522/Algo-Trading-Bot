# Phase 4 Day 8 - Portfolio & Account Analytics Dashboard

## Scope

Phase 4 Day 8 adds portfolio and account analytics to the VPS dashboard. This is a display and simulation analytics layer only. It summarizes broker demo accounts, simulated balances, account readiness, symbol exposure, placeholder P&L, and the NIFTY50 conditional state.

## Backend

- Added `backend/portfolio/`.
- Added portfolio account, exposure, and overview models.
- Added account analytics and exposure summary services.
- Added `/portfolio/status`, `/portfolio/overview`, `/portfolio/accounts`, `/portfolio/exposure`, and `/portfolio/pnl-summary`.

## Frontend

- Added `PortfolioOverviewPanel`.
- Added `AccountAnalyticsPanel`.
- Added `ExposureSummaryPanel`.
- Added `SimulatedPnlPanel`.
- Wired portfolio endpoints into `frontend/lib/dashboard-api.ts`.

## Safety

- Portfolio analytics are simulation-only.
- Balances and P&L are simulated placeholders.
- NIFTY50 remains blocked/conditional until Indian broker integration.
- Live and broker execution remain disabled.

## Verification

Run:

```bash
python tests/regression_routes_verification.py
python tests/phase4_day8_verification.py
cd frontend
npm run build
```
