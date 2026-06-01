# AI-Assisted Algorithmic Trading Platform

Professional modular algorithmic trading platform foundation covering Forex, XAUUSD, and Indian stock markets.

Phase 1 of the backend foundation is complete, and Phase 2 has begun with institutional market-structure intelligence. The system includes analysis, risk, news, orchestration, persistence, offline backtesting, simulated trade journaling, streaming, controlled background monitoring, integration health auditing, and SMC/ICT-style observation. It does not implement real order execution.

## Architecture Overview

- `backend/strategy_engine`: future strategy orchestration and signal lifecycle.
- `backend/execution_engine`: simulation-only order validation, risk-gated fills, and execution event logging.
- `backend/ai_engine`: rule-based advisory scoring, regime classification, confidence, and persisted trade-quality decisions.
- `backend/risk_engine`: risk limits, sizing calculations, guardrails, and emergency permission controls.
- `backend/news_engine`: macro-event risk filtering, blackout windows, and auditable news-risk decisions.
- `backend/market_data`: read-only MT5 market data collection, validation, candles, and snapshots.
- `backend/analytics`: future performance reporting and research analytics.
- `backend/broker_integrations`: broker adapters, including MT5 and Indian broker foundations.
- `backend/websocket`: future real-time dashboard transport.
- `backend/database`: SQLAlchemy persistence, repositories, SQLite fallback, and PostgreSQL-ready records.
- `backend/backtesting`: deterministic historical replay, simulated PnL accounting, performance analysis, and stored reports.
- `backend/streaming`: read-only market tick streaming, WebSocket subscribers, and simulated fallback updates.
- `backend/trading_loop`: controlled, rate-limited simulation-only orchestration scheduling.
- `backend/trade_journal`: analytics-only journal records, performance reporting, drawdown, exposure, and risk alerts.
- `backend/system_health`: integration readiness, source safety scanning, route auditing, runtime reporting, and Phase 1 reporting.
- `backend/institutional_intelligence`: SMC/ICT-style market analysis, simulated setup lifecycle, institutional reasoning and analytics, and unified backend dashboard context reporting.
- `backend/config`: environment-driven settings.
- `backend/utils`: shared logging and utility code.
- `frontend`: reserved dashboard and admin surfaces.
- `deployment`: reserved Docker, Nginx, and operational scripts.
- `docs`: project documentation.
- `tests`: verification and future automated tests.
- `logs`: runtime log location.

## Setup

```powershell
cd "C:\Users\Swati Natti\Documents\Algo Trading Bot\trading-platform"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

The application uses local SQLite persistence by default. Update `.env` to use PostgreSQL, Redis, and optional MT5 credentials where appropriate.

## Run Backend

```powershell
uvicorn backend.main:app --reload
```

Expected health endpoints:

- `GET http://127.0.0.1:8000/health`
- `GET http://127.0.0.1:8000/status`

Market Data API examples:

- `GET http://127.0.0.1:8000/market-data/timeframes`
- `GET http://127.0.0.1:8000/market-data/tick/XAUUSD`
- `GET http://127.0.0.1:8000/market-data/candles/XAUUSD?timeframe=M15&count=100`
- `GET http://127.0.0.1:8000/market-data/snapshot/XAUUSD`

Strategy API examples:

- `GET http://127.0.0.1:8000/strategy/trend/XAUUSD`
- `GET http://127.0.0.1:8000/strategy/liquidity/XAUUSD`
- `GET http://127.0.0.1:8000/strategy/structure/XAUUSD`
- `GET http://127.0.0.1:8000/strategy/order-block/xauusd`
- `GET http://127.0.0.1:8000/strategy/regime/xauusd`
- `GET http://127.0.0.1:8000/strategy/confluence/xauusd`
- `GET http://127.0.0.1:8000/strategy/analyze/eurusd`
- `GET http://127.0.0.1:8000/strategy/eurusd/session-context`
- `GET http://127.0.0.1:8000/strategy/eurusd/indicator-context`
- `GET http://127.0.0.1:8000/strategy/eurusd/liquidity`
- `GET http://127.0.0.1:8000/strategy/eurusd/structure`
- `GET http://127.0.0.1:8000/strategy/eurusd/fvg`
- `GET http://127.0.0.1:8000/strategy/eurusd/order-block`
- `GET http://127.0.0.1:8000/strategy/eurusd/regime`
- `GET http://127.0.0.1:8000/strategy/eurusd/confluence`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/status`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/evaluate-signal`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/preview-signal`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/evaluate-and-preview`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/xauusd/latest`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/eurusd/latest`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/decisions`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/demo-approval/status`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/demo-approval/approve`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/demo-approval/approvals`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/demo-approval/history`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/demo-approval/candidates`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/final-demo-execution/status`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/final-demo-execution/execute`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/final-demo-execution/executions`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/e2e/status`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/e2e/mock-eurusd-demo`
- `POST http://127.0.0.1:8000/strategy-execution-bridge/e2e/run-signal`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/e2e/flows`
- `GET http://127.0.0.1:8000/trade-copier/execution-results`
- `POST http://127.0.0.1:8000/trade-copier/distribute-execution`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/status`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/overview`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/pipeline-events`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/recent-executions`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/recent-rejections`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/readiness`
- `GET http://127.0.0.1:8000/strategy-execution-bridge/operations/health`
- `GET http://127.0.0.1:8000/deployment/status`
- `GET http://127.0.0.1:8000/deployment/readiness`
- `GET http://127.0.0.1:8000/deployment/checklist`
- `GET http://127.0.0.1:8000/deployment/blockers`
- `GET http://127.0.0.1:8000/deployment/warnings`
- `GET http://127.0.0.1:8000/security/status`
- `GET http://127.0.0.1:8000/security/secrets-audit`
- `GET http://127.0.0.1:8000/security/access-policy`
- `GET http://127.0.0.1:8000/strategy/session`
- `GET http://127.0.0.1:8000/strategy/snapshot/XAUUSD`

Risk Management API examples:

- `GET http://127.0.0.1:8000/risk/status`
- `GET http://127.0.0.1:8000/risk/config`
- `POST http://127.0.0.1:8000/risk/calculate-position-size`
- `POST http://127.0.0.1:8000/risk/check-trade`
- `POST http://127.0.0.1:8000/risk/kill-switch/activate`
- `POST http://127.0.0.1:8000/risk/kill-switch/deactivate`

Execution Engine API examples:

- `GET http://127.0.0.1:8000/execution/status`
- `POST http://127.0.0.1:8000/execution/validate-order`
- `POST http://127.0.0.1:8000/execution/simulate-order`
- `POST http://127.0.0.1:8000/execution/prepare-mt5-order`
- `GET http://127.0.0.1:8000/execution/logs`
- `GET http://127.0.0.1:8000/execution/logs/{execution_id}`

MT5 Broker Data Layer API examples:

- `GET http://127.0.0.1:8000/mt5/status`
- `POST http://127.0.0.1:8000/mt5/initialize`
- `POST http://127.0.0.1:8000/mt5/shutdown`
- `GET http://127.0.0.1:8000/mt5/account`
- `GET http://127.0.0.1:8000/mt5/symbol/XAUUSD`
- `GET http://127.0.0.1:8000/mt5/tick/XAUUSD`
- `GET http://127.0.0.1:8000/mt5/positions`
- `GET http://127.0.0.1:8000/mt5/positions/XAUUSD`
- `GET http://127.0.0.1:8000/mt5/health`

