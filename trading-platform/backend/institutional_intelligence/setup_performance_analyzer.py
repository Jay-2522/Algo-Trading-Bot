from collections import Counter, defaultdict
from typing import Any

from backend.institutional_intelligence.performance_analytics_models import SetupPerformanceMetrics


class SetupPerformanceAnalyzer:
    """Aggregate institutional setup validation quality deterministically."""

    def analyze_setups(self, setup_validation_contexts: list[Any] | None) -> SetupPerformanceMetrics:
        validations = [
            validation
            for context in setup_validation_contexts or []
            for validation in self._items(context, "validations")
        ]
        if not validations:
            return SetupPerformanceMetrics()
        approved = [item for item in validations if self._get(item, "approved_for_simulation", False)]
        rejected = [item for item in validations if self._get(item, "readiness") == "REJECTED"]
        waiting = [
            item for item in validations
            if item not in approved and item not in rejected
        ]
        scores_by_type: dict[str, list[float]] = defaultdict(list)
        reasons: Counter[str] = Counter()
        for validation in validations:
            model_type = str(self._get(validation, "model_type", "UNKNOWN"))
            scores_by_type[model_type].append(float(self._get(validation, "overall_score", 0.0) or 0.0))
            reasons.update(str(reason) for reason in self._items(validation, "rejection_reasons"))
        averages = {key: sum(scores) / len(scores) for key, scores in scores_by_type.items()}
        total = len(validations)
        return SetupPerformanceMetrics(
            total_setups=total,
            approved_setups=len(approved),
            rejected_setups=len(rejected),
            waiting_setups=len(waiting),
            approval_rate=round(len(approved) / total * 100.0, 2),
            rejection_rate=round(len(rejected) / total * 100.0, 2),
            average_setup_score=round(sum(averages_value for scores in scores_by_type.values() for averages_value in scores) / total, 2),
            best_setup_type=max(averages, key=averages.get) if averages else None,
            weakest_setup_type=min(averages, key=averages.get) if averages else None,
            recurring_rejection_reasons=[reason for reason, _ in reasons.most_common(5)],
        )

    def _items(self, value: Any, key: str) -> list[Any]:
        return value.get(key, []) if isinstance(value, dict) else getattr(value, key, [])

    def _get(self, value: Any, key: str, default: Any = None) -> Any:
        return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)
