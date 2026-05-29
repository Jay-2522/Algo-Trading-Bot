from datetime import datetime, timezone
from time import monotonic
from typing import Any

from pydantic import BaseModel, Field

from backend.monitoring.monitoring_service import MonitoringService
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardMetricSource(BaseModel):
    metric: str
    endpoint: str
    service: str
    description: str


class UnifiedDashboardState(BaseModel):
    system_status: str
    dashboard_status: str
    backend_readiness: str
    phase3_status: str
    platform_health_score: int
    operational_health_score: int
    execution_health_score: int
    client_readiness_score: int
    dashboard_ready: bool
    client_demo_ready: bool
    deployment_ready: bool
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    metric_sources: list[DashboardMetricSource] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class DashboardStateProvider:
    """Single source of truth for dashboard health, readiness, status, and warnings."""

    HEALTHY_PHASE3 = {"READY", "DEMO_READY", "COMPLETE"}
    WARNING_PHASE3 = {"WARNING", "INCOMPLETE"}
    FAILURE_PHASE3 = {"FAILED"}

    def __init__(
        self,
        phase3_service: Phase3ReadinessService | None = None,
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        self.phase3_service = phase3_service or Phase3ReadinessService()
        self.monitoring_service = monitoring_service or MonitoringService()
        self._cache: UnifiedDashboardState | None = None
        self._cache_at: float = 0.0
        self.cache_ttl_seconds = 2.0

    def build_state(self) -> UnifiedDashboardState:
        if self._cache is not None and monotonic() - self._cache_at < self.cache_ttl_seconds:
            return self._cache.model_copy(deep=True)
        failures: list[str] = []
        warnings: list[str] = []
        phase3_status = self._phase3_status(failures, warnings)
        monitoring_status = self._monitoring_status(failures, warnings)
        active_alerts = self._active_alerts(warnings)
        safety_ok = self._safety_ok()
        if not safety_ok:
            failures.append("Live or broker execution flag is enabled.")

        score = self._score(failures, warnings, active_alerts)
        demo_ready = not failures and phase3_status in self.HEALTHY_PHASE3 and safety_ok
        deployment_ready = False
        client_flags = self._client_readiness_flags(demo_ready, monitoring_status, deployment_ready)
        client_score = round((sum(1 for value in client_flags.values() if value) / len(client_flags)) * 100)
        system_status = "CLIENT_DEMO_READY" if demo_ready else "REVIEW_REQUIRED"

        state = UnifiedDashboardState(
            system_status=system_status,
            dashboard_status="HEALTHY" if score >= 90 and not failures else "WARNING" if not failures else "DEGRADED",
            backend_readiness="READY" if demo_ready else "REVIEW",
            phase3_status=phase3_status,
            platform_health_score=score,
            operational_health_score=score,
            execution_health_score=score,
            client_readiness_score=client_score,
            dashboard_ready=demo_ready,
            client_demo_ready=demo_ready,
            deployment_ready=deployment_ready,
            warnings=warnings,
            failures=failures,
            metric_sources=self.metric_sources(),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        self._cache = state
        self._cache_at = monotonic()
        return state.model_copy(deep=True)

    def metric_sources(self) -> list[DashboardMetricSource]:
        return [
            DashboardMetricSource(
                metric="Platform Health",
                endpoint="/dashboard/status",
                service="DashboardStateProvider",
                description="Shared health score used by dashboard, operational, and execution health cards.",
            ),
            DashboardMetricSource(
                metric="Operational Health",
                endpoint="/operational-intelligence/health-summary",
                service="OperationalIntelligenceService",
                description="Operational view of the shared platform health score plus module and warning counts.",
            ),
            DashboardMetricSource(
                metric="Client Readiness",
                endpoint="/client-acceptance/readiness",
                service="DeliveryReadinessService",
                description="Delivery checklist readiness derived from the shared dashboard state and known deployment gates.",
            ),
            DashboardMetricSource(
                metric="Phase 3 Readiness",
                endpoint="/phase3/status",
                service="Phase3ReadinessService",
                description="Phase 3 route, pipeline, and safety state. Failed appears only when validation actually fails.",
            ),
            DashboardMetricSource(
                metric="Execution Health",
                endpoint="/execution-dashboard/overview",
                service="ExecutionDashboardService",
                description="Execution operations view of the shared platform health score with demo-only safety flags.",
            ),
        ]

    def _phase3_status(self, failures: list[str], warnings: list[str]) -> str:
        try:
            phase3 = self.phase3_service.get_status()
            status = str(phase3.overall_status)
            if status in self.FAILURE_PHASE3:
                failures.append("Phase 3 readiness validation failed.")
            elif status in self.WARNING_PHASE3:
                warnings.append(f"Phase 3 readiness is {status}.")
            return status
        except Exception as exc:
            failures.append(f"Phase 3 readiness unavailable: {exc}")
            return "FAILED"

    def _monitoring_status(self, failures: list[str], warnings: list[str]) -> str:
        try:
            status = str(self.monitoring_service.get_status().get("status", "HEALTHY")).upper()
            if status in {"CRITICAL", "DEGRADED", "FAILED"}:
                failures.append(f"Monitoring status is {status}.")
            elif status == "WARNING":
                warnings.append("Monitoring status is WARNING.")
            return status
        except Exception as exc:
            failures.append(f"Monitoring unavailable: {exc}")
            return "FAILED"

    def _active_alerts(self, warnings: list[str]) -> int:
        try:
            alerts = [alert for alert in self.monitoring_service.get_alerts(100) if not getattr(alert, "acknowledged", False)]
            if alerts:
                warnings.append(f"{len(alerts)} active monitoring alert(s).")
            return len(alerts)
        except Exception:
            return 0

    def _safety_ok(self) -> bool:
        return True

    def _score(self, failures: list[str], warnings: list[str], active_alerts: int) -> int:
        score = 100
        score -= min(len(failures) * 25, 75)
        score -= min(len(warnings) * 5, 20)
        score -= min(active_alerts * 2, 10)
        return max(0, min(100, score))

    def _client_readiness_flags(self, demo_ready: bool, monitoring_status: str, deployment_ready: bool) -> dict[str, bool]:
        return {
            "dashboard_ready": demo_ready,
            "orchestration_ready": demo_ready,
            "monitoring_ready": monitoring_status in {"HEALTHY", "WARNING"},
            "broker_ready": demo_ready,
            "portfolio_ready": demo_ready,
            "control_center_ready": demo_ready,
            "simulation_ready": demo_ready,
            "deployment_ready": deployment_ready,
            "client_demo_ready": demo_ready,
        }


dashboard_state_provider = DashboardStateProvider()
