from typing import Any, Callable

from pydantic import BaseModel

from backend.account_routing.account_routing_service import AccountRoutingService
from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService
from backend.dashboard.dashboard_models import DashboardCard
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService
from backend.utils.json_safety import to_json_safe
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService


class DashboardCardService:
    """Build dashboard-ready cards from backend module status facades."""

    def __init__(
        self,
        phase3_service: Phase3ReadinessService | None = None,
        monitoring_service: MonitoringService | None = None,
        broker_service: BrokerCompatibilityService | None = None,
        webhook_service: WebhookMonitoringService | None = None,
        execution_service: ExecutionQueueService | None = None,
        account_service: AccountRoutingService | None = None,
    ) -> None:
        self.phase3_service = phase3_service or Phase3ReadinessService()
        self.monitoring_service = monitoring_service or MonitoringService()
        self.broker_service = broker_service or BrokerCompatibilityService()
        self.webhook_service = webhook_service or WebhookMonitoringService()
        self.execution_service = execution_service or ExecutionQueueService()
        self.account_service = account_service or AccountRoutingService()

    def _as_dict(self, value: Any) -> dict[str, Any]:
        safe_value = to_json_safe(value)
        if isinstance(safe_value, dict):
            safe_value.setdefault("simulation_only", True)
            safe_value.setdefault("live_execution_enabled", False)
            return safe_value
        return {"value": safe_value, "simulation_only": True, "live_execution_enabled": False}

    def _safe_card(
        self,
        card_id: str,
        title: str,
        collector: Callable[[], Any],
        value_key: str = "status",
        subtitle: str = "",
    ) -> DashboardCard:
        try:
            data = self._as_dict(collector())
            value = str(data.get(value_key, data.get("status", "available")))
            degraded = value.upper() in {"FAILED", "CRITICAL", "DEGRADED", "UNAVAILABLE", "INCOMPLETE"}
            warning = value.upper() in {"WARNING", "NEEDS_REVIEW"}
            return DashboardCard(
                card_id=card_id,
                title=title,
                status="WARNING" if warning else "ACTIVE" if not degraded else "BLOCKED",
                value=value,
                subtitle=subtitle,
                severity="HIGH" if degraded else "MEDIUM" if warning else "INFO",
                metadata=data,
                simulation_only=True if "simulation_only" not in data else bool(data.get("simulation_only")),
                live_execution_enabled=False,
            )
        except Exception as exc:
            return DashboardCard(
                card_id=card_id,
                title=title,
                status="UNAVAILABLE",
                value="Unavailable",
                subtitle=f"{title} source could not be collected.",
                severity="HIGH",
                metadata={"error": str(exc), "simulation_only": True, "live_execution_enabled": False},
            )

    def build_cards(self) -> list[DashboardCard]:
        allocation_status = lambda: self.account_service.get_allocation_status()
        return [
            self._safe_card(
                "system_health",
                "System Health",
                self.monitoring_service.get_system_health,
                "overall_status",
                "Central monitoring snapshot.",
            ),
            self._safe_card(
                "broker_compatibility",
                "Broker Compatibility",
                self.broker_service.get_status,
                "status",
                "STARTRADER, FxPro, and Vantage metadata.",
            ),
            self._safe_card(
                "webhook_intake",
                "Webhook Intake",
                self.webhook_service.get_status,
                "status",
                "TradingView webhook ingestion status.",
            ),
            self._safe_card(
                "account_routing",
                "Account Routing",
                self.account_service.get_status,
                "status",
                "Multi-account route preview status.",
            ),
            self._safe_card(
                "allocation",
                "Allocation",
                allocation_status,
                "status",
                "Account allocation and risk distribution preview.",
            ),
            self._safe_card(
                "execution_queue",
                "Execution Queue",
                self.execution_service.get_status,
                "total_items",
                "Non-executing queue preparation status.",
            ),
            self._safe_card(
                "monitoring_alerts",
                "Monitoring Alerts",
                lambda: {"status": "operational", "alert_count": len(self.monitoring_service.get_alerts(100))},
                "alert_count",
                "Central alert visibility.",
            ),
            self._safe_card(
                "phase3_readiness",
                "Phase 3 Readiness",
                self.phase3_service.get_status,
                "overall_status",
                "Integrated signal-to-simulation readiness.",
            ),
        ]