Database Persistence API examples:

- `GET http://127.0.0.1:8000/database/status`
- `POST http://127.0.0.1:8000/database/init`
- `GET http://127.0.0.1:8000/database/trades/recent`
- `GET http://127.0.0.1:8000/database/execution-logs/recent`
- `GET http://127.0.0.1:8000/database/risk-events/recent`
- `GET http://127.0.0.1:8000/database/strategy-snapshots/recent`
- `GET http://127.0.0.1:8000/database/market-snapshots/recent`
- `GET http://127.0.0.1:8000/database/audit-logs/recent`
- `POST http://127.0.0.1:8000/database/audit-logs/test`
- `POST http://127.0.0.1:8000/database/market-snapshots/test`

AI Decision Engine API examples:

- `GET http://127.0.0.1:8000/ai/status`
- `GET http://127.0.0.1:8000/ai/regime/XAUUSD`
- `GET http://127.0.0.1:8000/ai/signal-score/XAUUSD`
- `GET http://127.0.0.1:8000/ai/decision/XAUUSD`
- `GET http://127.0.0.1:8000/ai/full-analysis/XAUUSD`
- `GET http://127.0.0.1:8000/ai/confidence/XAUUSD`

News Intelligence API examples:

- `GET http://127.0.0.1:8000/news/status`
- `GET http://127.0.0.1:8000/news/command-center`
- `GET http://127.0.0.1:8000/news/health`
- `GET http://127.0.0.1:8000/news/readiness-dashboard`
- `GET http://127.0.0.1:8000/news/phase7/status`
- `GET http://127.0.0.1:8000/news/supported-sources`
- `GET http://127.0.0.1:8000/news/supported-events`
- `GET http://127.0.0.1:8000/news/calendar-placeholder`
- `GET http://127.0.0.1:8000/news/readiness`
- `POST http://127.0.0.1:8000/news/forex-factory/ingest`
- `GET http://127.0.0.1:8000/news/calendar`
- `GET http://127.0.0.1:8000/news/upcoming-events`
- `GET http://127.0.0.1:8000/news/risk-context`
- `GET http://127.0.0.1:8000/news/filter/status`
- `POST http://127.0.0.1:8000/news/filter/evaluate`
- `GET http://127.0.0.1:8000/news/filter/current/xauusd`
- `GET http://127.0.0.1:8000/news/macro/status`
- `POST http://127.0.0.1:8000/news/macro/context`
- `GET http://127.0.0.1:8000/news/macro/context`
- `GET http://127.0.0.1:8000/news/macro/xauusd-bias`
- `POST http://127.0.0.1:8000/news/macro/xauusd-bias/evaluate`
- `POST http://127.0.0.1:8000/news/headlines/ingest`
- `GET http://127.0.0.1:8000/news/headlines`
- `GET http://127.0.0.1:8000/news/headlines/recent`
- `GET http://127.0.0.1:8000/news/headlines/risk-context`
- `POST http://127.0.0.1:8000/news/headlines/evaluate`
- `GET http://127.0.0.1:8000/news/unified-risk/status`
- `GET http://127.0.0.1:8000/news/unified-risk/xauusd`
- `POST http://127.0.0.1:8000/news/unified-risk/evaluate`
- `GET http://127.0.0.1:8000/news/upcoming`
- `GET http://127.0.0.1:8000/news/high-impact`
- `GET http://127.0.0.1:8000/news/risk-status/XAUUSD`
- `GET http://127.0.0.1:8000/news/allow-trading/XAUUSD`
- `GET http://127.0.0.1:8000/news/blackout-windows`
- `GET http://127.0.0.1:8000/news/macro-score/XAUUSD`

Trading Orchestration API examples:

- `GET http://127.0.0.1:8000/orchestration/status`
- `POST http://127.0.0.1:8000/orchestration/run/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/orchestration/symbols`
- `POST http://127.0.0.1:8000/orchestration/symbols/XAUUSD`
- `DELETE http://127.0.0.1:8000/orchestration/symbols/XAUUSD`
- `GET http://127.0.0.1:8000/orchestration/last-decision/XAUUSD`
- `GET http://127.0.0.1:8000/orchestration/config`

Backtesting API examples:

- `GET http://127.0.0.1:8000/backtesting/status`
- `POST http://127.0.0.1:8000/backtesting/run/XAUUSD`
- `GET http://127.0.0.1:8000/backtesting/results/recent`
- `GET http://127.0.0.1:8000/backtesting/result/{backtest_id}`
- `GET http://127.0.0.1:8000/backtesting/metrics/{backtest_id}`
- `GET http://127.0.0.1:8000/backtesting/equity/{backtest_id}`

Live Streaming API examples:

- `GET http://127.0.0.1:8000/streaming/status`
- `POST http://127.0.0.1:8000/streaming/start/XAUUSD`
- `POST http://127.0.0.1:8000/streaming/stop/XAUUSD`
- `GET http://127.0.0.1:8000/streaming/tick/XAUUSD`
- `GET http://127.0.0.1:8000/streaming/clients`
- `WS ws://127.0.0.1:8000/ws/market/XAUUSD`

Background Trading Loop API examples:

- `GET http://127.0.0.1:8000/trading-loop/status`
- `GET http://127.0.0.1:8000/trading-loop/config`
- `POST http://127.0.0.1:8000/trading-loop/start`
- `POST http://127.0.0.1:8000/trading-loop/stop`
- `POST http://127.0.0.1:8000/trading-loop/pause`
- `POST http://127.0.0.1:8000/trading-loop/resume`
- `POST http://127.0.0.1:8000/trading-loop/run-once`
- `GET http://127.0.0.1:8000/trading-loop/symbols`
- `POST http://127.0.0.1:8000/trading-loop/symbols/XAUUSD`
- `DELETE http://127.0.0.1:8000/trading-loop/symbols/XAUUSD`

Trade Journal And Advanced Risk Analytics API examples:

- `GET http://127.0.0.1:8000/trade-journal/status`
- `POST http://127.0.0.1:8000/trade-journal/add-test-entry`
- `GET http://127.0.0.1:8000/trade-journal/recent`
- `GET http://127.0.0.1:8000/trade-journal/risk-analytics`
- `GET http://127.0.0.1:8000/trade-journal/exposure`
- `GET http://127.0.0.1:8000/trade-journal/risk-alerts`

System Health And Phase 1 Hardening API examples:

- `GET http://127.0.0.1:8000/system/status`
- `GET http://127.0.0.1:8000/system/readiness`
- `GET http://127.0.0.1:8000/system/safety-scan`
- `GET http://127.0.0.1:8000/system/routes`
- `GET http://127.0.0.1:8000/system/phase-report`
- `GET http://127.0.0.1:8000/system/config-summary`

Institutional Intelligence API examples:

- `GET http://127.0.0.1:8000/institutional/status`
- `GET http://127.0.0.1:8000/institutional/context/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/swings/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/liquidity/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/bias/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/premium-discount/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/displacement/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/sweeps/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/latest-sweep/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/high-quality-sweeps/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/context/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/context/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/bos/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/choch/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/mss/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/context/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/score/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/explanation/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/components/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/confluence/readiness/XAUUSD?timeframe=M15`

## Run Day 1 Verification

```powershell
python tests/day1_verification.py
```

The verifier prints readable `PASS` or `FAIL` results for folders, imports, settings, logger, MT5 module presence, database models, docs, and environment template.

