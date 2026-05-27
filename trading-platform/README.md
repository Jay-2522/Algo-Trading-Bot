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

## MT5 Safety Boundary

The MT5 foundation is read-only. It supports connection checks, account info, symbol info, and latest ticks. Order placement must be added later through the execution engine with risk checks, audit logging, and environment safeguards.
