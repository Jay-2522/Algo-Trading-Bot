# Phase 2 Day 5 Progress

## Breaker Block Detection Engine

Phase 2 Day 5 adds an analysis-only breaker block engine to institutional intelligence. A breaker begins with a previously validated order block that later fails through an opposite-direction displacement close. The failed zone is then represented as a possible reaction area for research, dashboarding, and future ranking models only.

## Breaker Logic

### Bullish Breaker

A bullish breaker forms when:

- a valid bearish order block exists
- a later bullish candle closes above that bearish block's `zone_high`
- the closing break is expanded bullish displacement
- the original bearish supply zone is converted into a bullish breaker zone

### Bearish Breaker

A bearish breaker forms when:

- a valid bullish order block exists
- a later bearish candle closes below that bullish block's `zone_low`
- the closing break is expanded bearish displacement
- the original bullish demand zone is converted into a bearish breaker zone

Every breaker records `source_order_block_id`, its original OB direction, the invalidation candle index, and break price. The detector emits at most one first-confirmed breaker per failed source order block.

## Structure Shift Confirmation

The invalidating candle must close beyond the failed OB boundary and satisfy deterministic displacement requirements:

- impulse range is at least `1.5` times the recent average candle range
- impulse body is at least `60%` of its range
- impulse direction matches the breaker direction

Validation rejects missing source OBs, unvalidated source OBs, malformed candles, out-of-sequence invalidations, and closes that remain inside the original zone.

## Mitigation Lifecycle

Mitigation is evaluated after the breaker-forming displacement candle:

- `FRESH`: the converted reaction zone has not been revisited.
- `PARTIALLY_MITIGATED`: price entered the zone without crossing the far boundary.
- `MITIGATED`: price traversed the complete breaker zone.

For bullish breakers, subsequent lows measure depth into the zone. For bearish breakers, subsequent highs measure depth. Mitigation percentage is capped at `100`.

## Strength And Confluence

Breaker strength is deterministic and bounded from `0` to `100`:

- invalidation displacement quality: up to `25`
- confirmed market structure shift: `25`
- freshness: up to `20`
- remaining unmitigated zone: up to `15`
- FVG, sweep, and structure-bias confluence: up to `15`

Confluence awards `5` points each for a directionally aligned fresh FVG near invalidation, a recent validated aligned liquidity sweep, and matching structure bias. A breaker is high quality at `strength >= 75`.

## Delivered Components

- `breaker_block_models.py`: typed breaker, validation, mitigation, score, and aggregate contracts.
- `breaker_block_detector.py`: failed valid-OB conversion detection.
- `breaker_block_validator.py`: source linkage, displacement close, and structure-shift validation.
- `breaker_block_mitigation_tracker.py`: fresh, partial, and full reaction-zone lifecycle.
- `breaker_block_strength_scorer.py`: bounded confluence-aware ranking.
- `breaker_block_context_builder.py`: dashboard-ready breaker context aggregation.
- Updated SMC service, institutional API, readiness registry, route auditing, regression verification, and README.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/breakers/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/breakers/context/XAUUSD?timeframe=M15`

The combined context response contains breakers, source order blocks, FVGs, liquidity sweeps, structure bias, and explicit simulation-only flags.

## Safety Protections

- Breakers consume candle-derived institutional context only.
- No real orders, broker trading calls, or live-execution changes are introduced.
- `simulation_only` remains `true` and `live_execution_enabled` remains `false`.
- MT5 absence safely returns empty typed breaker context.
- Existing Phase 1 and Phase 2 routes remain under regression and route-audit protection.
- System readiness reports `institutional_breaker_blocks` as analysis-only.

## Verification

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

## Next Direction

Subsequent Phase 2 work can detect mitigation blocks or assemble OB, breaker, FVG, sweep, dealing-range, and session context into multi-timeframe analytical setup ranking while preserving the non-executable boundary.