## Run Day 2 Verification

```powershell
python tests/day2_verification.py
```

The Day 2 verifier checks the market data package, API router registration, supported timeframes, validators, and Candle model without requiring a live MT5 terminal.

## Run Day 3 Verification

```powershell
python tests/day3_verification.py
```

The Day 3 verifier checks strategy modules, router registration, session handling, analyzer imports, and the StrategySnapshot model without requiring a live MT5 terminal.

## Run Day 4 Verification

```powershell
python tests/day4_verification.py
```

The Day 4 verifier checks centralized risk modules, router registration, risk guard behavior, position sizing, kill-switch state, and risk status without requiring MT5.

## Run Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day5_verification.py
```

The Day 5 execution engine is simulation-only. It validates requests, checks risk permission, records in-memory logs, and returns simulated fills. The MT5 execution path is deliberately disabled and does not place real trades.

## Run Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day6_verification.py
```

The Day 6 MT5 broker layer is read-only. It provides safe connection, account, symbol, tick, position, and health inspection while returning structured unavailable states when the terminal cannot be reached.

## Run Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day7_verification.py
```

The Day 7 persistence layer uses a local SQLite database when `DATABASE_URL` is not configured and remains ready for PostgreSQL through environment configuration.

## Run Day 8 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day8_verification.py
```

The Day 8 AI layer is rule-based and advisory only. It scores trade quality, classifies regime, records generated decisions for audit and later research, and never enables live trade execution.

## Run Day 9 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day9_verification.py
```

The Day 9 news engine uses dynamic mock economic-calendar events to calculate macro risk and no-trade blackout windows. It filters trading permission only and never submits orders.

## Run Day 10 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day10_verification.py
```

The Day 10 orchestration engine runs a single coordinated trade-readiness pipeline across strategy, AI, news, and risk controls. It can invoke simulated execution after approval, records audit outcomes when persistence is available, and does not enable broker order submission.

## Run Day 11 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day11_verification.py
```

The Day 11 backtesting engine replays deterministic historical candles through historical strategy and AI advisory evaluation, simulates PnL with spread and slippage, stores reports and simulated trades, and remains isolated from live broker execution.

## Run Day 12 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day12_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'streaming' in r.path or 'ws' in r.path])"
```

The Day 12 streaming engine publishes read-only tick messages over REST and WebSocket interfaces. It can use already-available MT5 ticks or simulated fallback data, creates no uncontrolled background loop, and never enables live execution.

## Run Day 13 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'trading-loop' in r.path])"
```

The Day 13 trading loop owns a single rate-limited, start/stop-controlled monitoring task. It delegates to simulation-only orchestration, tracks cycle results, writes audit events when available, and permanently reports `live_execution_enabled: false`.

## Run Day 14 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day14_verification.py
```

The Day 14 trade journal stores simulation-only analytics entries and produces performance, exposure, drawdown, strategy-effectiveness, and risk-alert reporting without any broker action.

## Run Day 15 And Phase 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'system' in r.path])"
```

Day 15 supplies unified module readiness, route integrity, runtime configuration reporting, source safety scanning, lifecycle cleanup verification, and the Phase 1 completion report. All system health endpoints are read-only and preserve simulation-only boundaries.

## Run Phase 2 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 1 adds analysis-only institutional context: swings, equal and structural liquidity, structure bias, premium/discount positioning, and displacement observations. It consumes read-only candle data when available and returns a safe empty context otherwise; it cannot place or enable trades.

## Run Phase 2 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 2 detects validated liquidity sweeps only after mapped pools have formed. A bearish sweep rejects above high-side liquidity and closes back below; a bullish sweep rejects below low-side liquidity and closes back above. Results include wick rejection validation, bounded strength scoring, and high-quality context for future analysis, with no execution capability.

## Run Phase 2 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 3 identifies bullish and bearish three-candle fair value gaps, evaluates fresh, partial, and fully mitigated lifecycle status using later candles only, and returns strength-scored imbalance context aligned with structural bias. The FVG engine is observation-only and cannot place or enable trades.

## Run Phase 2 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day4_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 4 detects bullish and bearish order blocks as opposing candles before expanded displacement, requires break-of-structure confirmation, tracks fresh and mitigated zones, and provides deterministic FVG, sweep, and bias confluence scoring. Its outputs remain analysis-only and cannot submit or enable live orders.

## Run Phase 2 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day5_verification.py
python tests/phase2_day4_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 5 identifies bullish and bearish breaker blocks when validated order blocks fail on opposite-direction displacement closes. It confirms structure shifts, tracks converted-zone mitigation, and scores FVG, sweep, source-OB, and bias context without introducing any live execution capability.

## Run Phase 2 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day6_verification.py
python tests/phase2_day5_verification.py
python tests/phase2_day4_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 6 identifies strong and weak swing breaks, continuation BOS events, counter-bias CHOCH events, and displacement or follow-through confirmed MSS events. It combines structure events with sweep, FVG, order-block, breaker, and bias context while remaining analysis-only.

## Run Phase 2 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day7_verification.py
python tests/phase2_day6_verification.py
python tests/phase2_day5_verification.py
python tests/phase2_day4_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 7 consolidates bias, sweeps, FVGs, order blocks, breakers, structure shifts, dealing-range position, displacement, session quality, and risk status into deterministic bullish/bearish confluence scores, quality/readiness labels, and dashboard-ready explanations. The result is analysis-only and cannot place or enable trades.

## Run Phase 2 Day 8 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day8_verification.py
python tests/phase2_day7_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 8 evaluates the existing confluence intelligence across H4, H1, M15, and M5. It resolves top-down institutional direction with H4 authority, identifies higher/lower timeframe conflict, and returns dashboard-ready narrative and alignment confidence. The feature is analysis-only and remains incapable of enabling or placing trades.

## Run Phase 2 Day 9 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day9_verification.py
python tests/phase2_day8_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 9 measures Asian, London, and New York UTC ranges; identifies London Open, New York Open, and London Close killzones; and ranks time-of-day quality using range expansion, confirmed range raids, advisory news risk, confluence, and multi-timeframe alignment. It is a simulation-only timing assessment and cannot enable or place trades.

## Run Phase 2 Day 10 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day10_verification.py
python tests/phase2_day9_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 10 converts confluence, alignment, session timing, sweeps, imbalance zones, institutional blocks, structure shifts, and risk readiness into structured entry models for simulation assessment. Candidates include continuation, retracement, breaker retest, MSS reversal, liquidity reversal, and explicit no-trade outcomes; none can place or enable trades.

## Run Phase 2 Day 11 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day11_verification.py
python tests/phase2_day10_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 11 validates institutional entry models through independent alignment, session/news, confluence, risk, and structure gates. It produces visible approval or rejection reasoning and labels only qualified models as eligible for simulation; it adds no live execution capability.

## Run Phase 2 Day 12 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day12_verification.py
python tests/phase2_day11_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 12 turns validated approvals into final simulation-only decisions and analytical intents. It selects approved or conditional setups, estimates reward-to-risk, rechecks risk/news/session restrictions, and outputs `SIMULATE_BUY`, `SIMULATE_SELL`, `WAIT`, `AVOID`, or `NO_TRADE` without constructing broker orders or enabling live trading.

## Run Phase 2 Day 13 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day13_verification.py
python tests/phase2_day12_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 13 advances approved simulation intents through a paper-only lifecycle: pending candidate, deterministic midpoint activation, active monitoring, and closed outcome with simulated PnL and R result. Ambiguous candles use conservative invalidation-first evaluation, and all outputs preserve `simulation_only = true` with live execution disabled.

## Run Phase 2 Day 14 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day14_verification.py
python tests/phase2_day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 14 manages active paper positions with deterministic partial profit reduction, break-even protection, structure-aware trailing, institutional invalidation exits, session discipline, and emergency risk shutdown decisions. It is a post-entry simulation-management layer only and does not add any live execution path.

## Run Phase 2 Day 15 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day15_verification.py
python tests/phase2_day14_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 15 unifies all institutional contexts from market structure through paper-position management into one timed, failure-isolated orchestration report and one conservative final system state. It exposes client-ready summaries and health checks while preserving the simulation-only safety boundary.

## Run Phase 2 Day 16 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day16_verification.py
python tests/phase2_day15_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 16 translates institutional orchestration output into evidence-bounded market narratives, detailed desk reasoning, client summaries, dashboard summaries, and consistency checks. The reasoning output remains analysis-only and cannot claim or initiate live execution.

## Run Phase 2 Day 17 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day17_verification.py
python tests/phase2_day16_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 17 measures validated setups, simulation decisions, deduplicated paper outcomes, and position-management actions, then generates evidence-led optimization recommendations. Limited observations are identified as insufficient data, and the analytics layer cannot execute or enable live trading.

## Run Phase 2 Day 18 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day18_verification.py
python tests/phase2_day17_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 18 packages orchestration, reasoning, and performance outputs into JSON-safe dashboard cards, alerts, a final recommendation, and an overall dashboard status. It is a backend context layer only; recommendation eligibility is limited to paper simulation and no broker execution is added.

## Run Phase 2 Day 19 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day19_verification.py
python tests/phase2_day18_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

Phase 2 Day 19 certifies all nineteen institutional modules, audits the complete institutional API route surface, and publishes typed completion/readiness and safety reporting. Phase 2 is complete in simulation-only mode with live execution disabled.

## Phase 2 Completion And Client Demo

Phase 2 is complete and client-demo ready as a simulation-only institutional intelligence backend. It detects institutional market structure, grades and validates hypothetical setups, manages paper positions, explains decisions, reports analytics, and audits its own safety boundary.

Client demo endpoints:

- `GET http://127.0.0.1:8000/institutional/demo/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/demo/summary/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/demo/modules/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/demo/talking-points/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/phase2/completion-report`

