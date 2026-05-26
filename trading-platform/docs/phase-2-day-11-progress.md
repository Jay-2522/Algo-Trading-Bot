# Phase 2 Day 11: Trade Setup Validator and Execution Readiness Engine

## Purpose

Day 11 is the final institutional approval gate before a setup can be labelled eligible for simulation. It validates Day 10 entry models against alignment, session/news timing, confluence, risk, and structural integrity. It is not an order execution layer.

## Validation Pipeline

1. Validate higher-timeframe alignment.
2. Validate session timing, killzone quality, liquidity, and news restriction.
3. Validate institutional confluence direction and quality.
4. Validate defined risk geometry, analytical reward-to-risk, and operational risk status.
5. Validate actionable entry-model structure.
6. Aggregate visible rule scores and critical failures.
7. Produce an institutional approval decision.

Every gate returns a typed rule with category, pass/fail state, score, severity, and explanation.

## Gatekeeper Rules

### Alignment

- Fully aligned, same-direction higher-timeframe evidence receives the strongest approval support.
- Neutral or incomplete alignment creates a warning and confirmation requirement.
- Conflicted or opposing alignment is a critical rejection.

### Session And News

- An active high-quality killzone supports approval.
- Missing timing quality lowers readiness.
- Low or poor session liquidity is a critical rejection.
- An active news blackout is a critical rejection.

### Confluence

- Same-direction confluence with score `>= 75` and sufficient confidence passes.
- Moderate confluence creates a warning and conditional posture.
- Weak, conflicted, or opposing confluence is rejected.

### Risk And Structure

- Entry zone, invalidation, and target must be defined.
- Analytical reward-to-risk must be at least `1.5`.
- Blocked risk controls reject simulation eligibility.
- `NO_TRADE` models or malformed zones cannot pass structural integrity.

## Approval Grades

| Grade | Requirements | Simulation Eligibility |
| --- | --- | --- |
| `INSTITUTIONAL_A_PLUS` | Score `>= 85`, confidence `>= 80`, all critical gates passed | Eligible |
| `INSTITUTIONAL_A` | Score `>= 75`, approval gates passed | Eligible |
| `INSTITUTIONAL_B` | Score `>= 65`, requires further confirmation | Not eligible |
| `LOW_QUALITY` | Score `>= 45`, weak quality | Not eligible |
| `REJECTED` | Critical failure or score below threshold | Not eligible |

`execution_readiness` refers only to readiness for the existing simulation workflow. No order-routing capability is introduced.

## API Routes

- `GET http://127.0.0.1:8000/institutional/setup-validation/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/setup-validation/approved/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/setup-validation/waiting/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/setup-validation/rejected/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/setup-validation/best/XAUUSD`
- `GET http://127.0.0.1:8000/institutional/setup-validation/readiness/XAUUSD`

## Safety Protections

- Analysis-only and simulation-only.
- No broker order placement.
- No live execution enablement.
- No autonomous trading activation.
- Unavailable MT5 or missing evidence returns rejection, never implied eligibility.
- System readiness and route audit monitoring include the validation module.

## Verification

```powershell
python tests/regression_routes_verification.py
python tests/phase2_day11_verification.py
python -c "from backend.main import app; print([r.path for r in app.routes if 'institutional' in r.path])"
```
