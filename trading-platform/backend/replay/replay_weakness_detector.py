from uuid import uuid4

from backend.replay.replay_models import ReplayStepResult
from backend.replay.replay_report_models import (
    ReplayDecisionAnalytics,
    ReplayTradeAnalytics,
    ReplayWeaknessInsight,
)


class ReplayWeaknessDetector:
    """Detect recurring replay-quality weaknesses without blocking the run."""

    def detect_weaknesses(
        self,
        trade_analytics: ReplayTradeAnalytics,
        decision_analytics: ReplayDecisionAnalytics,
        step_results: list[ReplayStepResult],
    ) -> list[ReplayWeaknessInsight]:
        insights: list[ReplayWeaknessInsight] = []
        if not step_results:
            insights.append(
                self._insight(
                    "DATA",
                    "CRITICAL",
                    "Replay produced no analysis steps.",
                    "Verify candle availability, replay window size, and requested date range.",
                )
            )
            return insights

        if trade_analytics.total_trades == 0:
            insights.append(
                self._insight(
                    "ENTRY_MODEL",
                    "WARNING",
                    "No simulated trades were generated during the replay.",
                    "Review entry model thresholds and confirm that historical conditions include valid setups.",
                )
            )
        if decision_analytics.block_rate >= 70.0:
            insights.append(
                self._insight(
                    "CONFLUENCE",
                    "WARNING",
                    "Most replay steps were blocked or classified as no-trade.",
                    "Inspect confluence, setup-validation, and session filters for overly restrictive behavior.",
                )
            )
        if trade_analytics.total_trades and trade_analytics.win_rate < 40.0:
            insights.append(
                self._insight(
                    "POSITION_MANAGEMENT",
                    "WARNING",
                    "Replay win rate is below institutional quality expectations.",
                    "Review exit management, entry timing, and structural invalidation behavior.",
                )
            )
        if trade_analytics.total_trades and trade_analytics.average_rr < 1.0:
            insights.append(
                self._insight(
                    "RISK",
                    "WARNING",
                    "Average realized R multiple is weak.",
                    "Tighten risk geometry validation or require stronger target quality before simulation.",
                )
            )

        notes = " ".join(" ".join(step.notes) for step in step_results).lower()
        if "session" in notes or any("session" in str(step.simulation_decision).lower() for step in step_results):
            insights.append(
                self._insight(
                    "SESSION",
                    "INFO",
                    "Session timing appeared in replay decision context.",
                    "Compare performance inside and outside London/New York killzones in later optimization.",
                )
            )
        if "confluence" in notes or any("confluence" in str(step.simulation_decision).lower() for step in step_results):
            insights.append(
                self._insight(
                    "CONFLUENCE",
                    "INFO",
                    "Confluence context influenced replay decisions.",
                    "Track whether confluence blocks correlate with better avoided losses over larger samples.",
                )
            )
        if not insights:
            insights.append(
                self._insight(
                    "DATA",
                    "INFO",
                    "No major replay weaknesses detected in this sample.",
                    "Increase sample size before making strategy-parameter changes.",
                )
            )
        return insights

    def _insight(
        self, category: str, severity: str, message: str, suggested_action: str
    ) -> ReplayWeaknessInsight:
        return ReplayWeaknessInsight(
            insight_id=f"RW-{uuid4().hex[:12]}",
            category=category,
            severity=severity,
            message=message,
            suggested_action=suggested_action,
        )
