# Dashboard Visible Number Audit

This audit maps visible dashboard numbers to their source endpoint and data classification. The dashboard must not present any value as live broker performance unless live execution has been explicitly approved, which is not enabled.

## Classification Key

- `real`: System state or route data returned by the backend.
- `demo`: Recorded demo/simulation activity only.
- `derived`: Computed from backend readiness, risk, analytics, or demo records.
- `placeholder`: Honest empty/default value shown until recorded activity exists.
- `hidden`: Intentionally not displayed to prevent confusion with live broker data.

## Main Trader Dashboard

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Bot Status | `/dashboard/status` | real | System status text only. |
| Live Trading | `/dashboard/status` | real safety flag | Shows Enabled/Disabled. Must remain disabled. |
| Connection | `/dashboard/status` | derived | Derived from dashboard readiness/loading state. |
| Simulated Balance | `/portfolio/exposure` | demo/placeholder | Label says simulated. Not live broker balance. |
| Simulated Equity | `/portfolio/exposure` | demo/placeholder | Label says simulated. Not live broker equity. |
| Demo P&L | `/trade-journal/recent?limit=8`, `/portfolio/pnl-summary` | derived demo | Uses completed non-legacy demo journal entries only. |
| Broker Positions | none shown to client | hidden | Live broker position values are hidden on the client dashboard. |
| AI Signals | `/webhooks/events?limit=4` | demo/analysis | Analysis event count, not executed trades. |
| Demo Trades / Trade History | `/trade-journal/recent?limit=8` | demo | Empty state until completed demo records exist. Legacy test records are filtered. |
| Demo Performance | `/trade-journal/overall-performance` | demo/derived | Hidden behind empty state until completed demo records exist. |
| Risk Level, Demo Drawdown, Demo Exposure | `/trade-journal/risk-analytics` | derived demo | Labels identify demo/derived risk context. |

## Client Analytics

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Demo Signals | `/client-analytics/overview` | demo/analysis | Count of recorded strategy ideas. |
| Demo Executions | `/client-analytics/overview` | demo | Empty-state copy if zero. |
| Demo Copy Batches | `/client-analytics/overview` | demo | Recorded copier batches only. |
| Risk Blocks | `/client-analytics/overview` | derived | Risk engine event count. |
| News Blocks | `/client-analytics/overview` | derived | News filter event count. |
| Demo Win Rate | `/client-analytics/overview` | derived demo | Calculated from completed demo P&L only. |
| Demo Net P&L | `/client-analytics/overview` | demo | Recorded demo P&L only. |
| Demo Max Drawdown | `/client-analytics/overview` | derived demo | Recorded demo drawdown only. |
| Symbol metrics | `/client-analytics/symbols` | demo/placeholder | NIFTY50 explicitly labeled placeholder pending broker integration. |
| Session metrics | `/client-analytics/sessions` | demo/derived | Labels say demo signals, demo P&L, demo confidence. |
| Risk analytics | `/client-analytics/risk` | derived | Protection-decision counts only. |

## Account Analytics

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Demo Accounts, Demo Copiers | `/client-analytics/accounts` | demo/placeholder | Count of configured demo analytics accounts. |
| Sync Status, Last Sync | `/client-analytics/accounts/sync-status` | demo/derived | Copier sync metadata only. |
| Demo Executions, Copied Demo Trades | `/client-analytics/accounts` | demo | Recorded demo activity only. |
| Demo Win Rate, Demo Net P&L, Demo Drawdown | `/client-analytics/accounts` | demo/derived | Labels identify demo metrics. |
| Live | `/client-analytics/accounts` | real safety flag | Must show disabled. |

## Strategy Intelligence

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Total Strategies | `/client-analytics/strategy/overview` | real/derived | Number of supported strategy analytics entries. |
| Avg Analysis Confidence | `/client-analytics/strategy/overview` | derived | Strategy-analysis metric, not broker result. |
| Avg Demo Risk/Execution Efficiency | `/client-analytics/strategy/overview` | derived demo | Demo analytics only. |
| Strategy comparison grid | `/client-analytics/strategy/performance` | derived demo/placeholder | NIFTY50 shows SMC intelligence ready, not production ready. |
| Session efficiency | `/client-analytics/strategy/session-efficiency` | derived demo | Labels identify demo signals and derived score. |
| Comparative ranking | `/client-analytics/strategy/rankings` | derived | Derived strategy score, not account return. |

## Reports

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Daily report count | `/client-analytics/reports/daily` | demo/analysis | Demo signals in current report. |
| Weekly report count | `/client-analytics/reports/weekly` | demo | Demo executions recorded. |
| Symbol report P&L | `/client-analytics/reports/symbol/{symbol}` | demo | Recorded demo P&L only. |
| Risk report blocks | `/client-analytics/reports/risk` | derived | Risk block count only. |

## Executive Dashboard

| Visible metric | Source endpoint | Classification | Current handling |
|---|---|---:|---|
| Overall completion percentage | `/client-analytics/executive/summary` | derived | Labeled derived readiness score. Must remain below 100. |
| System readiness scores | `/client-analytics/executive/readiness` | derived | Labeled readiness score. |
| System health scores | `/client-analytics/executive/system-health` | derived | Labeled derived operational scores. |
| Instrument readiness | `/client-analytics/executive/instruments` | derived | NIFTY50 remains not ready for production execution. |

## Removed Or Hidden

- Legacy fake `Recent Trades` card language was replaced by demo trade empty state.
- Legacy `Trading Results` was replaced by `Demo Performance`.
- Fake `+$900`, `+$100`, `100% win rate`, and fake XAUUSD BUY history are not displayed.
- Live broker positions from `/mt5/positions` are not displayed on the client dashboard.
- Empty `POST /trade-journal/add-test-entry` no longer creates a default fake XAUUSD BUY record.
