from backend.monitoring.alert_engine import AlertEngine
from backend.monitoring.alert_store import AlertStore
from backend.monitoring.broker_monitor import BrokerMonitor
from backend.monitoring.execution_monitor import ExecutionMonitor
from backend.monitoring.module_health_tracker import ModuleHealthTracker
from backend.monitoring.monitoring_models import AlertEvent, ExecutionMonitoringSummary, ModuleHealthStatus, SystemHealthSnapshot
from backend.monitoring.system_monitor import SystemMonitor
from backend.monitoring.webhook_monitor import WebhookMonitor


class MonitoringService:
    """Central monitoring facade for platform health, logs, and alerts."""

    def __init__(
        self,
        module_tracker: ModuleHealthTracker | None = None,
        alert_store: AlertStore | None = None,
        execution_monitor: ExecutionMonitor | None = None,
        webhook_monitor: WebhookMonitor | None = None,
        broker_monitor: BrokerMonitor | None = None,
    ) -> None:
        self.module_tracker = module_tracker or ModuleHealthTracker()
        self.system_monitor = SystemMonitor(self.module_tracker)
        self.alert_store = alert_store or AlertStore()
        self.alert_engine = AlertEngine(self.alert_store)
        self.execution_monitor = execution_monitor or ExecutionMonitor()
        self.webhook_monitor = webhook_monitor or WebhookMonitor()
        self.broker_monitor = broker_monitor or BrokerMonitor()

    def get_status(self) -> dict:
        snapshot = self.get_system_health()
        return {
            "status": snapshot.overall_status,
            "mode": "MONITORING_AND_ALERTING_ONLY",
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_system_health(self) -> SystemHealthSnapshot:
        snapshot = self.system_monitor.generate_snapshot()
        if snapshot.failed_modules:
            self.alert_engine.create_alert("ERROR", "system", "Module failure detected", "One or more modules are failing.")
        elif snapshot.warning_modules:
            self.alert_engine.create_alert("WARNING", "system", "Module warning detected", "One or more modules have warnings.")
        return snapshot

    def get_module_health(self) -> list[ModuleHealthStatus]:
        return self.module_tracker.get_module_statuses()

    def get_execution_monitoring(self) -> ExecutionMonitoringSummary:
        summary = self.execution_monitor.generate_execution_summary()
        if summary.failed_safe:
            self.alert_engine.create_alert("ERROR", "execution_queue", "Failed safe queue items", "Execution queue has failed-safe items.")
        return summary

    def get_webhook_monitoring(self) -> dict:
        metrics = self.webhook_monitor.get_webhook_metrics()
        if metrics["replay_attacks"] or metrics["rate_limits"]:
            self.alert_engine.create_alert("WARNING", "webhooks", "Suspicious webhook activity", "Replay/rate-limit events detected.")
        return metrics

    def get_broker_monitoring(self) -> dict:
        return self.broker_monitor.get_broker_health()

    def get_alerts(self, limit: int = 100) -> list[AlertEvent]:
        return self.alert_store.list_alerts(limit)

    def acknowledge_alert(self, alert_id: str) -> AlertEvent | None:
        return self.alert_store.acknowledge_alert(alert_id)
