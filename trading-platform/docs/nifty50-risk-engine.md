# NIFTY50 Risk Engine

## Purpose

The NIFTY50 risk engine qualifies or rejects trade candidates from strategy snapshots. It does not execute trades.

## Rejection Rules

The risk engine rejects when:

- confidence is below 70
- strategy bias is neutral
- regime is unknown
- no market data is available
- unexpected live or broker execution flags are enabled

## Qualification Rules

If risk analysis passes:

- bullish strategy bias qualifies a BUY candidate
- bearish strategy bias qualifies a SELL candidate
- all other cases return WAIT

## Execution Boundary

`execution_allowed=false` is enforced in every risk decision and trade candidate.

The phase does not connect broker APIs, place orders, or enable live execution.