Full final verification:

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day19_verification.py
python tests/phase2_full_verification.py
```

See `docs/phase-2-final-summary.md` for the final architecture and `docs/phase-2-client-demo-guide.md` for a concise presentation flow. Broker execution remains disabled throughout Phase 2.

## Run Phase 3 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day1_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

Phase 3 Day 1 adds a simulation-only advanced historical replay engine. It replays deterministic candle windows through the institutional pipeline without lookahead bias, records replay steps, calculates summary metrics, and exposes `/replay` APIs while keeping live execution disabled.

## Run Phase 3 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day1_verification.py
python tests/phase3_day2_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

Phase 3 Day 2 adds replay trade analytics and historical reporting. It analyzes replayed simulation decisions, paper-trade outcomes, equity progression, and recurring weaknesses through JSON-safe report routes such as `/replay/report/latest`, `/replay/analytics/trades/{replay_id}`, `/replay/equity/{replay_id}`, and `/replay/weaknesses/{replay_id}`. The reporting layer is historical analytics only and preserves `simulation_only = true` with live execution disabled.

## Run Phase 3 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day3_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

Phase 3 Day 3 adds replay calibration analytics. It analyzes blocked replay decisions, identifies restrictive gates, detects threshold strictness patterns, and produces safe research-mode tuning suggestions through `/replay/calibration/latest`, `/replay/calibration/{replay_id}`, `/replay/calibration/block-reasons/{replay_id}`, and `/replay/calibration/suggestions/{replay_id}`. It never changes live behavior and keeps hard safety gates strict.

## Run Phase 3 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day3_verification.py
python tests/phase3_day4_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

Phase 3 Day 4 adds historical replay scenario comparison. It ranks replay scenarios, compares timeframe performance, compares calibration filter behavior, and exposes `/replay/compare/recent`, `/replay/compare`, `/replay/compare/timeframes/{symbol}`, and `/replay/compare/filters`. The engine is comparison analytics only and cannot alter execution behavior.

## Run Phase 3 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day5_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'replay' in r.path])"
```

Phase 3 Day 5 adds official multi-symbol replay support for `EURUSD`, `XAUUSD`, and `NIFTY50`, including aliases such as `EUR/USD`, `GOLD`, and `NIFTY`. The deterministic replay loader uses symbol-specific price scales, and the API exposes `/replay/symbols`, `/replay/symbols/{symbol}`, `/replay/run-all-client-symbols`, and `/replay/compare/client-symbols`.

## Run Phase 3 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day6_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 6 adds simulation-only broker compatibility metadata for STARTRADER, FxPro, and Vantage. It maps `EURUSD` and `XAUUSD` as theoretical demo candidates, marks `NIFTY50` as conditional/unsupported pending terminal verification, and exposes `/brokers/status`, `/brokers`, `/brokers/{broker_id}/symbols`, and `/brokers/{broker_id}/demo-readiness`.

## Run Phase 3 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day7_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 7 adds read-only MT5 demo-readiness and broker symbol verification. It exposes `/brokers/mt5/readiness`, `/brokers/verification/all`, `/brokers/{broker_id}/verification`, and `/brokers/{broker_id}/verification/{symbol}`. If MT5 is unavailable, verification degrades safely; NIFTY50 remains conditional unless confirmed by the demo terminal.

## Run Phase 3 Day 8 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day7_verification.py
python tests/phase3_day8_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 8 adds broker demo observation mode. It exposes `/brokers/observation/status`, `/brokers/observation/all`, `/brokers/{broker_id}/observation`, and `/brokers/{broker_id}/observation/{symbol}`. The observer uses read-only MT5 tick/symbol data when available and marks fallback or unavailable data explicitly.

## Run Phase 3 Day 9 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day9_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 9 adds broker feed quality validation. It classifies spread quality, validates tick freshness, detects missing bid/ask data, and exposes `/brokers/feed-quality/status`, `/brokers/feed-quality/all`, `/brokers/{broker_id}/feed-quality`, and `/brokers/{broker_id}/feed-quality/{symbol}`. The engine is read-only data validation only.

## Run Phase 3 Day 10 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day9_verification.py
python tests/phase3_day10_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 10 adds canonical market feed normalization. It converts broker observation snapshots into AI-ready canonical ticks with bid, ask, mid, spread, market type, source metadata, usability, and quality. Routes include `/brokers/canonical-feed/status`, `/brokers/canonical-feed/all`, `/brokers/{broker_id}/canonical-feed`, and `/brokers/{broker_id}/canonical-feed/{symbol}`.

## Run Phase 3 Day 11 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day11_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'broker' in r.path or 'brokers' in r.path])"
```

Phase 3 Day 11 adds read-only canonical candle feeds for `M5`, `M15`, `H1`, and `H4`. It fetches MT5 OHLC candles when read-only terminal data is available, falls back to deterministic simulated candles when unavailable, validates OHLC integrity, and exposes `/brokers/candles/status`, `/brokers/candles/all`, `/brokers/{broker_id}/candles/{symbol}`, and `/brokers/{broker_id}/candles/{symbol}/{timeframe}`.

## Run Phase 3 Day 12 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day12_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'webhook' in r.path or 'webhooks' in r.path])"
```

