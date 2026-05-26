from collections import Counter
from typing import Any

from backend.institutional_intelligence.performance_analytics_models import DecisionQualityMetrics


class DecisionQualityAnalyzer:
    """Measure simulation decision distribution and blocking behavior."""

    def analyze_decisions(self, simulation_decision_contexts: list[Any] | None) -> DecisionQualityMetrics:
        decisions = [
            self._get(context, "decision")
            for context in simulation_decision_contexts or []
            if self._get(context, "decision") is not None
        ]
        if not decisions:
            return DecisionQualityMetrics()
        actions = Counter(str(self._get(item, "action", "NO_TRADE")) for item in decisions)
        blocks: Counter[str] = Counter()
        for decision in decisions:
            if self._get(decision, "action") in {"AVOID", "NO_TRADE"} or self._get(decision, "readiness") == "BLOCKED":
                blocks.update(str(reason) for reason in self._items(decision, "rejection_reasons"))
        total = len(decisions)
        blocked = actions["AVOID"] + actions["NO_TRADE"]
        return DecisionQualityMetrics(
            total_decisions=total,
            simulate_buy_count=actions["SIMULATE_BUY"],
            simulate_sell_count=actions["SIMULATE_SELL"],
            wait_count=actions["WAIT"],
            avoid_count=actions["AVOID"],
            no_trade_count=actions["NO_TRADE"],
            decision_block_rate=round(blocked / total * 100.0, 2),
            average_confidence=round(sum(float(self._get(item, "confidence", 0.0) or 0.0) for item in decisions) / total, 2),
            most_common_action=actions.most_common(1)[0][0] if actions else None,
            recurring_block_reasons=[reason for reason, _ in blocks.most_common(5)],
        )

    def _items(self, value: Any, key: str) -> list[Any]:
        return value.get(key, []) if isinstance(value, dict) else getattr(value, key, [])

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
