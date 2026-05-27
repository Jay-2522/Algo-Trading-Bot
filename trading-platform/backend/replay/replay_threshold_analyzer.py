from typing import Any

from backend.replay.replay_calibration_models import ReplayBlockReasonMetrics
from backend.replay.replay_report_models import ReplayDecisionAnalytics


class ReplayThresholdAnalyzer:
    """Detect threshold strictness patterns from replay block metrics."""

    def analyze_threshold_strictness(
        self,
        block_metrics: ReplayBlockReasonMetrics,
        decision_analytics: ReplayDecisionAnalytics | None = None,
    ) -> dict[str, Any]:
        total_decisions = decision_analytics.total_decisions if decision_analytics else 0
        simulated = (
            decision_analytics.simulate_buy + decision_analytics.simulate_sell
            if decision_analytics
            else 0
        )
        average_confidence = decision_analytics.average_confidence if decision_analytics else 0.0
        avoid_rate = (
            round((decision_analytics.avoid / total_decisions) * 100.0, 2)
            if decision_analytics and total_decisions
            else 0.0
        )
        no_trade_rate = (
            round((decision_analytics.no_trade / total_decisions) * 100.0, 2)
            if decision_analytics and total_decisions
            else block_metrics.block_rate
        )
        gate_counts = block_metrics.gate_counts

        flags = {
            "high_block_rate": block_metrics.block_rate >= 70.0,
            "high_avoid_rate": avoid_rate >= 50.0,
            "no_simulated_trades": total_decisions > 0 and simulated == 0,
            "low_confidence_decisions": total_decisions > 0 and average_confidence < 45.0,
            "repeated_confluence_rejection": gate_counts.get("CONFLUENCE", 0) >= max(2, block_metrics.total_blocked * 0.3),
            "repeated_session_rejection": gate_counts.get("SESSION", 0) >= max(2, block_metrics.total_blocked * 0.3),
            "risk_gate_pressure": gate_counts.get("RISK", 0) >= max(1, block_metrics.total_blocked * 0.25),
            "news_gate_pressure": gate_counts.get("NEWS", 0) >= max(1, block_metrics.total_blocked * 0.25),
            "entry_geometry_gap": gate_counts.get("ENTRY_GEOMETRY", 0) > 0,
        }

        if total_decisions == 0:
            status = "INSUFFICIENT_DATA"
        elif flags["high_block_rate"] or flags["no_simulated_trades"]:
            status = "TOO_RESTRICTIVE"
        elif block_metrics.block_rate < 20.0 and average_confidence < 50.0:
            status = "TOO_LOOSE"
        else:
            status = "HEALTHY"

        return {
            "status": status,
            "flags": flags,
            "avoid_rate": avoid_rate,
            "no_trade_rate": no_trade_rate,
            "simulated_trade_decisions": simulated,
            "average_confidence": average_confidence,
            "most_restrictive_gate": block_metrics.most_restrictive_gate,
        }
