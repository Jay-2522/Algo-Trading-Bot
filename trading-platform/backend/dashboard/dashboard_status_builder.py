from typing import Any, Callable

from pydantic import BaseModel

from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.dashboard.dashboard_models import DashboardOverview, DashboardStatusResponse
from backend.dashboard.dashboard_state_provider import DashboardStateProvider, dashboard_state_provider
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService
from backend.utils.json_safety import safe_error_payload, to_json_safe
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
        state_provider: DashboardStateProvider | None = None,
    ) -> None:
        self.phase3_service = phase3_service or Phase3ReadinessService()
        self.monitoring_service = monitoring_service or MonitoringService()
        self.broker_service = broker_service or BrokerCompatibilityService()
        self.webhook_service = webhook_service or WebhookMonitoringService()
        self.execution_service = execution_service or ExecutionQueueService()
        self.state_provider = state_provider or dashboard_state_provider

    def _safe_collect(self, name: str, collector: Callable[[], Any]) -> dict[str, Any]:
        try:
            value = collector()
            safe_value = to_json_safe(value)
            if isinstance(safe_value, dict):
                safe_value.setdefault("simulation_only", True)
                safe_value.setdefault("live_execution_enabled", False)
                return safe_value
            return {"status": "available", "value": safe_value, "simulation_only": True, "live_execution_enabled": False}
        except Exception as exc:
            return safe_error_payload(f"{name} dashboard source unavailable: {exc}", name)

    def build_status(self) -> DashboardStatusResponse:
        state = self.state_provider.build_state()
        return DashboardStatusResponse(
            status=state.backend_readiness,
            dashboard_ready=state.dashboard_ready,
            platform_health_score=state.platform_health_score,
            system_status=state.system_status,
            phase3_status=state.phase3_status,
            metric_sources=[source.model_dump(mode="json") for source in state.metric_sources],
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
        alerts = to_json_safe(self.monitoring_service.get_alerts(25))
        alert_list = alerts if isinstance(alerts, list) else alerts.get("value", [])
        cards = DashboardCardService(
            phase3_service=self.phase3_service,
            monitoring_service=self.monitoring_service,
            broker_service=self.broker_service,
            webhook_service=self.webhook_service,
            execution_service=self.execution_service,
        ).build_cards()
        state = self.state_provider.build_state()
        problem_cards = [card for card in cards if card.severity in {"HIGH", "CRITICAL"}]
        overall_status = "WARNING" if problem_cards or state.warnings else state.backend_readiness
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
