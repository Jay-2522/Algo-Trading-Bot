from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport
from backend.institutional_intelligence.dashboard_context_models import DashboardAlert
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.performance_analytics_models import InstitutionalPerformanceAnalyticsContext


class DashboardAlertBuilder:
    """Extract dashboard-visible safety and quality notices from typed contexts."""

    def build_alerts(
        self,
        orchestration_report: InstitutionalOrchestrationReport,
        performance_context: InstitutionalPerformanceAnalyticsContext | None = None,
        reasoning_report: InstitutionalReasoningReport | None = None,
    ) -> list[DashboardAlert]:
        alerts: list[DashboardAlert] = []
        if orchestration_report.live_execution_enabled or not orchestration_report.simulation_only:
            alerts.append(
                DashboardAlert(
                    severity="CRITICAL",
                    category="SAFETY",
                    message="Institutional dashboard safety flags are inconsistent with simulation-only operation.",
                    recommended_action="Review system safety controls and block simulation approvals.",
                )
            )
        else:
            alerts.append(
                DashboardAlert(
                    severity="INFO",
                    category="SAFETY",
                    message="Safety boundary confirmed: execution remains disabled and outputs are simulation-only.",
                    recommended_action="Continue simulation-only monitoring.",
                )
            )
        state = orchestration_report.system_state
        if state and state.final_state == "BLOCKED":
            alerts.append(
                DashboardAlert(
                    severity="HIGH",
                    category="READINESS",
                    message="Institutional simulation is blocked by current risk, timing, or management conditions.",
                    recommended_action="Avoid simulation until blocking conditions clear.",
                )
            )
        failed_steps = [step.step_name for step in orchestration_report.pipeline_steps if step.status == "FAILED"]
        if failed_steps:
            alerts.append(
                DashboardAlert(
                    severity="CRITICAL",
                    category="PIPELINE",
                    message=f"Pipeline failed safely at: {', '.join(failed_steps)}.",
                    recommended_action="Review unavailable analytical inputs before further simulation review.",
                )
            )
        alignment = orchestration_report.alignment_context
        if alignment and alignment.conflicts:
            alerts.append(
                DashboardAlert(
                    severity="MEDIUM",
                    category="ALIGNMENT",
                    message="Directional conflict exists across institutional timeframes.",
                    recommended_action="Wait for higher and lower timeframe agreement.",
                )
            )
        if performance_context and performance_context.optimization_status == "INSUFFICIENT_DATA":
            alerts.append(
                DashboardAlert(
                    severity="LOW",
                    category="DATA_QUALITY",
                    message="Insufficient paper-trade observations are available for optimization confidence.",
                    recommended_action="Accumulate simulation observations before optimizing thresholds.",
                )
            )
        if reasoning_report and reasoning_report.narrative.risks and not any(
            alert.category == "READINESS" for alert in alerts
        ):
            alerts.append(
                DashboardAlert(
                    severity="MEDIUM",
                    category="NARRATIVE_RISK",
                    message=reasoning_report.narrative.risks[0],
                    recommended_action="Review recorded narrative risk before simulation consideration.",
                )
            )
        return alerts
