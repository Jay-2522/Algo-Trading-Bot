from typing import Any, Callable

from pydantic import BaseModel

from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.dashboard.dashboard_models import DashboardOverview, DashboardStatusResponse
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService


class DashboardStatusBuilder:
    """Build high-level dashboard status and overview context."""

    def __init__(
        self,
        phase3_service: Phase3ReadinessService | None = None,
        monitoring_service: MonitoringService | None = None,
        broker_service: BrokerCompatibilityService | None = None,
        webhook_service: WebhookMonitoringService | None = None,
        execution_service: ExecutionQueueService | None = None,
    ) -> None:
        self.phase3_service = phase3_service or Phase3ReadinessService()
        self.monitoring_service = monitoring_service or MonitoringService()
        self.broker_service = broker_service or BrokerCompatibilityService()
        self.webhook_service = webhook_service or WebhookMonitoringService()
        self.execution_service = execution_service or ExecutionQueueService()

    def _safe_collect(self, name: str, collector: Callable[[], Any]) -> dict[str, Any]:
        try:
            value = collector()
            if isinstance(value, BaseModel):
                return value.model_dump(mode="json")
            if isinstance(value, dict):
                return value
            return {"status": "available", "value": value, "simulation_only": True, "live_execution_enabled": False}
        except Exception as exc:
            return {
                "status": "unavailable",
                "module": name,
                "message": f"{name} dashboard source unavailable: {exc}",
                "simulation_only": True,
                "live_execution_enabled": False,
            }

    def build_status(self) -> DashboardStatusResponse:
        phase3 = self._safe_collect("phase3", self.phase3_service.get_status)
        monitoring = self._safe_collect("monitoring", self.monitoring_service.get_status)
        dashboard_ready = (
            phase3.get("overall_status") in {"READY", "WARNING"}
            and monitoring.get("simulation_only") is True
            and phase3.get("live_execution_enabled") is False
        )
        return DashboardStatusResponse(
            status="READY" if dashboard_ready else "DEGRADED",
            dashboard_ready=dashboard_ready,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def build_overview(self) -> DashboardOverview:
        from backend.dashboard.dashboard_card_service import DashboardCardService

        phase3 = self._safe_collect("phase3", self.phase3_service.get_status)
        monitoring = self._safe_collect("monitoring", self.monitoring_service.get_status)
        broker = self._safe_collect("broker", self.broker_service.get_status)
        webhook = self._safe_collect("webhook", self.webhook_service.get_status)
        execution = self._safe_collect("execution_queue", self.execution_service.get_status)
        system = self._safe_collect("system_health", self.monitoring_service.get_system_health)
        alerts = self._safe_collect("alerts", lambda: [alert.model_dump(mode="json") for alert in self.monitoring_service.get_alerts(25)])
        alert_list = alerts if isinstance(alerts, list) else alerts.get("value", [])
        cards = DashboardCardService(
            phase3_service=self.phase3_service,
            monitoring_service=self.monitoring_service,
            broker_service=self.broker_service,
            webhook_service=self.webhook_service,
            execution_service=self.execution_service,
        ).build_cards()
        problem_cards = [card for card in cards if card.severity in {"HIGH", "CRITICAL"}]
        overall_status = "WARNING" if problem_cards else "READY"
        return DashboardOverview(
            overall_status=overall_status,
            system_status=system,
            broker_status=broker,
            webhook_status=webhook,
            execution_status=execution,
            monitoring_status=monitoring,
            phase3_status=phase3,
            cards=cards,
            alerts=alert_list if isinstance(alert_list, list) else [],
            simulation_only=True,
            live_execution_enabled=False,
        )
