# Phase 16 Day 4 Demo Execution Simulator

## What The Simulator Does

The demo execution simulator shows what would happen if a DEMO order were submitted in a future phase. It consumes the latest passed preflight result, builds a virtual order payload, and returns estimated risk, reward, risk/reward ratio, and margin.

## What The Simulator Does Not Do

The simulator does not send orders, does not interact with broker execution, does not enable live trading, and does not unlock execution. It is a virtual execution engine only.

## Risk Estimation Logic

Risk is estimated from the absolute distance between entry price and stop loss, multiplied by lot size and a simple contract-size estimate. The value is labeled estimated because exact broker risk depends on account currency, symbol specification, contract size, tick value, and broker margin rules.

## Reward Estimation Logic

Reward is estimated from the absolute distance between entry price and take profit, multiplied by lot size and the same simple contract-size estimate. Risk/reward ratio is estimated as reward divided by risk when risk is greater than zero.

## Margin Estimation Logic

Margin is estimated from notional value divided by an assumed leverage estimate. This is not a broker quote and must not be used as a production margin guarantee.

## Why No Order Is Sent

Phase 16 Day 4 is still simulation-only. Every simulator response preserves:

- `would_send_to_mt5 = false`
- `mt5_order_sent = false`
- `execution_allowed = false`
- `simulation_only = true`
- `live_execution_enabled = false`
- `broker_execution_enabled = false`

Future DEMO execution must add a separate guarded sender, fresh authorization, final risk checks, and explicit DEMO-only protections before any order submission is considered.
