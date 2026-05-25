from math import isfinite
from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_models import StructureEvent, StructureStrengthScore


class StructureShiftStrengthScorer:
    """Score validated structure breaks using quality and aligned context."""

    def score_event(
        self,
        event: StructureEvent,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None,
        sweep_context: Any = None,
        fvg_context: Any = None,
        ob_context: Any = None,
        breaker_context: Any = None,
        structure_bias: Any = None,
    ) -> StructureStrengthScore:
        close_score = 25.0 if event.close_confirmed else 8.0 if event.wick_break else 0.0
        swing_score = self._swing_score(event, swings or [])
        displacement_score = self._displacement_score(event, candles or [])
        quality_score = 15.0 if event.event_type == "MSS" else 13.0 if event.continuation or event.reversal else 6.0
        sweep_id = self.find_related_sweep(event, sweep_context)
        fvg_id = self.find_related_fvg(event, fvg_context)
        ob_id = self.find_related_order_block(event, ob_context)
        breaker_id = self.find_related_breaker(event, breaker_context)
        aligned_zone = ob_id or breaker_id
        bias_aligned = self._bias(structure_bias) == event.direction
        confluence_score = (
            (5.0 if sweep_id else 0.0)
            + (5.0 if fvg_id else 0.0)
            + (5.0 if aligned_zone else 0.0)
            + (5.0 if bias_aligned else 0.0)
        )
        score = round(min(close_score + swing_score + displacement_score + quality_score + confluence_score, 100.0), 2)
        return StructureStrengthScore(
            score=score,
            close_confirmation_score=close_score,
            swing_strength_score=swing_score,
            displacement_score=displacement_score,
            confluence_score=confluence_score,
            continuation_reversal_score=quality_score,
            reason=(
                f"{event.event_type} {event.direction.lower()} break; close={event.close_confirmed}, "
                f"sweep={bool(sweep_id)}, FVG={bool(fvg_id)}, zone={bool(aligned_zone)}, bias_aligned={bias_aligned}."
            ),
        )

    def find_related_sweep(self, event: StructureEvent, context: Any) -> str | None:
        tolerance = max(abs(event.break_level) * 0.005, 0.0001)
        for sweep in reversed(self._items(context, "sweeps")):
            level = self._get(sweep, "swept_level")
            if (
                self._get(sweep, "valid")
                and self._get(sweep, "direction") == event.direction
                and level is not None
                and abs(float(level) - event.break_level) <= tolerance
                and abs(int(self._get(sweep, "candle_index")) - event.candle_index) <= 5
            ):
                return self._get(sweep, "sweep_id")
        return None

    def find_related_fvg(self, event: StructureEvent, context: Any) -> str | None:
        for fvg in self._items(context, "fresh_fvgs"):
            start_index = self._get(fvg, "start_index")
            if self._get(fvg, "direction") == event.direction and start_index is not None:
                if event.candle_index - 1 <= int(start_index) <= event.candle_index + 3:
                    return self._get(fvg, "fvg_id")
        return None

    def find_related_order_block(self, event: StructureEvent, context: Any) -> str | None:
        for order_block in reversed(self._items(context, "order_blocks")):
            index = self._get(order_block, "candle_index")
            if self._get(order_block, "valid") and self._get(order_block, "direction") == event.direction and index is not None:
                if int(index) <= event.candle_index <= int(index) + 6:
                    return self._get(order_block, "ob_id")
        return None

    def find_related_breaker(self, event: StructureEvent, context: Any) -> str | None:
        for breaker in reversed(self._items(context, "breaker_blocks")):
            index = self._get(breaker, "candle_index")
            if self._get(breaker, "valid") and self._get(breaker, "direction") == event.direction and index is not None:
                if abs(int(index) - event.candle_index) <= 5:
                    return self._get(breaker, "breaker_id")
        return None

    def _swing_score(self, event: StructureEvent, swings: list[SwingPoint]) -> float:
        strength = float(event.swing_reference.get("strength", 0.0))
        available = [float(swing.strength) for swing in swings if isfinite(float(swing.strength))]
        average = sum(available) / len(available) if available else 0.0
        if average <= 0:
            return 10.0 if strength > 0 else 0.0
        return round(min(strength / average * 12.0, 20.0), 2)

    def _displacement_score(self, event: StructureEvent, candles: list[Any]) -> float:
        if event.candle_index >= len(candles):
            return 0.0
        current = self._values(candles[event.candle_index])
        prior = [self._values(candle) for candle in candles[max(0, event.candle_index - 5) : event.candle_index]]
        recent = [value for value in prior if value is not None]
        if current is None or len(recent) < 2:
            return 0.0
        average_range = sum(value["high"] - value["low"] for value in recent) / len(recent)
        candle_range = current["high"] - current["low"]
        body = abs(current["close"] - current["open"])
        if average_range <= 0 or candle_range <= 0:
            return 0.0
        expansion = min(candle_range / (average_range * 2.0), 1.0)
        body_quality = min(body / candle_range, 1.0)
        return round(20.0 * ((expansion + body_quality) / 2.0), 2)

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        value = context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])
        return list(value or [])

    def _get(self, item: Any, key: str) -> Any:
        return item.get(key) if isinstance(item, dict) else getattr(item, key, None)

    def _bias(self, context: Any) -> str | None:
        if isinstance(context, str):
            return context
        if isinstance(context, dict):
            return context.get("bias")
        return getattr(context, "bias", None)

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            return values if all(isfinite(value) for value in values.values()) and values["high"] >= values["low"] else None
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
