from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport
from backend.institutional_intelligence.dashboard_context_models import DashboardRecommendation
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport


class DashboardSummaryBuilder:
    """Turn resolved institutional state into a restrained dashboard recommendation."""

    def build_final_recommendation(
        self,
        orchestration_report: InstitutionalOrchestrationReport,
        reasoning_report: InstitutionalReasoningReport | None = None,
    ) -> DashboardRecommendation:
        state = orchestration_report.system_state
        final_state = state.final_state if state else "ERROR_SAFE_MODE"
        confidence = state.confidence if state else 0.0
        reason = (
            reasoning_report.narrative.headline
            if reasoning_report is not None
            else orchestration_report.executive_summary
        )
        unsafe = orchestration_report.live_execution_enabled or not orchestration_report.simulation_only
        failed = any(step.status == "FAILED" for step in orchestration_report.pipeline_steps)
        if unsafe or failed or final_state == "ERROR_SAFE_MODE":
            return DashboardRecommendation(
                action="REVIEW_SYSTEM",
                confidence=confidence,
                reason="Review system status. Institutional verification is incomplete.",
                next_step="Keep simulation decisions blocked until checks pass.",
            )
        mappings = {
            "BLOCKED": (
                "AVOID",
                "Avoid simulation now. Institutional conditions are not fully aligned.",
                False,
            ),
            "WAITING_FOR_CONFIRMATION": (
                "WAIT",
                "Wait for confirmation. Setup quality is not ready.",
                False,
            ),
            "READY_FOR_SIMULATION": (
                "READY_FOR_SIMULATION",
                "Ready for simulation. Risk and structure gates passed.",
                True,
            ),
            "MANAGING_POSITION": (
                "MANAGE_POSITION",
                "Manage the paper position. Protection rules are active.",
                False,
            ),
            "NO_TRADE": (
                "MONITOR",
                "Monitor conditions. No approved simulated setup is present.",
                False,
            ),
        }
        action, next_step, allowed = mappings.get(final_state, mappings["NO_TRADE"])
        return DashboardRecommendation(
            action=action,
            confidence=confidence,
            reason=next_step,
            next_step=next_step,
            simulation_allowed=allowed,
        )
