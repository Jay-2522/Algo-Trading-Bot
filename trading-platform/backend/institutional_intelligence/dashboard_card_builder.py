from typing import Any

from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport
from backend.institutional_intelligence.dashboard_context_models import (
    DashboardAlert,
    DashboardCard,
    DashboardRecommendation,
)
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.performance_analytics_models import InstitutionalPerformanceAnalyticsContext


class DashboardCardBuilder:
    """Build compact dashboard sections from recorded institutional analysis."""

    def build_market_overview_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        state = orchestration_report.system_state
        final_state = state.final_state if state else "NO_TRADE"
        value = state.market_state if state else "UNCLEAR"
        return DashboardCard(
            title="Market Overview",
            status=self._state_status(final_state),
            value=value,
            subtitle=orchestration_report.executive_summary or "Institutional market overview is unavailable.",
            severity=self._state_severity(final_state),
            data={"final_state": final_state, "confidence": state.confidence if state else 0.0},
            warnings=list(orchestration_report.warnings),
        )

    def build_bias_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        state = orchestration_report.system_state
        bias = state.institutional_bias if state else "UNCLEAR"
        confidence = state.confidence if state else 0.0
        return DashboardCard(
            title="Institutional Bias",
            status="HEALTHY" if bias not in {"UNCLEAR", "NEUTRAL", "CONFLICTED"} else "WAITING",
            value=bias,
            subtitle=f"Bias confidence {confidence:.1f} / 100.",
            severity="MEDIUM" if bias == "CONFLICTED" else "INFO",
            data={"institutional_bias": bias, "confidence": confidence},
            warnings=["Institutional direction is conflicted."] if bias == "CONFLICTED" else [],
        )

    def build_confluence_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.confluence_context
        if context is None:
            return self._inactive_card("Confluence Score", "NO_DATA", "Confluence context is unavailable.")
        score = context.confluence_score
        warning = list(score.warnings)
        return DashboardCard(
            title="Confluence Score",
            status=self._readiness_status(score.trade_readiness),
            value=round(score.overall_score, 2),
            subtitle=f"{score.setup_quality} quality, {score.dominant_direction} direction.",
            severity="MEDIUM" if score.dominant_direction == "CONFLICTED" else "INFO",
            data=score.model_dump(mode="json"),
            warnings=warning,
        )

    def build_alignment_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.alignment_context
        if context is None:
            return self._inactive_card("Multi-Timeframe Alignment", "NO_DATA", "Alignment context is unavailable.")
        status = "WARNING" if context.conflicts else ("HEALTHY" if "ALIGNED" in context.alignment_quality else "WAITING")
        return DashboardCard(
            title="Multi-Timeframe Alignment",
            status=status,
            value=context.overall_direction,
            subtitle=f"{context.alignment_quality} at {context.alignment_score:.1f} / 100.",
            severity="MEDIUM" if context.conflicts else "INFO",
            data={
                "alignment_quality": context.alignment_quality,
                "alignment_score": context.alignment_score,
                "confidence": context.confidence,
                "confirmations": context.confirmations,
            },
            warnings=list(context.conflicts + context.warnings),
        )

    def build_session_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.session_context
        if context is None:
            return self._inactive_card("Session And Killzone", "NO_DATA", "Session context is unavailable.")
        readiness = context.trade_timing_readiness
        killzone = context.active_killzone.killzone_name
        return DashboardCard(
            title="Session And Killzone",
            status=self._readiness_status(readiness),
            value=readiness,
            subtitle=f"Current session {context.current_session}; killzone {killzone}.",
            severity="HIGH" if readiness.startswith("AVOID") else "INFO",
            data={
                "current_session": context.current_session,
                "active_killzone": context.active_killzone.model_dump(mode="json"),
                "session_quality_score": context.session_quality_score,
                "liquidity_profile": context.liquidity_profile.model_dump(mode="json"),
            },
            warnings=list(context.warnings),
        )

    def build_entry_model_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.entry_model_context
        if context is None:
            return self._inactive_card("Entry Model", "NO_SETUP", "Entry model context is unavailable.")
        best = context.best_model
        value = best.model_type if best else "NO_SETUP"
        return DashboardCard(
            title="Entry Model",
            status=self._readiness_status(context.overall_readiness),
            value=value,
            subtitle=f"Overall readiness {context.overall_readiness}; confidence {context.confidence:.1f}.",
            severity="MEDIUM" if context.overall_readiness == "AVOID" else "INFO",
            data={
                "overall_readiness": context.overall_readiness,
                "confidence": context.confidence,
                "best_model": best.model_dump(mode="json") if best else None,
            },
            warnings=list(best.warnings) if best else [],
        )

    def build_setup_validation_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.setup_validation_context
        if context is None:
            return self._inactive_card("Setup Validation", "NO_VALIDATION", "Setup validation context is unavailable.")
        return DashboardCard(
            title="Setup Validation",
            status=self._readiness_status(context.execution_readiness),
            value=context.execution_readiness,
            subtitle=f"{len(context.approved_setups)} approved, {len(context.waiting_setups)} waiting, "
            f"{len(context.rejected_setups)} rejected.",
            severity="HIGH" if context.execution_readiness == "REJECTED" else "INFO",
            data={
                "simulation_eligible": context.simulation_eligible,
                "confidence": context.confidence,
                "approved_count": len(context.approved_setups),
                "waiting_count": len(context.waiting_setups),
                "rejected_count": len(context.rejected_setups),
            },
            warnings=list(context.best_setup.warnings) if context.best_setup else [],
        )

    def build_simulation_decision_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.simulation_decision_context
        if context is None:
            return self._inactive_card("Simulation Decision", "NO_TRADE", "Simulation decision is unavailable.")
        decision = context.decision
        return DashboardCard(
            title="Simulation Decision",
            status=self._readiness_status(decision.readiness),
            value=decision.action,
            subtitle=decision.explanation or f"Readiness {decision.readiness}.",
            severity="HIGH" if decision.action == "AVOID" else "INFO",
            data={
                "approved_for_simulation": decision.approved_for_simulation,
                "readiness": decision.readiness,
                "confidence": decision.confidence,
                "setup_quality": decision.setup_quality,
            },
            warnings=list(decision.warnings + decision.rejection_reasons),
        )

    def build_paper_trade_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.paper_trade_context
        if context is None:
            return self._inactive_card("Paper Trade Lifecycle", "NO_CANDIDATE", "Paper trade context is unavailable.")
        status = "ACTIVE" if context.active_positions else ("HEALTHY" if context.closed_positions else "WAITING")
        return DashboardCard(
            title="Paper Trade Lifecycle",
            status=status,
            value=context.lifecycle_status,
            subtitle=f"{len(context.active_positions)} active and {len(context.closed_positions)} closed paper position(s).",
            data={
                "candidates": len(context.candidates),
                "active_positions": len(context.active_positions),
                "closed_positions": len(context.closed_positions),
                "summary": context.summary,
            },
        )

    def build_position_management_card(self, orchestration_report: InstitutionalOrchestrationReport) -> DashboardCard:
        context = orchestration_report.position_management_context
        if context is None:
            return self._inactive_card("Position Management", "NO_POSITION", "Management context is unavailable.")
        emergency = bool(context.emergency_exit and context.emergency_exit.triggered)
        status = "CRITICAL" if emergency else ("ACTIVE" if context.active_positions else "INACTIVE")
        return DashboardCard(
            title="Position Management",
            status=status,
            value=context.management_status,
            subtitle=context.summary or "No active simulated position requires management.",
            severity="CRITICAL" if emergency else "INFO",
            data={
                "active_positions": len(context.active_positions),
                "partial_take_profits": len(context.partial_take_profits),
                "trailing_adjustments": len(context.trailing_stop_adjustments),
                "emergency_triggered": emergency,
            },
            warnings=(
                [context.emergency_exit.shutdown_reason]
                if emergency and context.emergency_exit is not None
                else list(context.session_exit_reasons)
            ),
        )

    def build_performance_card(self, performance_context: InstitutionalPerformanceAnalyticsContext) -> DashboardCard:
        status = "WAITING" if performance_context.optimization_status == "INSUFFICIENT_DATA" else (
            "WARNING" if performance_context.optimization_status in {"NEEDS_ATTENTION", "DEGRADED"} else "HEALTHY"
        )
        return DashboardCard(
            title="Performance Analytics",
            status=status,
            value=performance_context.optimization_status,
            subtitle=f"Analytics health {performance_context.overall_health_score:.1f} / 100.",
            severity="MEDIUM" if status == "WARNING" else "INFO",
            data={
                "overall_health_score": performance_context.overall_health_score,
                "setup_metrics": performance_context.setup_metrics.model_dump(mode="json"),
                "decision_metrics": performance_context.decision_metrics.model_dump(mode="json"),
                "recommendations": [item.model_dump(mode="json") for item in performance_context.recommendations],
            },
            warnings=[item.title for item in performance_context.recommendations if item.severity != "INFO"],
        )

    def build_reasoning_card(self, reasoning_report: InstitutionalReasoningReport) -> DashboardCard:
        action = reasoning_report.narrative.recommended_action
        return DashboardCard(
            title="AI Market Narrative",
            status=self._readiness_status(action),
            value=action,
            subtitle=reasoning_report.narrative.headline,
            severity="HIGH" if action == "AVOID" else "INFO",
            data={
                "dashboard_summary": reasoning_report.dashboard_summary,
                "confidence": reasoning_report.confidence,
                "key_drivers": reasoning_report.narrative.key_drivers,
                "risks": reasoning_report.narrative.risks,
            },
            warnings=list(reasoning_report.narrative.risks),
        )

    def build_risk_card(self, alerts: list[DashboardAlert]) -> DashboardCard:
        critical = any(alert.severity == "CRITICAL" for alert in alerts)
        elevated = any(alert.severity in {"HIGH", "CRITICAL"} for alert in alerts)
        return DashboardCard(
            title="Warnings And Risk",
            status="CRITICAL" if critical else ("WARNING" if elevated else "HEALTHY"),
            value=len(alerts),
            subtitle="Recorded dashboard alerts and institutional safety notices.",
            severity="CRITICAL" if critical else ("HIGH" if elevated else "INFO"),
            data={"alerts": [alert.model_dump(mode="json") for alert in alerts]},
            warnings=[alert.message for alert in alerts if alert.severity in {"HIGH", "CRITICAL"}],
        )

    def build_recommendation_card(self, recommendation: DashboardRecommendation) -> DashboardCard:
        return DashboardCard(
            title="Final Recommendation",
            status=self._readiness_status(recommendation.action),
            value=recommendation.action,
            subtitle=recommendation.reason,
            severity="HIGH" if recommendation.action in {"AVOID", "REVIEW_SYSTEM"} else "INFO",
            data=recommendation.model_dump(mode="json"),
        )

    def _inactive_card(self, title: str, value: str, warning: str) -> DashboardCard:
        return DashboardCard(
            title=title,
            status="INACTIVE",
            value=value,
            subtitle=warning,
            severity="LOW",
            warnings=[warning],
        )

    def _state_status(self, final_state: str) -> str:
        return {
            "READY_FOR_SIMULATION": "HEALTHY",
            "WAITING_FOR_CONFIRMATION": "WAITING",
            "BLOCKED": "BLOCKED",
            "MANAGING_POSITION": "ACTIVE",
            "ERROR_SAFE_MODE": "CRITICAL",
            "NO_TRADE": "INACTIVE",
        }.get(final_state, "INACTIVE")

    def _state_severity(self, final_state: str) -> str:
        return {"BLOCKED": "HIGH", "ERROR_SAFE_MODE": "CRITICAL"}.get(final_state, "INFO")

    def _readiness_status(self, value: str) -> str:
        if value in {"READY_FOR_SIMULATION", "APPROVED", "APPROVED_FOR_SIMULATION"}:
            return "HEALTHY"
        if value in {"MANAGE_POSITION"}:
            return "ACTIVE"
        if value in {"WAIT", "WAITING_FOR_CONFIRMATION", "WAIT_FOR_CONFIRMATION", "CONDITIONAL"}:
            return "WAITING"
        if value in {"AVOID", "BLOCKED", "REJECTED", "BLOCKED_BY_RISK"}:
            return "BLOCKED"
        return "INACTIVE"
