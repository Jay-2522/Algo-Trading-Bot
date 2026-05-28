from time import monotonic

from backend.monitoring.module_health_tracker import ModuleHealthTracker
from backend.monitoring.monitoring_models import SystemHealthSnapshot


class SystemMonitor:
    """Generate system health snapshots from module status state."""

    def __init__(self, module_tracker: ModuleHealthTracker | None = None) -> None:
        self.module_tracker = module_tracker or ModuleHealthTracker()
        self.started_at = monotonic()

    def generate_snapshot(self) -> SystemHealthSnapshot:
        statuses = self.module_tracker.get_module_statuses()
        warning_count = len([status for status in statuses if status.status == "WARNING"])
        failed_count = len([status for status in statuses if status.status == "FAILED"])
        if failed_count >= 3:
            overall = "CRITICAL"
        elif failed_count:
            overall = "DEGRADED"
        elif warning_count:
            overall = "WARNING"
        else:
            overall = "HEALTHY"
        return SystemHealthSnapshot(
            overall_status=overall,
            active_modules=len([status for status in statuses if status.status in {"HEALTHY", "WARNING"}]),
            warning_modules=warning_count,
            failed_modules=failed_count,
            uptime_seconds=round(monotonic() - self.started_at, 2),
            simulation_only=True,
            live_execution_enabled=False,
        )
