# Database Schema Plan

This Day 1 schema establishes the persistence boundaries for future trading, risk, market data, and observability systems.

## Tables

- `trades`: completed or lifecycle-tracked trade records, including symbol, side, size, prices, PnL, broker, and strategy attribution.
- `positions`: open exposure view by symbol and asset class, including average price, current price, unrealized PnL, and status.
- `strategy_logs`: strategy decision audit trail for future signal generation and AI-assisted analysis.
- `risk_events`: risk alerts and controls, including severity, thresholds, exposure, and action taken.
- `market_snapshots`: normalized market data snapshots from MT5, forex feeds, gold feeds, and Indian market data providers.
- `system_logs`: application-level observability records for services, trace IDs, and structured context.

## Migration Plan

Migrations are intentionally not enabled on Day 1. Add Alembic once database connectivity and deployment topology are finalized.

