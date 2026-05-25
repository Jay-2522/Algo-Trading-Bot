from fastapi import FastAPI

from backend.system_health.health_models import PhaseCompletionReport, RouteAuditResult, SafetyScanResult, SystemReadiness
from backend.system_health.phase_report import PhaseReportBuilder
from backend.system_health.readiness_checker import ReadinessChecker
from backend.system_health.route_auditor import RouteAuditor
from backend.system_health.safety_scanner import SafetyScanner


class SystemHealthService:
    """Unified integration audit facade for the existing application instance."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.scanner = SafetyScanner()

    def get_system_status(self) -> dict:
        readiness = self.get_readiness()
        online = sum(1 for module in readiness.modules if module.route_available)
        return {
            "status": "operational" if readiness.overall_status == "READY" else "degraded",
            "phase": "PHASE_1_BACKEND_FOUNDATION",
            "live_execution_enabled": False,
            "simulation_only": True,
            "modules_online": online,
        }

    def get_readiness(self) -> SystemReadiness:
        return ReadinessChecker(self.app, self.scanner).check()

    def run_safety_scan(self) -> SafetyScanResult:
        return self.scanner.scan()

    def audit_routes(self) -> RouteAuditResult:
        return RouteAuditor(self.app).audit()

    def get_phase_report(self) -> PhaseCompletionReport:
        return PhaseReportBuilder().build(self.get_readiness())
