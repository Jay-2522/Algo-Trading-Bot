# Phase 20 Day 3 - XAUUSD MT5 Diagnostics

## Purpose

Day 2 showed `mt5.symbol_select("XAUUSD", True)` returning `(-3, "Terminal: Out of memory")` even though the MT5 UI showed XAUUSD in Market Watch with live prices and Full Access trade mode.

This phase adds a read-only diagnostics endpoint and changes symbol availability classification so a visible `symbol_info("XAUUSD")` is not incorrectly reported as unavailable only because `symbol_select()` failed.

## Diagnostics Endpoint

`GET /mt5-demo/diagnostics/xauusd`

The endpoint returns:

- account login
- server
- terminal path
- terminal build
- terminal symbol count
- MT5 Python package version tuple when available
- `symbol_info("XAUUSD")`
- `symbol_info_tick("XAUUSD")`
- symbol visibility
- `symbol_select("XAUUSD", True)` result
- `mt5.last_error()`
- initialization state
- diagnostic report

## Classification Model

The market-data service now distinguishes:

- `SYMBOL_NOT_FOUND`: `symbol_info()` returned `None`.
- `SYMBOL_HIDDEN`: `symbol_info()` exists, visible is false, and `symbol_select()` failed.
- `SYMBOL_AVAILABLE`: `symbol_info()` exists and the symbol is visible or was successfully selected.
- `SYMBOL_AVAILABLE_SELECT_FAILED`: `symbol_info()` exists and visible is true, but `symbol_select()` failed.
- `SYMBOL_TICK_UNAVAILABLE`: symbol exists, but MT5 did not return a usable tick.

## Root-Cause Logic

When `symbol_info("XAUUSD")` exists and `visible=true`, the symbol is available to the terminal. In that case, a `symbol_select()` failure is treated as a terminal/API warning, not proof that XAUUSD is unavailable.

The specific `(-3, "Terminal: Out of memory")` error therefore means the MT5 API could not complete the selection request, while the symbol can still be considered present if `symbol_info()` confirms it.

## Safety

This phase is read-only:

- no orders are placed
- no positions are closed
- no `mt5.order_send` path is added
- live trading remains disabled
- broker execution remains disabled
