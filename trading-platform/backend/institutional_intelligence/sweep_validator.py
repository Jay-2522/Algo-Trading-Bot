from typing import Any

from backend.institutional_intelligence.liquidity_sweep_models import SweepValidationResult
from backend.institutional_intelligence.smc_models import LiquidityPool


class SweepValidator:
    """Validate rejection of a mapped liquidity level using candle geometry."""

    HIGH_POOLS = {"EQUAL_HIGHS", "PREVIOUS_HIGH"}
    LOW_POOLS = {"EQUAL_LOWS", "PREVIOUS_LOW"}

    def validate_sweep(self, candle: Any, pool: LiquidityPool) -> SweepValidationResult:
        values = self.values(candle)
        if values is None:
            return SweepValidationResult(
                valid=False,
                close_back_inside=False,
                wick_rejection=False,
                reason="Malformed candle data.",
            )
        directions = self._candidate_directions(pool)
        results = [self._validate_direction(values, pool.price_level, direction) for direction in directions]
        return max(results, key=lambda item: (item.valid, item.rejection_strength))

    def direction(self, candle: Any, pool: LiquidityPool) -> str | None:
        values = self.values(candle)
        if values is None:
            return None
        results = [
            (direction, self._validate_direction(values, pool.price_level, direction))
            for direction in self._candidate_directions(pool)
        ]
        direction, result = max(results, key=lambda item: (item[1].valid, item[1].rejection_strength))
        return direction if result.valid else None

    def values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None

    def _candidate_directions(self, pool: LiquidityPool) -> list[str]:
        if pool.liquidity_type in self.HIGH_POOLS:
            return ["BEARISH"]
        if pool.liquidity_type in self.LOW_POOLS:
            return ["BULLISH"]
        return ["BEARISH", "BULLISH"]

    def _validate_direction(self, values: dict, level: float, direction: str) -> SweepValidationResult:
        candle_range = max(values["high"] - values["low"], 0.0)
        if direction == "BEARISH":
            crossed = values["high"] > level
            close_inside = values["close"] < level
            wick = values["high"] - max(values["open"], values["close"], level)
        else:
            crossed = values["low"] < level
            close_inside = values["close"] > level
            wick = min(values["open"], values["close"], level) - values["low"]
        wick_rejection = wick > 0
        rejection_strength = round(min(max(wick / candle_range * 100, 0.0), 100.0), 2) if candle_range else 0.0
        valid = crossed and close_inside and wick_rejection and rejection_strength > 0
        if not crossed:
            reason = "Candle did not cross liquidity level."
        elif not close_inside:
            reason = "Candle did not close back inside liquidity level."
        elif not wick_rejection:
            reason = "No wick rejection beyond liquidity level."
        else:
            reason = "Liquidity sweep validated with close-back-inside rejection."
        return SweepValidationResult(
            valid=valid,
            close_back_inside=close_inside,
            wick_rejection=wick_rejection,
            rejection_strength=rejection_strength,
            reason=reason,
        )
