from backend.phase3_readiness.phase3_client_readiness_report import Phase3ClientReadinessReportBuilder
from backend.phase3_readiness.phase3_module_registry import Phase3ModuleRegistry
from backend.phase3_readiness.phase3_pipeline_validator import Phase3PipelineValidator
from backend.phase3_readiness.phase3_readiness_models import Phase3ReadinessReport
from backend.phase3_readiness.phase3_route_auditor import Phase3RouteAuditor
from backend.phase3_readiness.phase3_safety_auditor import Phase3SafetyAuditor


class Phase3ReadinessService:
    """Facade for Phase 3 integration readiness checks."""

    def __init__(
        self,
        registry: Phase3ModuleRegistry | None = None,
        route_auditor: Phase3RouteAuditor | None = None,
        pipeline_validator: Phase3PipelineValidator | None = None,
        safety_auditor: Phase3SafetyAuditor | None = None,
        client_report_builder: Phase3ClientReadinessReportBuilder | None = None,
    ) -> None:
        self.registry = registry or Phase3ModuleRegistry()
        self.route_auditor = route_auditor or Phase3RouteAuditor(self.registry)
        self.pipeline_validator = pipeline_validator or Phase3PipelineValidator()
        self.safety_auditor = safety_auditor or Phase3SafetyAuditor()
        self.client_report_builder = client_report_builder or Phase3ClientReadinessReportBuilder(self.registry)

    def get_status(self) -> Phase3ReadinessReport:
        route_report = self.get_routes()
        module_statuses = self.get_modules()
        safety = self.run_safety_audit()
        completed = [status.module_name for status in module_statuses if status.route_available]
        missing = [status.module_name for status in module_statuses if not status.route_available]
        warnings = [status.module_name for status in module_statuses if status.status not in {"READY"}]
        if missing or safety.safety_status != "PASSED":
            overall = "FAILED" if safety.safety_status != "PASSED" else "INCOMPLETE"
        elif warnings:
            overall = "WARNING"
        else:
            overall = "READY"
        return Phase3ReadinessReport(
            overall_status=overall,
            completed_modules=completed,
            missing_modules=missing,
            warning_modules=warnings,
            total_routes=route_report["total_routes"],
            safety_status=safety.safety_status,
            client_mvp_status="BACKEND_READY" if overall == "READY" else "NEEDS_REVIEW",
            simulation_only=True,
            live_execution_enabled=False,
        )

    def get_modules(self):
        route_report = self.get_routes()
        routes = set(route_report.get("all_routes", []))
        return self.registry.list_modules(routes)

    def get_routes(self) -> dict:
        report = self.route_auditor.audit_routes()
        try:
            from backend.main import app

            report["all_routes"] = sorted({route.path for route in app.routes})
        except Exception:
            report["all_routes"] = []
        return report

    def validate_pipeline(self):
        return self.pipeline_validator.validate_pipeline()

    def run_safety_audit(self):
        return self.safety_auditor.run_safety_audit()

    def get_client_readiness_report(self) -> dict:
        report = self.client_report_builder.build_report()
        report["readiness"] = self.get_status().model_dump(mode="json")
        return report
