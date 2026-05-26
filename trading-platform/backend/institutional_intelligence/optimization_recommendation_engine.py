from backend.institutional_intelligence.performance_analytics_models import (
    DecisionQualityMetrics,
    InstitutionalOptimizationRecommendation,
    PaperTradePerformanceMetrics,
    PositionManagementMetrics,
    SetupPerformanceMetrics,
)
from backend.institutional_intelligence.rejection_pattern_analyzer import RejectionPatternAnalyzer


class OptimizationRecommendationEngine:
    """Generate deterministic research recommendations without changing system controls."""

    def __init__(self, pattern_analyzer: RejectionPatternAnalyzer | None = None) -> None:
        self.pattern_analyzer = pattern_analyzer or RejectionPatternAnalyzer()

    def generate_recommendations(
        self,
        setup_metrics: SetupPerformanceMetrics,
        decision_metrics: DecisionQualityMetrics,
        paper_trade_metrics: PaperTradePerformanceMetrics,
        position_management_metrics: PositionManagementMetrics,
    ) -> list[InstitutionalOptimizationRecommendation]:
        patterns = self.pattern_analyzer.analyze_rejections(setup_metrics, decision_metrics)
        recommendations: list[InstitutionalOptimizationRecommendation] = []
        if setup_metrics.total_setups == 0 and decision_metrics.total_decisions == 0:
            recommendations.append(
                self._make(
                    "DATA_QUALITY", "INFO", "Collect institutional simulation history",
                    "There are no recorded setup or decision observations for longitudinal evaluation.",
                    "Persist additional simulation-only orchestration snapshots before tuning thresholds.",
                    "Provides a statistically meaningful baseline for later optimization.",
                )
            )
            return recommendations
        if "SESSION_TIMING" in patterns:
            recommendations.append(
                self._make(
                    "SESSION_TIMING", "WARNING", "Concentrate evaluation within qualified sessions",
                    "Recorded blocks frequently reference session timing or liquidity quality.",
                    "Compare London and New York killzone samples against off-window samples.",
                    "May reduce low-quality simulation candidates without changing execution safety.",
                )
            )
        if "CONFLUENCE" in patterns:
            recommendations.append(
                self._make(
                    "CONFLUENCE", "WARNING", "Review conflicting confluence factors",
                    "Repeated reasons indicate directional or confluence disagreement.",
                    "Audit structure-shift, FVG, order-block, and alignment score contributions.",
                    "Clarifies which analytical modules weaken approved setup quality.",
                )
            )
        if "RISK" in patterns:
            recommendations.append(
                self._make(
                    "RISK", "WARNING", "Audit simulated risk geometry failures",
                    "Recorded rejection reasons reference risk or invalid setup geometry.",
                    "Measure invalidation and target construction by setup type before parameter changes.",
                    "Improves simulation candidate integrity and RR comparability.",
                )
            )
        if setup_metrics.rejection_rate >= 60.0:
            recommendations.append(
                self._make(
                    "SETUP_QUALITY", "WARNING", "Investigate high setup rejection rate",
                    f"Setup rejection rate is {setup_metrics.rejection_rate:.1f} percent.",
                    "Review weakest setup type and its gate failures using additional paper samples.",
                    "Targets filters that systematically suppress otherwise valid observations.",
                )
            )
        if paper_trade_metrics.total_candidates > 0 and paper_trade_metrics.activated_positions == 0:
            recommendations.append(
                self._make(
                    "SETUP_QUALITY", "WARNING", "Review entry activation behavior",
                    "Paper candidates exist but none have activated into simulated positions.",
                    "Assess zone proximity and entry-model strictness on historical candles.",
                    "Distinguishes unavailable market opportunity from excessive entry filtering.",
                )
            )
        if paper_trade_metrics.closed_positions >= 3 and paper_trade_metrics.win_rate < 40.0:
            recommendations.append(
                self._make(
                    "POSITION_MANAGEMENT", "CRITICAL", "Examine weak paper outcome distribution",
                    f"Closed paper positions show a {paper_trade_metrics.win_rate:.1f} percent win rate.",
                    "Attribute losses by setup type, session, and invalidation mechanism.",
                    "Supports evidence-led adjustment of simulation analysis thresholds.",
                )
            )
        if position_management_metrics.emergency_exits > 0:
            recommendations.append(
                self._make(
                    "RISK", "CRITICAL", "Investigate emergency management exits",
                    "At least one paper management cycle triggered an emergency exit condition.",
                    "Review simulation integrity, risk state, geometry, and volatility diagnostics.",
                    "Protects the reliability of future paper-performance measurements.",
                )
            )
        if not recommendations:
            recommendations.append(
                self._make(
                    "SETUP_QUALITY", "INFO", "Continue evidence collection",
                    "No concentrated analytical weakness is identified in the current sample.",
                    "Continue simulation-only collection before considering threshold changes.",
                    "Maintains disciplined optimization based on larger samples.",
                )
            )
        return recommendations

    def _make(
        self, category: str, severity: str, title: str, description: str, action: str, impact: str
    ) -> InstitutionalOptimizationRecommendation:
        return InstitutionalOptimizationRecommendation(
            category=category,
            severity=severity,
            title=title,
            description=description,
            suggested_action=action,
            expected_impact=impact,
        )
