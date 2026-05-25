# Day 11 Progress

## Architecture

Day 11 introduces an offline Backtesting Engine foundation. It generates reproducible historical OHLCV candles, feeds rolling historical context through the existing strategy analyzers and AI advisory scoring layer, closes trades through an internal simulation engine, calculates performance, and persists backtest-only records.

## Modules Added

- `backtest_models.py`: typed requests, candles, trades, equity points, metrics, and reports.
- `historical_data_loader.py`: deterministic mock historical candles for `M1`, `M5`, `M15`, `H1`, and `H4`.
- `trade_simulator.py`: BUY/SELL exits with stop loss, take profit, spread, and slippage modeling.
- `performance_analyzer.py`: return, risk, expectancy, streak, and Sharpe approximation metrics.
- `equity_curve.py`: simulated balance and drawdown progression.
- `backtest_engine.py`: candle replay, historical strategy/AI evaluation, and report construction.
- `backtest_storage.py`: persistence of run summaries and simulated trades.
- `backtest_service.py`: API-facing report service.

## Data And Decision Flow

1. Accept a backtest request and build deterministic mock candles.
2. Validate OHLCV bars and skip malformed records safely.
3. Build rolling historical strategy context from trend, liquidity, structure, and session analyzers.
4. Send that historical context to the AI advisory scoring layer without reading live broker data.
5. Convert approved advisory directions into simulated BUY or SELL outcomes only.
6. Track the equity curve and calculate metrics.
7. Store the final result in `backtest_runs` and its simulated fills in `backtest_trades`.

## APIs Added

- `GET /backtesting/status`
- `POST /backtesting/run/{symbol}`
- `GET /backtesting/results/recent`
- `GET /backtesting/result/{backtest_id}`
- `GET /backtesting/metrics/{backtest_id}`
- `GET /backtesting/equity/{backtest_id}`

## Safety Protections

- Historical generation uses no external feed or broker terminal.
- AI evaluation receives historical strategy context and modeled spread quality.
- Trades are internal simulations and cannot submit broker orders.
- Invalid candles are skipped with recorded errors.
- Empty datasets and zero-trade runs return safe zero-valued statistics.
- New persistence tables are isolated from live-facing trade and execution records.
- Existing FastAPI routers remain registered on the single application instance.

## Simulation Boundary

Backtesting never calls execution APIs connected to MT5 and never creates live orders. A future paper-trading runtime must be separately designed, approved, and guarded before it can consume backtest research outcomes.

## Verification Summary

Run:

```powershell
python tests/regression_routes_verification.py
python tests/day11_verification.py
```

Manual API checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/backtesting/status
Invoke-RestMethod -Method Post http://127.0.0.1:8000/backtesting/run/XAUUSD
Invoke-RestMethod http://127.0.0.1:8000/backtesting/results/recent
```
