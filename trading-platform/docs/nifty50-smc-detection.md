# NIFTY50 SMC Detection

## Inputs

The NIFTY50 SMC layer reads manually ingested candles from the Phase 12 Day 3 market-data layer.

## Detectors

- `NIFTYSwingDetector` finds simple pivot highs and lows using neighboring candles.
- `NIFTYBOSDetector` detects close-through breaks of the latest swing high or low.
- `NIFTYCHOCHDetector` detects simple trend-change breaks against the prior directional bias.
- `NIFTYRegimeDetector` classifies trend or range state from directional close expansion.
- `NIFTYConfidenceEngine` scores deterministic confluence from liquidity, structure, FVG, order block, and regime.

## Detection Scope

Implemented:

- Swing highs
- Swing lows
- BOS
- CHOCH
- Liquidity sweeps
- Fair value gaps
- Order blocks
- Regime
- Bias
- Confidence

## Safety

This layer does not place orders, connect to brokers, fetch live market data, or enable execution.
