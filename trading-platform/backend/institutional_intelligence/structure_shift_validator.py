from math import isfinite
from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_models import StructureEvent, StructureValidationResult


class StructureShiftValidator:
    """Validate that each event reflects an actual swing-level price break."""

    def validate_event(
        self,
        event: StructureEvent,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None,
    ) -> StructureValidationResult:
        if event.event_type not in {"BOS", "CHOCH", "MSS"} or event.direction not in {"BULLISH", "BEARISH"}:
            return self._invalid("Unsupported event type or direction.")
        if not isfinite(event.break_level) or not candles or event.candle_index >= len(candles):
            return self._invalid("Break level or candle index is invalid.")
        reference = self._reference(event, swings or [])
        if reference is None:
            return self._invalid("No valid swing reference is linked to the structure event.")
        values = self._values(candles[event.candle_index])
        if values is None:
            return self._invalid("Structure break candle contains malformed OHLC values.")
        if event.direction == "BULLISH":
            close_confirmed = values["close"] > event.break_level
            wick_break = values["high"] > event.break_level
        else:
            close_confirmed = values["close"] < event.break_level
            wick_break = values["low"] < event.break_level
        if not close_confirmed and not wick_break:
            return self._invalid("Price did not break the referenced swing level.")
        break_strength = 100.0 if close_confirmed else 40.0
        return StructureValidationResult(
            valid=True,
            close_confirmed=close_confirmed,
            wick_break=not close_confirmed and wick_break,
            break_strength=break_strength,
            reason=(
                "Swing level closed through with structure confirmation."
                if close_confirmed
                else "Swing level was probed by wick only; structure break is weak."
            ),
        )

    def _reference(self, event: StructureEvent, swings: list[SwingPoint]) -> SwingPoint | None:
        reference_index = event.swing_reference.get("index")
        reference_price = event.swing_reference.get("price")
        return next(
            (
                swing
                for swing in swings
                if swing.index == reference_index and swing.price == reference_price
            ),
            None,
        )

    def _invalid(self, reason: str) -> StructureValidationResult:
        return StructureValidationResult(
            valid=False,
            close_confirmed=False,
            wick_break=False,
            break_strength=0.0,
            reason=reason,
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()) or values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
