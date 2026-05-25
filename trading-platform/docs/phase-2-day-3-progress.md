# Phase 2 Day 3 Progress

## Fair Value Gap And Imbalance Detection

Phase 2 Day 3 adds an analysis-only Fair Value Gap (FVG) engine to the institutional intelligence package. It identifies three-candle imbalance zones, tracks later mitigation, and scores context for future research models without creating or executing orders.

## FVG Logic

### Bullish FVG

A bullish FVG exists when the first candle high is below the third candle low. The untraded zone is:

- `gap_low`: first candle high
- `gap_high`: third candle low

### Bearish FVG

A bearish FVG exists when the first candle low is above the third candle high. The untraded zone is:

- `gap_low`: third candle high
- `gap_high`: first candle low

The model timestamps an FVG at its middle impulse candle and does not evaluate mitigation until the three-candle formation is complete.

## Mitigation Lifecycle

- `FRESH`: no later candle has entered the imbalance zone.
- `PARTIAL`: a later candle has entered the zone but has not traded through its far boundary.
- `MITIGATED`: a later candle has fully traversed the zone boundary.

For bullish FVGs, later lows measure re-entry into the gap. For bearish FVGs, later highs measure re-entry. Mitigation percentage is capped at `100`.

## Strength Scoring

Scores are bounded from `0` to `100` using:

- gap size relative to recent candle range: up to `25`
- middle-candle displacement body quality: up to `25`
- freshness: up to `20`
- remaining unmitigated value: up to `20`
- alignment with current structure bias: up to `10`

Fresh imbalances score higher than comparable fully mitigated gaps. Bias alignment is recorded as context metadata only; it is not an instruction to trade.

## Delivered Components

- `fair_value_gap_models.py`: FVG, context, mitigation, and score contracts.
- `fair_value_gap_detector.py`: robust bullish and bearish three-candle detection.
- `fvg_mitigation_tracker.py`: fresh, partial, and full mitigation tracking.
- `fvg_strength_scorer.py`: bounded quality and confluence scoring.
- `fvg_context_builder.py`: typed aggregate context with latest and high-quality groups.
- Updated `smc_service.py`, institutional API, route audit, and system readiness registry.

## API Endpoints

- `GET http://127.0.0.1:8000/institutional/fvg/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/fresh/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/mitigated/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/high-quality/XAUUSD?timeframe=M15`
- `GET http://127.0.0.1:8000/institutional/fvg/latest/XAUUSD?timeframe=M15`

## Safety Protections

- The FVG engine consumes candle observations only.
- No execution or broker-order capability is introduced.
- `simulation_only` remains true and `live_execution_enabled` remains false.
- Missing candle availability produces an empty JSON-safe `FVGContext`.
- All Phase 1 and previous Phase 2 routes remain registered.
- System health reports `institutional_fvg` as an observational module.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day3_verification.py
python tests/phase2_day2_verification.py
python tests/phase2_day1_verification.py
python tests/day15_verification.py
python tests/phase1_full_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```

## Next Direction

Subsequent Phase 2 work can add order block detection and assemble sweep, FVG, displacement, dealing-range, and structural-bias confluence into a ranked analytical entry model while maintaining the non-executable boundary.
