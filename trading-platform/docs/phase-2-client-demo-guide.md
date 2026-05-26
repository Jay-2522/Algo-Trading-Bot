# Phase 2 Client Demo Guide

## What To Show First

Open the concise report first:

```text
http://127.0.0.1:8000/institutional/demo/XAUUSD
```

Explain that the platform detects institutional structure, grades simulation opportunities, and prevents weak or unsafe simulated decisions from advancing.

## Recommended Demo Order

1. `http://127.0.0.1:8000/institutional/demo/XAUUSD`
2. `http://127.0.0.1:8000/institutional/dashboard/XAUUSD`
3. `http://127.0.0.1:8000/institutional/reasoning/summary/XAUUSD`
4. `http://127.0.0.1:8000/institutional/performance/XAUUSD`
5. `http://127.0.0.1:8000/institutional/phase2/completion-report`
6. `http://127.0.0.1:8000/institutional/phase2/safety-audit`

Additional presentation endpoints:

```text
http://127.0.0.1:8000/institutional/demo/summary/XAUUSD
http://127.0.0.1:8000/institutional/demo/modules/XAUUSD
http://127.0.0.1:8000/institutional/demo/talking-points/XAUUSD
```

## Explaining Statuses

- `READY_FOR_SIMULATION`: The evidence and gates support a paper-only assessment.
- `WAIT`: Structure or timing needs more confirmation.
- `AVOID`: Current institutional conditions are not sufficiently aligned.
- `MONITOR`: No high-quality simulated setup is currently present.
- `MANAGE_POSITION`: The platform is managing an existing paper position, not seeking a new entry.

Blocked and no-trade states are useful outcomes: they demonstrate restraint, transparent validation, and risk discipline rather than system failure.

## Explaining Simulation-Only Mode

Use this language:

- The system is operating in simulation-only institutional intelligence mode.
- The platform identifies market structure and validates hypothetical setups.
- Broker execution remains disabled.
- Safety audits confirm the institutional module cannot submit live orders.

## What Not To Promise

- Do not describe simulation decisions as live signals or executed positions.
- Do not promise profitability or guaranteed prediction accuracy.
- Do not imply that broker trading can be enabled from these endpoints.
- Do not present limited simulation history as validated live performance.