Phase 3 Day 12 adds the TradingView webhook foundation. It safely ingests alerts, authenticates optional webhook secrets, validates payloads, normalizes aliases for `EURUSD`, `XAUUSD`, and `NIFTY50`, creates orchestration-ready signal objects, and exposes `/webhooks/tradingview`, `/webhooks/status`, `/webhooks/events`, and `/webhooks/events/{event_id}`. This is ingestion only and does not route or place trades.

## Run Phase 3 Day 13 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day13_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'webhook' in r.path or 'webhooks' in r.path])"
```

Phase 3 Day 13 adds the webhook signal orchestration bridge. It consumes normalized TradingView signals, checks institutional dashboard context when available, applies a simulation-only risk gate, builds broker routing previews, and returns decisions through `/webhooks/orchestration/status`, `/webhooks/orchestration/decisions`, `/webhooks/orchestration/decisions/{decision_id}`, and `/webhooks/orchestration/test`.

## Run Phase 3 Day 14 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day14_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'webhook' in r.path or 'webhooks' in r.path])"
```

Phase 3 Day 14 adds webhook validation hardening for VPS/public deployment preparation. It includes deterministic request fingerprinting, duplicate/replay detection, source-IP rate limiting, malformed payload classification, security audit logging, and `/webhooks/security/status`, `/webhooks/security/events`, and `/webhooks/security/test`.

## Run Phase 3 Day 15 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day15_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'account' in r.path or 'accounts' in r.path])"
```

Phase 3 Day 15 adds the multi-account routing foundation. It defines broker demo account profiles, account groups, a default `COPY_TO_ALL` routing policy, simulation-only route previews, and conservative disabled placeholders for Zerodha, AngelOne, and Upstox. Routes include `/accounts/status`, `/accounts`, `/accounts/groups`, `/accounts/policy/default`, and `/accounts/route-preview`.

## Run Phase 3 Day 16 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day15_verification.py
python tests/phase3_day16_verification.py
```

Phase 3 Day 16 adds account allocation and risk distribution previews. It maintains simulated account risk profiles, balance snapshots, symbol risk rules, broker lot constraints, exposure checks, and allocation previews through `/accounts/allocation/status`, `/accounts/risk-profiles`, `/accounts/balance-snapshots`, `/accounts/symbol-rules/{symbol}`, and `/accounts/allocation/preview`.

## Run Phase 3 Day 17 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day17_verification.py
```

Phase 3 Day 17 adds the execution queue foundation. It converts approved allocation previews into non-executing execution intents, validates demo-queue readiness, stores queue items, supports cancellation, and exposes `/execution-queue/status`, `/execution-queue/items`, `/execution-queue/items/{queue_id}`, `/execution-queue/enqueue-preview`, and `/execution-queue/items/{queue_id}/cancel`.

## Run Phase 3 Day 18 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day17_verification.py
python tests/phase3_day18_verification.py
```

Phase 3 Day 18 adds the simulated execution lifecycle emulator. It processes execution queue items without broker orders, simulates acceptance/fill/rejection, tracks lifecycle states, records audit events, reconciles simulated fills, and exposes `/execution-queue/lifecycle/status`, `/execution-queue/lifecycle/items`, `/execution-queue/lifecycle/audit-events`, `/execution-queue/items/{queue_id}/simulate`, and `/execution-queue/simulate-latest`.

## Run Phase 3 Day 19 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day19_verification.py
```

Phase 3 Day 19 adds centralized monitoring and alerting. It tracks module health, system snapshots, execution queue summaries, webhook/security metrics, broker feed health, and alert acknowledgement through `/monitoring/status`, `/monitoring/system-health`, `/monitoring/modules`, `/monitoring/execution`, `/monitoring/webhooks`, `/monitoring/brokers`, and `/monitoring/alerts`.

## Run Phase 3 Day 20 / Full Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase3_day19_verification.py
python tests/phase3_day20_verification.py
python tests/phase3_full_verification.py
```

Phase 3 Day 20 adds integration hardening and delivery readiness. It exposes `/phase3/status`, `/phase3/modules`, `/phase3/routes`, `/phase3/pipeline`, `/phase3/safety-audit`, and `/phase3/client-readiness`, validating the full simulation-only chain from TradingView signal to simulated lifecycle and monitoring.

## Run Phase 4 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day1_verification.py
```

Phase 4 Day 1 begins the VPS dashboard backend foundation. It aggregates existing backend services into dashboard-ready status, overview, card, and summary outputs through `/dashboard/status`, `/dashboard/overview`, `/dashboard/cards`, and `/dashboard/summary`. This is backend context only; frontend UI and manual safety controls come later.

## Run Phase 4 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day1_verification.py
python tests/phase4_day2_verification.py
```

Phase 4 Day 2 adds the VPS dashboard frontend shell at `frontend/app/dashboard/page.tsx`, with reusable components under `frontend/components/dashboard` and API helpers in `frontend/lib/dashboard-api.ts`. The shell displays system, broker, webhook, routing, allocation, execution queue, alerts, Phase 3 readiness, and safety status. It is display-only and keeps live execution disabled.

## Run Phase 4 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day3_verification.py
cd frontend
npm run lint
npm run build
```

Phase 4 Day 3 upgrades the dashboard into a premium client-ready trading UI. It adds refined glass cards, a compact gradient header, broker status widgets, account status widgets, execution safety guardrails, and a cleaner responsive layout while preserving simulation-only display behavior.

## Run Phase 4 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day3_verification.py
python tests/phase4_day4_verification.py
cd frontend
npm run lint
npm run build
```

Phase 4 Day 4 adds live dashboard data panels and safe auto-refresh. The dashboard polls backend status every 10 seconds by default, supports pause/resume and manual refresh, preserves previous data during partial backend failures, and displays live broker, account routing, execution queue, webhook, monitoring, and Phase 3 readiness state.

## Run Phase 4 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day6_verification.py
cd frontend
npm run build
```

Phase 4 Day 6 adds the simulation-only manual override and safety control panel. Backend routes under `/control-center` expose safety lock state, queue pause/resume, queue-item cancellation, alert acknowledgement, emergency-stop placeholder state, and audit events. The dashboard now includes manual controls, a safety lock panel, and an operator audit trail while keeping live and broker execution disabled.

## Run Phase 4 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day7_verification.py
cd frontend
npm run build
```

Phase 4 Day 7 adds client demo mode and an executive overview dashboard section. Backend routes under `/demo-mode` summarize supported markets, supported brokers, TradingView-to-simulation pipeline readiness, executive KPI cards, safety posture, and next production steps. The frontend now presents this as a polished top-level client demo section while preserving simulation-only behavior.

## Run Phase 4 Day 8 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day8_verification.py
cd frontend
npm run build
```

Phase 4 Day 8 adds portfolio and account analytics. Backend routes under `/portfolio` expose simulated account summaries, portfolio overview, symbol-level exposure, and placeholder P&L. The dashboard now shows broker demo balances, enabled/disabled account state, EURUSD/XAUUSD readiness, NIFTY50 conditional status, and live-execution-disabled portfolio safety labels.

## Run Phase 4 Day 9 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day9_verification.py
cd frontend
npm run build
```

