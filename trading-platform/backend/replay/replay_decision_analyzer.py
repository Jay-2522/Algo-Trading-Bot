from collections import Counter

from backend.replay.replay_models import ReplayStepResult
from backend.replay.replay_report_models import ReplayDecisionAnalytics


class ReplayDecisionAnalyzer:
    """Analyze replayed institutional simulation decisions."""

    def analyze_decisions(self, step_results: list[ReplayStepResult]) -> ReplayDecisionAnalytics:
        actions = [str(step.simulation_decision.get("action", "NO_TRADE") or "NO_TRADE") for step in step_results]
        total = len(actions)
        counts = Counter(actions)
        confidences = [float(step.confidence or 0.0) for step in step_results]
        blocked = counts["AVOID"] + counts["NO_TRADE"]

        return ReplayDecisionAnalytics(
            total_decisions=total,
            simulate_buy=counts["SIMULATE_BUY"],
            simulate_sell=counts["SIMULATE_SELL"],
            wait=counts["WAIT"],
            avoid=counts["AVOID"],
            no_trade=counts["NO_TRADE"],
            block_rate=round((blocked / total) * 100.0, 2) if total else 0.0,
            average_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            most_common_action=counts.most_common(1)[0][0] if counts else "NO_TRADE",
        )
