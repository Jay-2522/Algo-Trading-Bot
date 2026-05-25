# Phase 2 Day 2 Progress

## Liquidity Sweep Detection

Phase 2 Day 2 adds an analysis-only liquidity sweep layer on top of the institutional liquidity pools delivered on Day 1. It identifies candle rejections through mapped liquidity levels and returns structured context for later research and entry-model design.

## Sweep Logic

### Bullish Sweep

A bullish sweep is recorded when a candle trades below an equal-low or previous-low liquidity level, prints a lower wick through that level, and closes back above it. This represents a modeled rejection of sell-side liquidity.

### Bearish Sweep

A bearish sweep is recorded when a candle trades above an equal-high or previous-high liquidity level, prints an upper wick through that level, and closes back below it. This represents a modeled rejection of buy-side liquidity.

Generic internal and external pools are evaluated by their observed rejection direction rather than assigned an assumed high-side or low-side direction.

## Validation And Scoring

- Detection only evaluates candles after the related liquidity pool has formed.
- A liquidity pool records its first validated sweep only; later candles do not repeatedly count consumed liquidity.
- A valid sweep requires a level cross, close-back-inside validation, and a non-zero rejection wick.
- Rejection strength measures wick size relative to the candle range.
- Sweep strength is bounded from `0` to `100` and combines wick rejection, close-back-inside quality, liquidity pool strength, and swept-side penetration distance.
- High-quality sweep context uses a score threshold of `70`.

## Delivered Components

- `liquidity_sweep_models.py`: sweep, validation, and aggregate context models.
- `sweep_validator.py`: cross, close-back-inside, and wick rejection validation.
- `sweep_strength_scorer.py`: bounded quality scoring.
- `liquidity_sweep_detector.py`: pool-aware sweep discovery.
- `sweep_context_builder.py`: latest, directional, high-quality, and confidence aggregation.
- Updated `smc_service.py`: live read-only candle integration with safe empty fallback.
- Updated institutional API and system-health route/readiness coverage.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/sweeps/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/latest-sweep/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/high-quality-sweeps/XAUUSD?timeframe=M15`

## Safety Protections

- Liquidity sweep detection analyzes candles and mapped liquidity levels only.
- No order creation, execution, or broker submission is involved.
- `simulation_only` remains true and `live_execution_enabled` remains false.
- Missing candle availability returns an empty JSON-safe `SweepContext`.
- Existing Phase 1 and Phase 2 Day 1 endpoints remain registered.
- System health includes `institutional_liquidity_sweeps` as an observational module.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

## Next Direction

The next institutional layer can analyze order blocks and fair value gaps, then combine them with validated sweep context and displacement observations for confluence research while retaining the non-executable safety boundary.
