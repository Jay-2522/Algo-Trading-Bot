# AI-Assisted Algorithmic Trading Platform

Professional Day 1 foundation for a modular algorithmic trading platform covering Forex, XAUUSD, and Indian stock markets.

This repository currently contains only the architectural foundation. It does not implement trading strategies, AI models, or real order execution.

## Architecture Overview

- `backend/strategy_engine`: future strategy orchestration and signal lifecycle.
- `backend/execution_engine`: simulation-only order validation, risk-gated fills, and execution event logging.
- `backend/ai_engine`: rule-based advisory scoring, regime classification, confidence, and persisted trade-quality decisions.
- `backend/risk_engine`: risk limits, sizing calculations, guardrails, and emergency permission controls.
- `backend/news_engine`: future macro, market, and sentiment ingestion.
- `backend/market_data`: read-only MT5 market data collection, validation, candles, and snapshots.
- `backend/analytics`: future performance reporting and research analytics.
- `backend/broker_integrations`: broker adapters, including MT5 and Indian broker foundations.
- `backend/websocket`: future real-time dashboard transport.
- `backend/database`: SQLAlchemy persistence, repositories, SQLite fallback, and PostgreSQL-ready records.
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

## MT5 Safety Boundary

The MT5 foundation is read-only. It supports connection checks, account info, symbol info, and latest ticks. Order placement must be added later through the execution engine with risk checks, audit logging, and environment safeguards.
