# Phase 2 Day 6 Progress

## Market Structure Shift, BOS And CHOCH Engine

Phase 2 Day 6 adds a typed, analysis-only structure-event layer. It transforms existing swing observations into Break of Structure (`BOS`), Change of Character (`CHOCH`), and Market Structure Shift (`MSS`) events, then enriches each event with confluence from liquidity sweeps, FVGs, order blocks, breaker blocks, and structure bias.

## BOS Logic

A BOS represents directional continuation through a prior swing level:

- Bullish BOS: price breaks a registered swing high.
- Bearish BOS: price breaks a registered swing low.
- A close beyond the swing level is classified as a strong confirmed break.
- A wick through the level without a close is retained as a weak analytical break.
- Each directional swing level is consumed only once to prevent duplicate events.

Continuation classification uses prior same-type swing progression where available: higher highs support bullish continuation and lower lows support bearish continuation.

## CHOCH Logic

A CHOCH represents the first counter-structure failure against the prior market bias:

- Bullish CHOCH: in bearish or ranging structure, price breaks a confirmed lower high.
- Bearish CHOCH: in bullish or ranging structure, price breaks a confirmed higher low.

A CHOCH must reference an actual swing with a preceding same-type swing so isolated levels are not mislabeled as character changes. Close confirmation is preferred; wick-only probes remain visible at reduced quality.
When the aggregate builder does not possess a historical prior-bias snapshot, it infers the counter-structure condition from sequential lower highs or higher lows rather than using the final post-break bias.

## MSS Logic

MSS promotes a reversal indication into a confirmed structural transition:

- CHOCH accompanied by deterministic displacement on the break candle; or
- CHOCH followed within five candles by a close-confirmed BOS in the new direction.

Displacement uses the existing institutional standard: range expansion of at least `1.5` times recent average range and body size of at least `60%` of candle range.

## Validation

Every event must contain:

- a supported `BOS`, `CHOCH`, or `MSS` classification
- a supported `BULLISH` or `BEARISH` direction
- a valid candle index and finite break level
- an existing indexed swing reference
- an observed close or wick break through that referenced swing

Close-confirmed events receive a stronger validation result than wick-only breaks. Malformed candle data is ignored safely.

## Strength Scoring

Scores are deterministic and bounded to `0-100`:

- close confirmation quality: up to `25`
- broken swing strength: up to `20`
- break-candle displacement: up to `20`
- continuation or reversal quality: up to `15`
- institutional confluence: up to `20`

Confluence awards `5` points each for:

- a nearby directionally aligned liquidity sweep
- an aligned fresh FVG created around the break
- an aligned order block or breaker zone
- alignment with current structure bias

Events with `strength >= 75` are exposed as high quality.

## Current Structure State

The context reports one dashboard-ready state:

- `BULLISH`: latest confirmed continuation or MSS is bullish.
- `BEARISH`: latest confirmed continuation or MSS is bearish.
- `TRANSITIONING`: latest valid event is CHOCH without MSS confirmation.
- `RANGING`: supplied bias remains ranging with no newer event.
- `UNCLEAR`: no evaluable directional structure exists.

## Delivered Components

- `structure_shift_models.py`: event, aggregate, validation, and score contracts.
- `bos_detector.py`: first-break swing continuation detection.
- `choch_detector.py`: counter-bias character-change detection.
- `structure_shift_detector.py`: combined BOS/CHOCH detection and MSS promotion.
- `structure_shift_validator.py`: swing-linked break verification.
- `structure_shift_strength_scorer.py`: bounded event quality and confluence scoring.
- `structure_shift_context_builder.py`: typed aggregate and current-state reporting.
- Updated SMC service, API routing, readiness and route audits, route regression coverage, and README.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/structure-shift/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/bos/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/choch/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/mss/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/latest/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/structure-shift/context/XAUUSD?timeframe=M15`

The combined context response includes structure events, sweeps, FVGs, order blocks, breaker blocks, structure bias, and explicit safety flags.

## Safety Protections

- The engine observes candle and derived institutional context only.
- No broker order submission or autonomous trading behavior is introduced.
- `simulation_only` remains `true`.
- `live_execution_enabled` remains `false`.
- Missing MT5 data returns an empty typed structure context.
- Previous Phase 1 and Phase 2 endpoint contracts remain protected by verification and route audit.
- System readiness reports `institutional_structure_shift` as analysis-only.

## Verification

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

## Next Direction

The next institutional layer can add inducement and liquidity-target sequencing, or build a multi-timeframe analytical ranking engine combining structure shifts, breakers, order blocks, imbalances, sweeps, and dealing-range position without enabling execution.
