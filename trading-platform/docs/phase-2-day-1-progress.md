# Phase 2 Day 1 Progress

## Institutional Intelligence Foundation

Phase 2 begins with a Smart Money Concepts / ICT-style market-structure intelligence package. It observes candles and returns structured analysis only; it does not submit orders, approve live trading, or change execution controls.

## Delivered Components

- `smc_models.py`: JSON-safe swing, liquidity, bias, dealing-range, displacement, and context models.
- `swing_detector.py`: neighboring-candle swing high and swing low detection with malformed-input tolerance.
- `liquidity_mapper.py`: equal highs, equal lows, previous levels, and internal/external liquidity mapping.
- `structure_bias.py`: bullish, bearish, ranging, or unclear swing-sequence classification.
- `premium_discount.py`: observed dealing range, equilibrium, premium, and discount positioning.
- `displacement_detector.py`: large directional candle-body identification relative to recent range.
- `institutional_context.py`: combined SMC snapshot construction.
- `smc_service.py`: market-data integration with safe empty-context fallback when candles are unavailable.
- `api/institutional_routes.py`: read-only institutional intelligence API.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/status`
- `GET http://127.0.0.1:8000/institutional/context/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/swings/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/liquidity/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/bias/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/premium-discount/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/displacement/XAUUSD?timeframe=M15`

## Analysis Logic

- Swing highs require a candle high above its neighboring highs; swing lows require a low below neighboring lows.
- Equal liquidity pools group swing extremes within a configured absolute tolerance and increase strength with repeated touches.
- External liquidity reflects extreme structural swing levels; internal liquidity represents intervening structural points.
- Bias uses sequences of higher highs and higher lows, or lower highs and lower lows.
- Premium and discount are evaluated relative to the midpoint of the observed candle range.
- Displacement identifies large directional bodies relative to a recent average range.

## Safety Boundary

- Institutional intelligence consumes market data for observation only.
- All endpoint output is modeled and JSON-safe.
- No execution service is invoked.
- Live execution remains disabled and the simulation-only system boundary is unchanged.
- The existing system health registry and route audit now include `/institutional/status`.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

## Next Direction

Future Phase 2 work can build liquidity sweep recognition, order block identification, fair value gap mapping, entry-model confluence, and AI ranking on top of this typed context without loosening execution safeguards.
