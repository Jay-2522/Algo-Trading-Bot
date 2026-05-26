from typing import Any

from backend.institutional_intelligence.position_management_models import ManagedPosition, StructuralExitSignal


class StructuralExitDetector:
    """Detect opposing institutional structure events against a simulated position."""

    def detect_exit(
        self,
        position: ManagedPosition,
        structure_context: Any = None,
        breaker_context: Any = None,
    ) -> StructuralExitSignal:
        opposing = "BEARISH" if position.direction == "BUY" else "BULLISH"
        evidence: list[str] = []
        confidence = 0.0
        for event in self._items(structure_context, "events"):
            if self._get(event, "direction") != opposing or not self._get(event, "valid", True):
                continue
            event_type = self._get(event, "event_type")
            strength = float(self._get(event, "strength", 0.0) or 0.0)
            if event_type in {"MSS", "CHOCH"} and strength >= 65.0:
                evidence.append(f"Opposing {event_type} confirmed at {strength:.1f} strength.")
                confidence = max(confidence, strength)
        for breaker in self._items(breaker_context, "breaker_blocks"):
            strength = float(self._get(breaker, "strength", 0.0) or 0.0)
            if (
                self._get(breaker, "direction") == opposing
                and self._get(breaker, "valid", True)
                and strength >= 75.0
            ):
                evidence.append(f"Opposing breaker block confirmed at {strength:.1f} strength.")
                confidence = max(confidence, strength)
        required = bool(evidence)
        return StructuralExitSignal(
            position_id=position.position_id,
            exit_required=required,
            exit_reason="Institutional structure invalidated the simulated position." if required else "No opposing structural invalidation detected.",
            severity="CRITICAL" if confidence >= 80.0 else ("WARNING" if required else "INFO"),
            confidence=confidence,
            structural_evidence=evidence,
        )

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        return context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
