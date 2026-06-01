from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.deployment.deployment_readiness_service import DeploymentReadinessService
from backend.monitoring.api_monitor import APIMonitor
from backend.monitoring.log_store import LogStore
from backend.monitoring.mt5_monitor import MT5Monitor
from backend.monitoring.process_monitor import ProcessMonitor
from backend.monitoring.system_metrics import SystemMetrics


class PlatformHealthOverview(BaseModel):
    status: str = "HEALTHY"
    health_score: int = 100
    deployment_status: str = "UNKNOWN"
    monitoring_status: str = "OPERATIONAL"
    execution_status: str = "MONITORED"
    strategy_status: str = "MONITORED"
    mt5_status: str = "UNKNOWN"
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlatformHealthService:
    """Aggregate deployment, monitoring, execution, strategy, news, and MT5 health."""

    def __init__(
        self,
        deployment_service: DeploymentReadinessService | None = None,
        process_monitor: ProcessMonitor | None = None,
        system_metrics: SystemMetrics | None = None,
        api_monitor: APIMonitor | None = None,
        mt5_monitor: MT5Monitor | None = None,
        log_store: LogStore | None = None,
    ) -> None:
        self.deployment_service = deployment_service or DeploymentReadinessService()
        self.process_monitor = process_monitor or ProcessMonitor()
        self.system_metrics = system_metrics or SystemMetrics()
        self.api_monitor = api_monitor or APIMonitor()
        self.mt5_monitor = mt5_monitor or MT5Monitor()
        self.log_store = log_store or LogStore()

    def get_overview(self) -> PlatformHealthOverview:
        deployment = self.deployment_service.run_full_check()
        mt5 = self.mt5_monitor.get_mt5_status()
        warnings = self.get_warnings()
        score = self.get_health_score()
        return PlatformHealthOverview(
            status=self._status(score),
            health_score=score,
            deployment_status=deployment.status,
            monitoring_status="OPERATIONAL",
            execution_status="MONITORED",
            strategy_status="MONITORED",
            mt5_status="READY_FOR_DEMO" if mt5["package_available"] and mt5["terminal_detected"] else "WARNING",
            warnings=warnings,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def get_health_score(self) -> int:
        deployment = self.deployment_service.run_full_check()
        metrics = self.system_metrics.get_metrics()
        apis = self.api_monitor.get_api_health()
        score = 100
        if deployment.deployment_score < 70:
            score -= 15
        elif deployment.deployment_score < 90:
            score -= 5
        if not metrics.get("metrics_available"):
            score -= 5
        if apis.get("total_routes", 0) <= 0:
            score -= 20
        return max(0, min(100, score))

    def get_module_status(self) -> dict[str, Any]:
        return {
            "deployment": self.deployment_service.run_full_check(),
            "processes": self.process_monitor.get_process_status(),
            "metrics": self.system_metrics.get_metrics(),
            "apis": self.api_monitor.get_api_health(),
            "mt5": self.mt5_monitor.get_mt5_status(),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_warnings(self) -> list[str]:
        deployment = self.deployment_service.run_full_check()
        mt5 = self.mt5_monitor.get_mt5_status()
        metrics = self.system_metrics.get_metrics()
        warnings = [*deployment.warnings, *mt5["warnings"], *metrics.get("warnings", [])]
        warnings.extend(self.log_store.get_warning_logs(10))
        return list(dict.fromkeys(warnings))

    def _status(self, score: int) -> str:
        if score >= 90:
            return "HEALTHY"
        if score >= 70:
            return "WARNING"
        return "DEGRADED"