Phase 4 Day 9 adds the Operational Intelligence Center. Backend routes under `/operational-intelligence` aggregate health score, module status, warnings, alerts, broker readiness, webhook posture, queue health, control center state, portfolio analytics, and safety posture. The dashboard now includes a health score card, monitored module grid, warning center, and operational insights.

## Run Phase 4 Day 10 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase4_day9_verification.py
python tests/phase4_day10_verification.py
cd frontend
npm run build
```

Phase 4 Day 10 adds the client acceptance and delivery readiness layer. Backend routes under `/client-acceptance` expose final readiness score, checklist, and remaining production items. The dashboard now includes a client delivery readiness section with score visualization, completed systems, deployment/demo readiness badges, remaining work, and safety confirmation.

## Run Phase 5 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
```

Phase 5 Day 1 adds the MT5 demo execution bridge. Backend routes under `/demo-execution` verify demo-account status, guard execution queue items, build tiny EURUSD-only market requests, store demo execution results, and block safely whenever MT5 demo conditions are not satisfied. Live account execution remains disabled.

## Run Phase 5 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
```

Phase 5 Day 2 adds the first controlled end-to-end demo execution flow. `/demo-execution/eligible-queue-items` lists EURUSD-only queue items that meet the tiny-lot demo rules, `/demo-execution/execute-latest-eligible` submits the newest eligible item through the guarded demo executor, and `/demo-execution/audit-events` exposes request, blocked, order-sent, filled, rejected, and failed-safe audit events. Duplicate queue execution is blocked, lifecycle states are updated, and live execution remains disabled.

## Run Phase 5 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
```

Phase 5 Day 3 adds multi-account MT5 demo routing. Backend routes under `/multi-account-execution` preview STARTRADER/FxPro/Vantage demo account plans, enforce EURUSD-only 0.01-lot-per-account rules, block XAUUSD and NIFTY50, prevent duplicate per-account execution attempts, and store per-account batch results. Any MT5 submission remains delegated through the existing guarded demo executor only.

## Run Phase 5 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
python tests/phase5_day4_verification.py
```

Phase 5 Day 4 adds the demo trade copier coordination layer. Backend routes under `/trade-copier` preview READY/PLANNED copy batches, create auditable copy batches, track per-account copy status, summarize synchronized outcomes, identify partial copies and unavailable accounts, block duplicate copy attempts per signal/account/symbol/action on created batches, and prepare dashboard-visible batch status. The copier remains EURUSD-only, demo-only, and never submits MT5 orders directly.

## Run Phase 5 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
python tests/phase5_day4_verification.py
python tests/phase5_day5_verification.py
```

Phase 5 Day 5 adds execution confirmation tracking and position lifecycle reconciliation. Backend routes under `/execution-confirmation` ingest existing demo and multi-account execution results, track order/deal/position confirmation state, classify confirmed, pending, rejected, missing-position, and mismatched lifecycles, expose reconciliation summaries, and keep an audit trail. This layer is read-only, demo-only, and adds no order placement path.

## Run Phase 5 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
python tests/phase5_day4_verification.py
python tests/phase5_day5_verification.py
python tests/phase5_day6_verification.py
```

Phase 5 Day 6 adds execution-time risk enforcement. Backend routes under `/execution-risk` expose the active policy, evaluate proposed demo execution requests, and list risk decisions and audit events. The demo execution guard, multi-account execution guard, and trade copier service now call the risk evaluator before allowing execution or copy workflows to proceed. Policy remains EURUSD-only, max `0.01` lot per account, max three target accounts, queue/emergency-stop aware, and live/broker execution disabled.

## Run Phase 5 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day1_verification.py
python tests/phase5_day2_verification.py
python tests/phase5_day3_verification.py
python tests/phase5_day4_verification.py
python tests/phase5_day5_verification.py
python tests/phase5_day6_verification.py
python tests/phase5_day7_verification.py
cd frontend
npm run build
```

Phase 5 Day 7 adds the unified Execution Operations Dashboard. Backend routes under `/execution-dashboard` aggregate demo execution bridge status, multi-account routing, trade copier state, confirmations, reconciliation, risk decisions, audit warnings, health score, and client-facing execution readiness. The frontend dashboard now includes the Execution Operations Center with health cards, summary metrics, and readiness safety flags. This is display and monitoring only; live and broker execution remain disabled.

## Run Phase 6 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase5_day7_verification.py
python tests/phase6_day1_verification.py
```

Phase 6 Day 1 adds the XAUUSD strategy engine foundation. Backend routes under `/strategy` expose analysis-only status, XAUUSD signal generation, stored signals, and session context. The engine builds UTC session context, EMA/ATR/RSI indicator context, Asian and previous-day liquidity sweep context, SMC/ICT placeholders, and risk-safe strategy signals. Signals default to `WAIT` without sufficient market context and always return `execution_allowed=false`.

## Run Phase 6 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
```

Phase 6 Day 2 adds the professional XAUUSD liquidity sweep detection engine. Backend routes under `/strategy/liquidity/xauusd` expose Asian high/low, previous-day high/low, equal highs/lows, liquidity pools, buy-side and sell-side sweep detection, rejection classification, session alignment, sweep strength, confidence, and sweep quality. This remains strategy analysis only; the strategy engine still requires future SMC confirmation and keeps `execution_allowed=false`.

## Run Phase 6 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
python tests/phase6_day3_verification.py
```

Phase 6 Day 3 adds the BOS / CHOCH market structure detection engine. Backend routes under `/strategy/structure/xauusd` expose swing highs, swing lows, bullish/bearish BOS, bullish/bearish CHOCH, structure bias, structure strength, structure quality, and post-liquidity-sweep confirmation. This remains strategy analysis only; BUY/SELL outputs are candidates only and `execution_allowed=false` remains enforced.

## Run Phase 6 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
python tests/phase6_day3_verification.py
python tests/phase6_day4_verification.py
```

Phase 6 Day 4 adds the Fair Value Gap detection engine. Backend routes under `/strategy/fvg/xauusd` expose bullish and bearish FVGs, bounds, midpoint, size, fill percentage, mitigation state, active state, quality, and alignment with BOS/CHOCH and liquidity sweeps. This remains strategy analysis only; FVG is confluence, not a standalone trading trigger.

## Run Phase 6 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
python tests/phase6_day3_verification.py
python tests/phase6_day4_verification.py
python tests/phase6_day5_verification.py
```

Phase 6 Day 5 adds the Institutional Order Block detection engine. Backend routes under `/strategy/order-block/xauusd` expose bullish and bearish order blocks, bounds, midpoint, active/fresh/mitigated/broken state, fill percentage, remaining effectiveness, quality, and alignment with BOS/CHOCH, liquidity sweeps, and FVGs. This remains strategy analysis only; order blocks are confluence confirmation and never enable execution.

## Run Phase 6 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
python tests/phase6_day3_verification.py
python tests/phase6_day4_verification.py
python tests/phase6_day5_verification.py
python tests/phase6_day6_verification.py
```

Phase 6 Day 6 adds the Market Regime Detection Engine. Backend routes under `/strategy/regime/xauusd` classify XAUUSD as trending, ranging, high volatility, low volatility, news-volatility placeholder, or unclear, then return trend strength, volatility score, range score, ATR state, EMA alignment, tradeability, risk mode, and confidence. The XAUUSD strategy engine now uses regime context to force `WAIT` in high-volatility, low-volatility, and unclear conditions, reduce confidence during ranges, and reward healthy trending conditions while keeping execution disabled.

