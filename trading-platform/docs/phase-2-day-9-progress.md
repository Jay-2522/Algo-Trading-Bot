# Phase 2 Day 9: Session and Killzone Intelligence Engine

## Purpose

Day 9 adds deterministic time-of-day context to institutional analysis. It evaluates whether observed liquidity and manipulation occur during meaningful UTC participation windows and returns simulation-readiness guidance only.

## Session Ranges

| Session | UTC Window | Use |
| --- | --- | --- |
| Asian | 00:00-09:00 | Initial liquidity range and raid reference |
| London | 07:00-16:00 | European expansion and Asian-range manipulation |
| New York | 12:00-21:00 | US expansion and reversal assessment |

The range detector calculates high, low, midpoint, and range size from valid OHLC candles. A session range is valid only when at least two valid candles are available.

## Killzones

| Killzone | UTC Window | Liquidity Classification |
| --- | --- | --- |
| London Open | 07:00-10:00 | High liquidity |
| New York Open | 12:00-15:00 | High liquidity |
| London Close | 15:00-16:00 | Normal liquidity |

Outside those periods the active killzone is `NONE`.

## Liquidity And Manipulation Logic

Liquidity quality is derived from session range expansion relative to observed candle range, strengthened when existing validated liquidity sweeps are present.

Manipulation detection is deterministic:

- A later London or New York candle that trades above the valid Asian high and closes back below it yields a bearish `ASIAN_HIGH_SWEEP`.
- A later London or New York candle that trades below the valid Asian low and closes back above it yields a bullish `ASIAN_LOW_SWEEP`.
- A London Asian-range rejection is also identified as `LONDON_FAKEOUT`.
- A New York rejection of the Asian low is identified as `NEW_YORK_REVERSAL`.
- Related validated sweep direction increases confidence; it does not create a signal without price confirmation.

## Session Quality Scoring

The bounded `0-100` score uses:

| Factor | Maximum Contribution |
| --- | ---: |
| Active killzone | 25 |
| Liquidity profile | 25 |
| Confirmed manipulation signal | 20 |
| Volatility quality | 15 |
| Advisory news status | 15 |

An active news blackout applies a deterministic penalty and prevents a high-quality timing label.

## Readiness Labels

- `HIGH_QUALITY_WINDOW`: active killzone, sufficient liquidity, high score, and no broader conflict.
- `WAIT_FOR_KILLZONE`: acceptable context but no active institutional timing window.
- `AVOID_LOW_LIQUIDITY`: observed liquidity is insufficient.
- `AVOID_NEWS_WINDOW`: advisory news blackout is active.
- `NORMAL_MONITORING`: an active window exists but confluence or alignment is not clean enough.

Confluence and multi-timeframe alignment conflict are incorporated as warnings that prevent a high-quality timing declaration.

## API Routes

- `GET http://127.0.0.1:8000/institutional/session/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/session/ranges/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/session/killzone/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/session/liquidity/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/session/manipulation/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/session/readiness/XAUUSD`

## Safety Boundaries

- Analysis-only and simulation-only.
- No order placement or live broker execution.
- No autonomous trading activation.
- No MT5 dependency is required for tests; missing market data returns safe JSON contexts.
- Session routes are monitored by system readiness and route auditing.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day9_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
