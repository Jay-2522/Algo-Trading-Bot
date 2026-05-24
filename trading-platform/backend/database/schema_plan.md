# Database Schema Plan

This schema establishes persistence boundaries for simulated trades, risk, strategy analysis, broker snapshots, market data, and observability.

## Tables

- `trade_records`: simulated or future lifecycle-tracked trade records.
- `execution_log_records`: execution workflow event history.
- `risk_event_records`: risk-permission and protection events.
- `strategy_snapshot_records`: normalized strategy-analysis outputs.
- `mt5_account_snapshot_records`: read-only account observations.
- `market_snapshot_records`: normalized market observations.
- `system_audit_log_records`: operational and audit events.
- `positions`: legacy Day 1 model retained until lifecycle design is finalized.

## Migration Plan

Migrations are intentionally not enabled in this foundation phase. Add Alembic before shared or production deployments.
