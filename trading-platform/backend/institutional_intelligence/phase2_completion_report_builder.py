from collections.abc import Iterable

from backend.institutional_intelligence.phase2_completion_models import Phase2ReadinessReport
from backend.institutional_intelligence.phase2_readiness_checker import Phase2ReadinessChecker


class Phase2CompletionReportBuilder:
    """Produce the final Phase 2 institutional completion certification report."""

    def __init__(self, readiness_checker: Phase2ReadinessChecker | None = None) -> None:
        self.readiness_checker = readiness_checker or Phase2ReadinessChecker()

    def build_report(self, app_routes: Iterable[str] | None = None) -> Phase2ReadinessReport:
        return self.readiness_checker.check_readiness(app_routes)
