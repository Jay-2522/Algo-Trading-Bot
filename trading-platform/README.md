# AI-Assisted Algorithmic Trading Platform

Professional Day 1 foundation for a modular algorithmic trading platform covering Forex, XAUUSD, and Indian stock markets.

This repository currently contains only the architectural foundation. It does not implement trading strategies, AI models, or real order execution.

## Architecture Overview

- `backend/strategy_engine`: future strategy orchestration and signal lifecycle.
- `backend/execution_engine`: future order execution workflows with broker and risk controls.
- `backend/ai_engine`: future AI-assisted analytics and decision support.
- `backend/risk_engine`: risk limits, sizing calculations, guardrails, and emergency permission controls.
- `backend/news_engine`: future macro, market, and sentiment ingestion.
- `backend/market_data`: read-only MT5 market data collection, validation, candles, and snapshots.
- `backend/analytics`: future performance reporting and research analytics.
- `backend/broker_integrations`: broker adapters, including MT5 and Indian broker foundations.
- `backend/websocket`: future real-time dashboard transport.
- `backend/database`: SQLAlchemy engine, sessions, and initial schema models.
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

Update `.env` with local PostgreSQL, Redis, and optional MT5 credentials.

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

## MT5 Safety Boundary

The MT5 foundation is read-only. It supports connection checks, account info, symbol info, and latest ticks. Order placement must be added later through the execution engine with risk checks, audit logging, and environment safeguards.
