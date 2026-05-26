from typing import Any

from backend.institutional_intelligence.position_management_models import ManagedPosition, TrailingStopAdjustment


class TrailingStopManager:
    """Tighten paper stops only after protected continuation and only behind recent structure."""

    def adjust_stop(
        self,
        position: ManagedPosition,
        candles: list[Any] | None,
        structure_context: Any = None,
    ) -> tuple[ManagedPosition, TrailingStopAdjustment]:
        reference = self._reference_level(position, candles)
        continuation = self._continuation_supported(position, structure_context)
        applied = bool(position.break_even_applied and position.tp2_achieved and continuation and reference is not None)
        if applied and position.direction == "BUY":
            applied = reference > position.current_stop and reference < self._latest_close(candles, float("inf"))
        elif applied:
            applied = reference < position.current_stop and reference > self._latest_close(candles, float("-inf"))
        new_stop = float(reference) if applied else position.current_stop
        adjustment = TrailingStopAdjustment(
            position_id=position.position_id,
            applied=applied,
            previous_stop=position.current_stop,
            adjusted_stop=new_stop,
            reference_level=reference,
            reason="Stop tightened behind protected recent structure." if applied else "No protected continuation level suitable for trailing.",
        )
        if not applied:
            return position, adjustment
        return position.model_copy(update={"current_stop": new_stop, "trailing_active": True}), adjustment

    def _reference_level(self, position: ManagedPosition, candles: list[Any] | None) -> float | None:
        valid: list[float] = []
        key = "low" if position.direction == "BUY" else "high"
        for candle in (candles or [])[-3:]:
            value = candle.get(key) if isinstance(candle, dict) else getattr(candle, key, None)
            try:
                valid.append(float(value))
            except (TypeError, ValueError):
                continue
        if len(valid) < 2:
            return None
        return round(min(valid) if position.direction == "BUY" else max(valid), 8)

    def _continuation_supported(self, position: ManagedPosition, context: Any) -> bool:
        events = getattr(context, "events", None) if context is not None else None
        if isinstance(context, dict):
            events = context.get("events", [])
        if not events:
            return True
        expected = "BULLISH" if position.direction == "BUY" else "BEARISH"
        return any(
            (event.get("direction") if isinstance(event, dict) else getattr(event, "direction", None)) == expected
            and (event.get("valid", True) if isinstance(event, dict) else getattr(event, "valid", True))
            for event in events
        )

    def _latest_close(self, candles: list[Any] | None, fallback: float) -> float:
        if not candles:
            return fallback
        candle = candles[-1]
        value = candle.get("close") if isinstance(candle, dict) else getattr(candle, "close", None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback
