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
                reason=reason or "Institutional context is incomplete or safety status requires review.",
                next_step="Keep simulation decisions blocked until system evidence is complete.",
            )
        mappings = {
            "BLOCKED": (
                "AVOID",
                "Do not approve a simulated setup while recorded blocking conditions remain.",
                False,
            ),
            "WAITING_FOR_CONFIRMATION": (
                "WAIT",
                "Monitor for confirmation before permitting a simulation decision.",
                False,
            ),
            "READY_FOR_SIMULATION": (
                "READY_FOR_SIMULATION",
                "Eligible setup may proceed through simulation-only review.",
                True,
            ),
            "MANAGING_POSITION": (
                "MANAGE_POSITION",
                "Continue managing the existing paper position under protection rules.",
                False,
            ),
            "NO_TRADE": (
                "MONITOR",
                "Observe institutional conditions until a validated setup is present.",
                False,
            ),
        }
        action, next_step, allowed = mappings.get(final_state, mappings["NO_TRADE"])
        return DashboardRecommendation(
            action=action,
            confidence=confidence,
            reason=reason or f"Institutional system state is {final_state}.",
            next_step=next_step,
            simulation_allowed=allowed,
        )