## Run Phase 6 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day1_verification.py
python tests/phase6_day2_verification.py
python tests/phase6_day3_verification.py
python tests/phase6_day4_verification.py
python tests/phase6_day5_verification.py
python tests/phase6_day6_verification.py
python tests/phase6_day7_verification.py
```

Phase 6 Day 7 adds the final XAUUSD confluence and confidence scoring engine. Backend routes under `/strategy/confluence/xauusd` combine session, indicators, liquidity sweep, BOS/CHOCH, FVG, order block, and market regime into confidence, trade quality, risk mode, aligned confirmations, missing confirmations, client summary, and technical summary. The engine produces BUY/SELL candidates only when directional liquidity, structure, FVG/order-block entry context, acceptable regime, and confidence are aligned, while `execution_allowed=false` remains enforced.

## Run Phase 7 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase6_day7_verification.py
python tests/phase7_day1_verification.py
```

Phase 7 Day 1 adds the News Intelligence Foundation. Backend routes under `/news` expose architecture status, supported placeholder sources, supported macro event types, a placeholder calendar, and readiness reporting for Forex Factory, Financial Juice, DXY, and US10Y integrations. This phase makes no external API calls, performs no scraping, uses no API keys, and only adds a non-decision-changing news placeholder to XAUUSD strategy metadata.

## Run Phase 7 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
```

Phase 7 Day 2 adds the Forex Factory economic calendar integration foundation. The system accepts manual Forex Factory-style event payloads through `/news/forex-factory/ingest`, normalizes them into economic calendar events, classifies CPI/NFP/FOMC/PMI risk, applies pre-news and post-news windows, and exposes `/news/calendar`, `/news/upcoming-events`, and `/news/risk-context`. No live fetching, scraping, API keys, or broker execution are introduced.

## Run Phase 7 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
python tests/phase7_day3_verification.py
```

Phase 7 Day 3 adds the News Risk Filter and Strategy Blocking Engine. Routes under `/news/filter` evaluate current or supplied news context, block XAUUSD analysis during high-impact and extreme USD news windows, reduce confidence before medium-risk events, and pause during post-news stabilization. This remains strategy filtering only and adds no live feeds, scraping, API calls, or execution path.

## Run Phase 7 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
python tests/phase7_day3_verification.py
python tests/phase7_day4_verification.py
```

Phase 7 Day 4 adds the DXY and US10Y Macro Bias Engine. Routes under `/news/macro` accept manual DXY and US10Y values, infer direction and momentum, derive XAUUSD gold macro bias, and evaluate whether macro context aligns with BUY/SELL candidates. This remains macro analysis only with no live feeds, scraping, API calls, or execution path.

## Run Phase 7 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
python tests/phase7_day3_verification.py
python tests/phase7_day4_verification.py
python tests/phase7_day5_verification.py
```

Phase 7 Day 5 adds the Financial Juice-style real-time headline intelligence foundation. Routes under `/news/headlines` accept manual headline payloads, normalize and classify Fed, inflation, CPI, NFP, FOMC, geopolitical, DXY, yield, gold, and USD headlines, build headline risk context, and adjust XAUUSD confluence confidence through a headline strategy filter. This remains manual/test-payload analysis only with no live feeds, scraping, API calls, or execution path.

## Run Phase 7 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
python tests/phase7_day3_verification.py
python tests/phase7_day4_verification.py
python tests/phase7_day5_verification.py
python tests/phase7_day6_verification.py
```

Phase 7 Day 6 adds the Unified News, Macro, and Headline Risk Orchestrator. Routes under `/news/unified-risk` combine economic calendar risk, news filter decisions, DXY/US10Y macro bias, and real-time headline context into one final XAUUSD risk action with confidence caps, confidence adjustments, blocking reasons, supportive reasons, and client/technical summaries. This remains orchestration-only with no live feeds, scraping, API calls, or execution path.

## Run Phase 7 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day1_verification.py
python tests/phase7_day2_verification.py
python tests/phase7_day3_verification.py
python tests/phase7_day4_verification.py
python tests/phase7_day5_verification.py
python tests/phase7_day6_verification.py
python tests/phase7_day7_verification.py
```

Phase 7 Day 7 adds the News Intelligence Command Center and Readiness Engine. Routes under `/news/command-center`, `/news/health`, `/news/readiness-dashboard`, and `/news/phase7/status` expose economic calendar, headline, macro, unified risk, health, readiness, and strategy news state in one operational visibility layer. Final Phase 7 status is `PHASE_7_READY` and `COMPLETE`, with no live feeds, scraping, API calls, or execution path.

## Run Phase 8 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase7_day7_verification.py
python tests/phase8_day1_verification.py
```

Phase 8 Day 1 adds the EURUSD strategy foundation while preserving XAUUSD as the primary strategy engine. Routes under `/strategy/analyze/eurusd`, `/strategy/eurusd/session-context`, and `/strategy/eurusd/indicator-context` expose analysis-only EURUSD signal, session, and indicator context. EURUSD returns `WAIT` until future confluence layers are added, with `execution_allowed=false`, `simulation_only=true`, and no broker connectivity.

## Run Phase 8 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
```

Phase 8 Day 2 adds the EURUSD liquidity sweep engine. The engine detects Asian high/low, previous-day high/low, equal highs/lows, buy-side and sell-side sweeps, rejection back inside liquidity, session alignment, and confidence scoring using EURUSD pip tolerance `0.0002`. EURUSD remains analysis-only and WAIT-only until future structure and confluence layers are integrated.

## Run Phase 8 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
python tests/phase8_day3_verification.py
```

Phase 8 Day 3 adds the EURUSD BOS / CHOCH market structure engine. The engine detects swing highs/lows, bullish and bearish BOS, bullish and bearish CHOCH, post-liquidity-sweep confirmation, structure strength, confidence, and quality using EURUSD pip tolerance `0.0002`. EURUSD remains analysis-only and WAIT-only until FVG, order block, regime, and confluence layers are integrated.

## Run Phase 8 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
python tests/phase8_day3_verification.py
python tests/phase8_day4_verification.py
```

Phase 8 Day 4 adds the EURUSD Fair Value Gap detection engine. The engine detects bullish and bearish FVGs, bounds, midpoint, fill percentage, active/mitigated state, structure alignment, liquidity alignment, and quality scoring using EURUSD tolerance `0.0002` while ignoring noise gaps below `0.0001`. EURUSD remains analysis-only and WAIT-only until order block, regime, and confluence layers are integrated.

## Run Phase 8 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
python tests/phase8_day3_verification.py
python tests/phase8_day4_verification.py
python tests/phase8_day5_verification.py
```

Phase 8 Day 5 adds the EURUSD Order Block detection engine. The engine detects bullish and bearish institutional order blocks, active/fresh/mitigated/broken state, fill percentage, structure alignment, liquidity alignment, FVG alignment, and quality scoring using EURUSD tolerance `0.0002` while ignoring tiny origin candles below `0.0001`. EURUSD remains analysis-only and WAIT-only until regime and confluence layers are integrated.

## Run Phase 8 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
python tests/phase8_day3_verification.py
python tests/phase8_day4_verification.py
python tests/phase8_day5_verification.py
python tests/phase8_day6_verification.py
```

