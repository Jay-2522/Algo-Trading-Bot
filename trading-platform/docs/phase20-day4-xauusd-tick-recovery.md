# Phase 20 Day 4 - XAUUSD Tick Retrieval Recovery

## Goal

Recover XAUUSD market-data readiness when MT5 confirms the symbol is visible, but `mt5.symbol_select("XAUUSD", True)` fails with the terminal memory warning.

## Recovery Order

The MT5 demo market-data service now attempts quote recovery in this order:

1. `mt5.symbol_info_tick("XAUUSD")`
2. `mt5.symbol_info("XAUUSD").bid` and `.ask`
3. Honest blocked state when no reliable bid/ask exists

No price is generated or estimated. A quote is considered usable only when bid and ask are positive numbers and ask is greater than bid.

## Recovery Classifications

- `TICK_AVAILABLE_DIRECT`: bid/ask recovered from `symbol_info_tick`.
- `TICK_AVAILABLE_FROM_SYMBOL_INFO`: bid/ask recovered from `symbol_info` fields.
- `TICK_STILL_UNAVAILABLE`: no reliable bid/ask was available.
- `TERMINAL_MEMORY_WARNING`: represented by `terminal_memory_warning=true` when MT5 reports the `(-3, "Terminal: Out of memory")` condition.

## Updated Tick Response

`GET /mt5-demo/market-data/tick/XAUUSD` now includes:

- `symbol`
- `bid`
- `ask`
- `spread`
- `source`
- `tick_recovery_status`
- `symbol_availability`
- `mt5_last_error`
- `terminal_memory_warning`

If direct tick or `symbol_info` bid/ask is available, the route returns `status=OK` and `freshness=READY`.

If no reliable quote exists, the route returns `status=SYMBOL_TICK_UNAVAILABLE` and keeps execution blocked.

## Diagnostics Extension

`GET /mt5-demo/diagnostics/xauusd` now includes:

- `direct_tick_result`
- `symbol_info_bid`
- `symbol_info_ask`
- `symbol_info_last`
- `calculated_spread`
- `recovery_status`
- `terminal_memory_warning`

## Safety

This phase remains read-only:

- no orders are placed
- no positions are closed
- no unrestricted `mt5.order_send` path is added
- live execution remains disabled
- broker execution remains disabled
