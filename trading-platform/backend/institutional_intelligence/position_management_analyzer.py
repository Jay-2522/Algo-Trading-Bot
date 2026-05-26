from collections import Counter
from typing import Any

from backend.institutional_intelligence.performance_analytics_models import PositionManagementMetrics


class PositionManagementAnalyzer:
    """Measure simulated management interventions and exit quality."""

    def analyze_position_management(self, position_management_contexts: list[Any] | None) -> PositionManagementMetrics:
        partials: dict[tuple, Any] = {}
        break_evens: dict[tuple, Any] = {}
        trailing: dict[tuple, Any] = {}
        structural: dict[tuple, Any] = {}
        emergencies: dict[tuple, Any] = {}
        decisions: dict[str, Any] = {}
        exits: Counter[str] = Counter()
        for context in position_management_contexts or []:
            for item in self._items(context, "partial_take_profits"):
                partials[self._key(item, "level")] = item
            for item in self._items(context, "break_even_adjustments"):
                if self._get(item, "applied", False):
                    break_evens[self._key(item)] = item
            for item in self._items(context, "trailing_stop_adjustments"):
                if self._get(item, "applied", False):
                    trailing[self._key(item)] = item
            for item in self._items(context, "structural_exit_signals"):
                if self._get(item, "exit_required", False):
                    structural[self._key(item)] = item
                    exits[str(self._get(item, "exit_reason", "STRUCTURAL_EXIT"))] += 1
            emergency = self._get(context, "emergency_exit")
            if emergency is not None and self._get(emergency, "triggered", False):
                emergencies[self._key(emergency)] = emergency
                exits[str(self._get(emergency, "shutdown_reason", "EMERGENCY_EXIT"))] += 1
            for decision in self._items(context, "decisions"):
                decision_id = self._get(decision, "decision_id")
                decisions[str(decision_id)] = decision
        qualities = [float(self._get(decision, "confidence", 0.0) or 0.0) for decision in decisions.values()]
        return PositionManagementMetrics(
            partial_tp_count=len(partials),
            break_even_moves=len(break_evens),
            trailing_adjustments=len(trailing),
            structural_exits=len(structural),
            emergency_exits=len(emergencies),
            average_management_quality=round(sum(qualities) / len(qualities), 2) if qualities else 0.0,
            most_common_exit_reason=exits.most_common(1)[0][0] if exits else None,
        )

    def _key(self, value: Any, suffix: str = "") -> tuple:
        timestamp = self._get(value, "timestamp")
        return (self._get(value, "position_id"), suffix or self._get(value, "reason", ""), str(timestamp))

    def _items(self, value: Any, key: str) -> list[Any]:
        return value.get(key, []) if isinstance(value, dict) else getattr(value, key, [])

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
