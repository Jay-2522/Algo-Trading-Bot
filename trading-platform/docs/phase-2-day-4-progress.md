# Phase 2 Day 4 Progress

## Order Block Detection Engine

Phase 2 Day 4 adds an analysis-only institutional order block engine. It identifies the final opposing candle before measurable displacement, validates break of structure (BOS), tracks later zone mitigation, and supplies deterministic confluence context for future research and AI ranking. It creates no orders and does not alter execution permissions.

## Order Block Logic

### Bullish Order Block

A bullish order block is the last bearish candle immediately preceding qualifying bullish displacement. Its full candle range becomes the demand zone:

- `zone_high`: bearish candle high
- `zone_low`: bearish candle low
- `direction`: `BULLISH`

### Bearish Order Block

A bearish order block is the last bullish candle immediately preceding qualifying bearish displacement. Its full candle range becomes the supply zone:

- `zone_high`: bullish candle high
- `zone_low`: bullish candle low
- `direction`: `BEARISH`

## Displacement And BOS

Displacement must occur within the next three candles and is deterministic:

- impulse range is at least `1.5` times the average range of up to five preceding candles
- impulse candle body is at least `60%` of its range
- impulse close direction must agree with the proposed block direction

BOS validation requires a close beyond preceding structure after the order block:

- bullish blocks require a close above a preceding swing-reference high
- bearish blocks require a close below a preceding swing-reference low

Detected impulse candidates remain visible with `valid: false` if BOS is not confirmed. Classified, latest, and confidence collections use validated blocks.

## Mitigation Lifecycle

- `FRESH`: candles after displacement do not revisit the order block zone.
- `PARTIAL`: subsequent price enters the zone without crossing its far boundary.
- `MITIGATED`: subsequent price trades through the entire zone.

For bullish blocks, depth is measured from `zone_high` down toward `zone_low`. For bearish blocks, it is measured from `zone_low` up toward `zone_high`. Percentage is capped at `100`.

## Strength And Confluence

Strength is explainable and bounded to `0-100`:

- displacement expansion and body quality: up to `25`
- BOS confirmation: `25`
- freshness state: up to `20`
- remaining unmitigated zone: up to `15`
- FVG, liquidity sweep, and structural-bias confluence: up to `15`

Confluence awards `5` points each for a directionally aligned fresh FVG created near the block, a recent validated directionally aligned sweep, and matching structure bias. Fully mitigated blocks receive no freshness score and no remaining-zone score.

## Delivered Components

- `order_block_models.py`: order block, validation, mitigation, strength, and context contracts.
- `order_block_detector.py`: bullish and bearish impulse-origin detection.
- `order_block_validator.py`: displacement and BOS verification.
- `order_block_mitigation_tracker.py`: fresh, partial, and full lifecycle tracking.
- `order_block_strength_scorer.py`: deterministic strength and confluence ranking.
- `order_block_context_builder.py`: dashboard-ready aggregation.
- Updated SMC service, API routes, system readiness and route audits, regression protection, and README.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/order-blocks/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/order-blocks/context/XAUUSD?timeframe=M15`

The context endpoint combines order blocks, FVG context, liquidity sweeps, and structure bias in one JSON-safe analysis response.

## Safety Protections

- The order block engine consumes candles only.
- No broker submission or live execution functionality is introduced.
- `simulation_only` remains `true` and `live_execution_enabled` remains `false`.
- Missing MT5 candle access returns empty typed contexts without requiring MT5.
- All Phase 1 and previous Phase 2 endpoint contracts remain protected.
- `institutional_order_blocks` is an observational readiness module.

## Verification

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

## Next Direction

Phase 2 can next compose order blocks, FVGs, liquidity raids, dealing-range position, session timing, and displacement into a multi-timeframe analytical ranking layer while retaining the existing non-executable boundary.
