from pathlib import Path

from backend.deployment.production_readiness_models import GoLiveAssessment
from backend.deployment.production_readiness_service import ProductionReadinessService


class GoLiveAssessmentService:
    """Produce final demo VPS go-live assessment from the readiness report."""

    def __init__(
        self,
        project_root: Path | None = None,
        production_readiness_service: ProductionReadinessService | None = None,
    ) -> None:
        self.project_root = project_root
        self.production_readiness_service = production_readiness_service or ProductionReadinessService(project_root)

    def run_assessment(self) -> GoLiveAssessment:
        report = self.production_readiness_service.get_report()
        return GoLiveAssessment(
            readiness_score=report.readiness_score,
            deployment_ready=report.deployment_score >= 85,
            monitoring_ready=report.monitoring_score >= 85,
            security_ready=report.security_score >= 85,
            backup_ready=report.backup_score >= 85,
            execution_ready=report.execution_score >= 85,
            strategy_ready=report.strategy_score >= 85,
            vps_ready=report.vps_score >= 85,
            blockers=report.blockers,
            warnings=report.warnings,
            next_actions=self.get_next_actions(report),
        )

    def get_next_actions(self, report=None) -> list[str]:
        report = report or self.production_readiness_service.get_report()
        actions = [
            "Deploy to demo VPS only after blockers are cleared.",
            "Run extended demo testing.",
            "Run MT5 stability testing on a demo account.",
            "Validate dashboard and monitoring after deployment.",
            "Complete client acceptance testing.",
            "Plan NIFTY50 completion as a future expansion item.",
        ]
        if report.overall_status in {"READY_FOR_DEMO_VPS", "READY_FOR_STAGING"}:
            actions.insert(0, "Prepare demo VPS deployment package.")
        else:
            actions.insert(0, "Resolve readiness warnings and blockers before VPS deployment.")
        return actions
