from collections.abc import Iterable

from backend.institutional_intelligence.phase2_completion_models import Phase2ReadinessReport
from backend.institutional_intelligence.phase2_readiness_checker import Phase2ReadinessChecker


class Phase2CompletionReportBuilder:
    """Produce the final Phase 2 institutional completion certification report."""

    def __init__(self, readiness_checker: Phase2ReadinessChecker | None = None) -> None:
        self.readiness_checker = readiness_checker or Phase2ReadinessChecker()

    def build_report(self, app_routes: Iterable[str] | None = None) -> Phase2ReadinessReport:
        report = self.readiness_checker.check_readiness(app_routes)
        ready = report.overall_status == "READY"
        safety_summary = (
            "Simulation-only safeguards verified; broker execution remains disabled."
            if report.safety_audit.passed
            else "Safety findings require review before Phase 2 can be certified."
        )
        client_summary = (
            "Institutional market analysis, simulation decisions, and dashboard reporting are ready for demonstration."
            if ready
            else "Institutional reporting is available, but readiness findings require review."
        )
        return report.model_copy(
            update={
                "completed_modules": list(report.completed_modules),
                "safety_summary": safety_summary,
                "client_ready_summary": client_summary,
                "next_phase_direction": (
                    "Phase 3 can add client visualization and historical simulation observability."
                ),
            }
        )
