from typing import Any

from backend.institutional_intelligence.decision_quality_analyzer import DecisionQualityAnalyzer
from backend.institutional_intelligence.optimization_recommendation_engine import OptimizationRecommendationEngine
from backend.institutional_intelligence.paper_trade_performance_analyzer import PaperTradePerformanceAnalyzer
from backend.institutional_intelligence.performance_analytics_models import InstitutionalPerformanceAnalyticsContext
from backend.institutional_intelligence.position_management_analyzer import PositionManagementAnalyzer
from backend.institutional_intelligence.setup_performance_analyzer import SetupPerformanceAnalyzer


class PerformanceAnalyticsContextBuilder:
    """Aggregate historical institutional paper observations into optimization metrics."""

    def __init__(
        self,
        setup_analyzer: SetupPerformanceAnalyzer | None = None,
        decision_analyzer: DecisionQualityAnalyzer | None = None,
        paper_analyzer: PaperTradePerformanceAnalyzer | None = None,
        position_analyzer: PositionManagementAnalyzer | None = None,
        recommendation_engine: OptimizationRecommendationEngine | None = None,
    ) -> None:
        self.setup_analyzer = setup_analyzer or SetupPerformanceAnalyzer()
        self.decision_analyzer = decision_analyzer or DecisionQualityAnalyzer()
        self.paper_analyzer = paper_analyzer or PaperTradePerformanceAnalyzer()
        self.position_analyzer = position_analyzer or PositionManagementAnalyzer()
        self.recommendation_engine = recommendation_engine or OptimizationRecommendationEngine()

    def build_performance_context(
        self, symbol: str, timeframe: str, historical_contexts: Any = None
    ) -> InstitutionalPerformanceAnalyticsContext:
        setup, decisions, paper, management, sample_count = self._collect(historical_contexts)
        setup_metrics = self.setup_analyzer.analyze_setups(setup)
        decision_metrics = self.decision_analyzer.analyze_decisions(decisions)
        paper_metrics = self.paper_analyzer.analyze_paper_trades(paper)
        management_metrics = self.position_analyzer.analyze_position_management(management)
        recommendations = self.recommendation_engine.generate_recommendations(
            setup_metrics, decision_metrics, paper_metrics, management_metrics
        )
        health_score = self._health_score(setup_metrics, decision_metrics, paper_metrics, management_metrics)
        data_points = setup_metrics.total_setups + decision_metrics.total_decisions + paper_metrics.closed_positions
        if sample_count < 3 or data_points == 0:
            status = "INSUFFICIENT_DATA"
        elif health_score >= 70.0:
            status = "HEALTHY"
        elif health_score >= 45.0:
            status = "NEEDS_ATTENTION"
        else:
            status = "DEGRADED"
        summary = (
            "Insufficient historical simulation observations for reliable optimization."
            if status == "INSUFFICIENT_DATA"
            else f"Institutional analytics status is {status} with health score {health_score:.1f}."
        )
        return InstitutionalPerformanceAnalyticsContext(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            setup_metrics=setup_metrics,
            decision_metrics=decision_metrics,
            paper_trade_metrics=paper_metrics,
            position_management_metrics=management_metrics,
            recommendations=recommendations,
            overall_health_score=health_score,
            optimization_status=status,
            summary=summary,
        )

    def _collect(self, historical: Any) -> tuple[list[Any], list[Any], list[Any], list[Any], int]:
        if historical is None:
            return [], [], [], [], 0
        if isinstance(historical, dict):
            return (
                list(historical.get("setup_validation_contexts", [])),
                list(historical.get("simulation_decision_contexts", [])),
                list(historical.get("paper_trade_contexts", [])),
                list(historical.get("position_management_contexts", [])),
                int(historical.get("sample_count", 0)),
            )
        reports = list(historical)
        return (
            [item for item in (self._get(report, "setup_validation_context") for report in reports) if item is not None],
            [item for item in (self._get(report, "simulation_decision_context") for report in reports) if item is not None],
            [item for item in (self._get(report, "paper_trade_context") for report in reports) if item is not None],
            [item for item in (self._get(report, "position_management_context") for report in reports) if item is not None],
            len(reports),
        )

    def _health_score(self, setup: Any, decisions: Any, paper: Any, management: Any) -> float:
        components: list[float] = []
        if setup.total_setups:
            components.append(setup.average_setup_score)
        if decisions.total_decisions:
            components.append(decisions.average_confidence)
        if paper.closed_positions:
            rr_quality = min(100.0, max(0.0, 50.0 + paper.average_rr * 20.0))
            components.append(round((paper.win_rate + rr_quality) / 2.0, 2))
        if (
            management.partial_tp_count
            or management.break_even_moves
            or management.trailing_adjustments
            or management.structural_exits
            or management.emergency_exits
        ):
            components.append(management.average_management_quality)
        return round(sum(components) / len(components), 2) if components else 0.0

    def _get(self, value: Any, key: str) -> Any:
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
