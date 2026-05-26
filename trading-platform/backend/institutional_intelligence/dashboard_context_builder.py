from typing import Any

from backend.institutional_intelligence.dashboard_alert_builder import DashboardAlertBuilder
from backend.institutional_intelligence.dashboard_card_builder import DashboardCardBuilder
from backend.institutional_intelligence.dashboard_context_models import InstitutionalDashboardContext
from backend.institutional_intelligence.dashboard_status_resolver import DashboardStatusResolver
from backend.institutional_intelligence.dashboard_summary_builder import DashboardSummaryBuilder
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.institutional_reasoning_engine import InstitutionalReasoningEngine
from backend.institutional_intelligence.performance_analytics_context_builder import PerformanceAnalyticsContextBuilder


class DashboardContextBuilder:
    """Compose existing analysis reports into one dashboard-ready response."""

    def __init__(
        self,
        orchestrator: Any = None,
        reasoning_engine: Any = None,
        performance_builder: Any = None,
        card_builder: DashboardCardBuilder | None = None,
        alert_builder: DashboardAlertBuilder | None = None,
        summary_builder: DashboardSummaryBuilder | None = None,
        status_resolver: DashboardStatusResolver | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.reasoning_engine = reasoning_engine or InstitutionalReasoningEngine()
        self.performance_builder = performance_builder or PerformanceAnalyticsContextBuilder()
        self.card_builder = card_builder or DashboardCardBuilder()
        self.alert_builder = alert_builder or DashboardAlertBuilder()
        self.summary_builder = summary_builder or DashboardSummaryBuilder()
        self.status_resolver = status_resolver or DashboardStatusResolver()

    def build_dashboard_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None = None,
        orchestration_report: InstitutionalOrchestrationReport | None = None,
        reasoning_report: Any = None,
        performance_context: Any = None,
    ) -> InstitutionalDashboardContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        try:
            report = orchestration_report or self.orchestrator.analyze_from_candles(
                normalized_symbol, normalized_timeframe, candles or []
            )
        except Exception:
            report = InstitutionalOrchestrationReport(
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
                warnings=["Institutional orchestration is unavailable; dashboard is in safe fallback mode."],
            )
        try:
            reasoning = reasoning_report or self.reasoning_engine.generate_reasoning(report)
        except Exception:
            reasoning = None
        try:
            performance = performance_context or self.performance_builder.build_performance_context(
                normalized_symbol, normalized_timeframe, [report]
            )
        except Exception:
            performance = self.performance_builder.build_performance_context(normalized_symbol, normalized_timeframe)

        alerts = self.alert_builder.build_alerts(report, performance, reasoning)
        recommendation = self.summary_builder.build_final_recommendation(report, reasoning)
        market = self.card_builder.build_market_overview_card(report)
        bias = self.card_builder.build_bias_card(report)
        confluence = self.card_builder.build_confluence_card(report)
        alignment = self.card_builder.build_alignment_card(report)
        session = self.card_builder.build_session_card(report)
        entry = self.card_builder.build_entry_model_card(report)
        validation = self.card_builder.build_setup_validation_card(report)
        decision = self.card_builder.build_simulation_decision_card(report)
        paper = self.card_builder.build_paper_trade_card(report)
        management = self.card_builder.build_position_management_card(report)
        performance_card = self.card_builder.build_performance_card(performance)
        reasoning_card = (
            self.card_builder.build_reasoning_card(reasoning)
            if reasoning is not None
            else self.card_builder._inactive_card("AI Market Narrative", "NO_DATA", "Reasoning context is unavailable.")
        )
        cards = [
            market,
            bias,
            confluence,
            alignment,
            session,
            entry,
            validation,
            decision,
            paper,
            management,
            performance_card,
            reasoning_card,
            self.card_builder.build_risk_card(alerts),
            self.card_builder.build_recommendation_card(recommendation),
        ]
        return InstitutionalDashboardContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            cards=cards,
            market_overview=market,
            institutional_bias=bias,
            confluence=confluence,
            alignment=alignment,
            session=session,
            entry_model=entry,
            setup_validation=validation,
            simulation_decision=decision,
            paper_trade=paper,
            position_management=management,
            performance=performance_card,
            reasoning=reasoning_card,
            alerts=alerts,
            final_recommendation=recommendation,
            dashboard_status=self.status_resolver.resolve_dashboard_status(cards, report),
            simulation_only=True,
            live_execution_enabled=False,
        )
