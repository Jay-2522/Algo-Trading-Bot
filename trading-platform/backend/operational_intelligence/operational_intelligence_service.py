from typing import Any

from backend.api.control_center_routes import control_center_service
from backend.api.dashboard_routes import dashboard_service
from backend.api.execution_queue_routes import execution_queue_service
from backend.api.monitoring_routes import monitoring_service
from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.demo_mode.client_demo_service import ClientDemoService
from backend.operational_intelligence.health_aggregator import HealthAggregator
from backend.operational_intelligence.monitoring_summary_builder import MonitoringSummaryBuilder
from backend.operational_intelligence.operational_models import OperationalHealthSummary, OperationalModuleStatus, WarningSummary
from backend.operational_intelligence.warning_engine import WarningEngine
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService
from backend.portfolio.portfolio_service import PortfolioService
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService


class OperationalIntelligenceService:
    """Central operational observability facade for dashboard monitoring."""

    def __init__(
        self,
        health_aggregator: HealthAggregator | None = None,
        warning_engine: WarningEngine | None = None,
        summary_builder: MonitoringSummaryBuilder | None = None,
    ) -> None:
        self.health_aggregator = health_aggregator or HealthAggregator()
        self.warning_engine = warning_engine or WarningEngine()
        self.summary_builder = summary_builder or MonitoringSummaryBuilder()
        self.broker_service = BrokerCompatibilityService()
        self.webhook_service = WebhookMonitoringService()
        self.phase3_service = Phase3ReadinessService()
        self.portfolio_service = PortfolioService()
        self.demo_service = ClientDemoService()

    def _probes(self) -> dict[str, Any]:
        return {
            "Brokers": self.broker_service.get_status,
            "Webhooks": self.webhook_service.get_status,
            "Dashboard": lambda: dashboard_service.get_status().model_dump(mode="json"),
            "Monitoring": monitoring_service.get_status,
            "Control Center": control_center_service.get_status,
            "Portfolio": self.portfolio_service.get_status,
            "Queue Engine": lambda: execution_queue_service.get_status().model_dump(mode="json"),
            "Orchestration": lambda: {"status": "HEALTHY", "simulation_only": True, "live_execution_enabled": False},
            "Phase 3": lambda: self.phase3_service.get_status().model_dump(mode="json"),
            "Demo Mode": self.demo_service.get_status,
        }

    def get_modules(self) -> list[OperationalModuleStatus]:
        return self.health_aggregator.collect_statuses(self._probes())

    def get_warnings(self) -> list[WarningSummary]:
        return self.warning_engine.build_warnings(self.get_modules())

    def get_health_summary(self) -> OperationalHealthSummary:
        statuses = self.get_modules()
        warnings = self.warning_engine.build_warnings(statuses)
        active_alerts = len(monitoring_service.get_alerts(100))
        score = self.health_aggregator.calculate_health_score(statuses, len(warnings), active_alerts)
        overall = self.health_aggregator.overall_status(score, statuses)
        return self.summary_builder.build_summary(statuses, warnings, active_alerts, score, overall)

    def get_status(self) -> dict[str, Any]:
        summary = self.get_health_summary()
        return {
            "status": summary.overall_status,
            "mode": "OPERATIONAL_INTELLIGENCE_ONLY",
            "health_score": summary.health_score,
            "monitored_modules": summary.monitored_modules,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_health_score(self) -> dict[str, Any]:
        summary = self.get_health_summary()
        return {
            "health_score": summary.health_score,
            "overall_status": summary.overall_status,
            "simulation_only": True,
            "live_execution_enabled": False,
        }