Phase 8 Day 6 adds the EURUSD Market Regime detection engine. The engine classifies trending, ranging, high-volatility, low-volatility, and unclear EURUSD conditions with FX-scaled ATR/EMA/range logic, tradeability scoring, risk mode mapping, and strategy metadata integration. EURUSD remains analysis-only and WAIT-only until the final EURUSD confluence layer is integrated.

## Run Phase 8 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day1_verification.py
python tests/phase8_day2_verification.py
python tests/phase8_day3_verification.py
python tests/phase8_day4_verification.py
python tests/phase8_day5_verification.py
python tests/phase8_day6_verification.py
python tests/phase8_day7_verification.py
```

Phase 8 Day 7 completes the EURUSD strategy intelligence layer with final confluence and confidence scoring. The engine combines session, indicator, liquidity, BOS/CHOCH, FVG, order block, regime, news, and DXY macro placeholders into action, confidence, trade quality, risk mode, client summary, and technical summary. EURUSD remains analysis-only with `execution_allowed=false`.

## Run Phase 9 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase8_day7_verification.py
python tests/phase9_day1_verification.py
```

Phase 9 Day 1 adds the Strategy Signal to Execution Intent Bridge. The bridge validates XAUUSD/EURUSD strategy signals, rejects WAIT signals, low confidence, news blocks, no-trade regimes, and `execution_allowed=false`, then can map approved signals into demo intent previews only. No orders are placed, no broker execution is enabled, and queue preview remains guarded by safety checks.

## Run Phase 9 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
```

Phase 9 Day 2 connects eligible mock strategy signals to bridge-owned queue previews. EURUSD BUY/SELL mock signals can create preview IDs after eligibility and execution risk approval, while WAIT, low-confidence, `execution_allowed=false`, oversized lot, and current XAUUSD policy-blocked signals create no preview and no execution.

## Run Phase 9 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
python tests/phase9_day3_verification.py
```

Phase 9 Day 3 adds the queue preview to demo execution approval flow. Fresh, risk-approved queue previews can become demo execution candidates only after explicit `confirm_demo_approval=true`; unconfirmed, stale, duplicate, rejected, and risk-rejected previews are blocked. Candidates still require final execution confirmation later, and no demo executor is called.

## Run Phase 9 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
python tests/phase9_day3_verification.py
python tests/phase9_day4_verification.py
```

Phase 9 Day 4 connects approved demo execution candidates to the existing guarded MT5 demo executor path. Final execution requires `confirm_demo_execution=true`, reruns execution risk, blocks stale/duplicate/unapproved candidates, and uses only the existing guarded demo executor. No live execution path is added.

## Run Phase 9 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
python tests/phase9_day3_verification.py
python tests/phase9_day4_verification.py
python tests/phase9_day5_verification.py
```

Phase 9 Day 5 adds an end-to-end demo flow verifier. It proves the safe chain from strategy signal through bridge validation, risk evaluation, queue preview, demo approval, final confirmation, guarded MT5 demo execution, execution result capture, confirmation tracking, and flow audit storage. The flow remains demo-only and live execution stays disabled.

## Run Phase 9 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
python tests/phase9_day3_verification.py
python tests/phase9_day4_verification.py
python tests/phase9_day5_verification.py
python tests/phase9_day6_verification.py
```

Phase 9 Day 6 connects guarded demo execution records to the existing multi-account trade copier coordination layer. EURUSD demo executions can create copy batches for `STARTRADER_DEMO_1`, `FXPRO_DEMO_1`, and `VANTAGE_DEMO_1`; duplicate protection, execution risk checks, max `0.01` lot limits, and demo-only safety flags remain active.

## Run Phase 9 Day 7 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day1_verification.py
python tests/phase9_day2_verification.py
python tests/phase9_day3_verification.py
python tests/phase9_day4_verification.py
python tests/phase9_day5_verification.py
python tests/phase9_day6_verification.py
python tests/phase9_day7_verification.py
```

Phase 9 Day 7 completes the execution operations control center. Backend routes under `/strategy-execution-bridge/operations` expose pipeline status, overview counts, pipeline events, recent executions, recent rejections, readiness, and health score. The center is monitoring-only and keeps live and broker execution disabled.

## Run Phase 10 Day 1 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase9_day7_verification.py
python tests/phase10_day1_verification.py
cd frontend
npm run build
```

Phase 10 Day 1 starts VPS deployment hardening. Backend routes under `/deployment` audit environment readiness, VPS prerequisites, MT5 demo environment readiness, blockers, warnings, and the deployment checklist. Startup scripts are provided under `scripts/`, and `docs/deployment-readiness-checklist.md` captures the Mumbai VPS, Python, Node, MT5 demo, ports, logs, and safety-flag checklist. This phase does not enable live trading.

## Run Phase 10 Day 2 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase10_day1_verification.py
python tests/phase10_day2_verification.py
cd frontend
npm run build
```

Phase 10 Day 2 adds Docker packaging for backend and frontend with `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`, `docker-compose.override.yml`, `.dockerignore`, safe environment templates, and Docker helper scripts. Deployment readiness now reports Docker, Compose, and environment-template readiness while preserving simulation/demo-only defaults.

## Run Phase 10 Day 3 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase10_day1_verification.py
python tests/phase10_day2_verification.py
python tests/phase10_day3_verification.py
cd frontend
npm run build
```

Phase 10 Day 3 adds production logging and monitoring. Backend routes under `/monitoring` now expose platform health, system metrics, process status, API route counts, MT5 demo environment status, and read-only log views. Logs write to `logs/platform.log` with 10 MB rotation and 5 backups. Monitoring remains observability-only and does not enable live execution.

## Run Phase 10 Day 4 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase10_day1_verification.py
python tests/phase10_day2_verification.py
python tests/phase10_day3_verification.py
python tests/phase10_day4_verification.py
cd frontend
npm run build
```

Phase 10 Day 4 adds read-only VPS runtime and service-management visibility. Backend routes under `/deployment/runtime` report backend/frontend health, runtime status, MT5 demo notes, and runtime audit events. Manual scripts under `scripts/` start or check services; the API never kills or restarts processes.

## Run Phase 10 Day 5 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase10_day1_verification.py
python tests/phase10_day2_verification.py
python tests/phase10_day3_verification.py
python tests/phase10_day4_verification.py
python tests/phase10_day5_verification.py
cd frontend
npm run build
```

Phase 10 Day 5 adds security readiness, secrets auditing, route access classification, config redaction, security audit events, and `/security` endpoints. Deployment readiness now includes `security_ready`. This is a foundation only: admin routes are classified for future protection, real secrets are not added, and live/broker execution remain disabled.

## Run Phase 10 Day 6 Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase10_day6_verification.py
cd frontend
npm run build
```

Phase 10 Day 6 adds backup, recovery, rollback, and incident-response readiness. Backend routes under `/backup` expose readiness score, backup strategy, recovery runbook, rollback guidance, and incident-response guidance. Operator scripts `scripts/backup_status.ps1` and `scripts/recovery_check.ps1` provide read-only checks. This phase is operational resilience only and keeps live/broker execution disabled.

## MT5 Safety Boundary

The MT5 foundation remains live-disabled by default. Read-only connection checks, account info, symbol info, and latest ticks are available broadly; demo order placement is allowed only through the guarded Phase 5 demo executor, only for verified demo accounts, only for EURUSD market orders, and only up to `0.01` lot. Live account execution remains disabled.
##
