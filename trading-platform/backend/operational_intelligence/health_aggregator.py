from collections.abc import Callable
from typing import Any

from backend.operational_intelligence.operational_models import OperationalModuleStatus


class HealthAggregator:
    """Aggregate health across critical simulation-only platform modules."""

    def _status_from_payload(self, module_name: str, payload: Any) -> OperationalModuleStatus:
        text = str(payload.get("status", "HEALTHY") if isinstance(payload, dict) else "HEALTHY").upper()
        if any(token in text for token in ("FAIL", "CRITICAL", "ERROR")):
            status = "FAILED"
        elif any(token in text for token in ("WARN", "REVIEW", "DEGRADED", "UNAVAILABLE")):
            status = "WARNING"
        elif "DISABLED" in text:
            status = "DISABLED"
        else:
            status = "HEALTHY"
        return OperationalModuleStatus(
            module_name=module_name,
            status=status,
            message=f"{module_name} status: {text}",
        )

    def collect_statuses(self, probes: dict[str, Callable[[], Any]]) -> list[OperationalModuleStatus]:
        statuses: list[OperationalModuleStatus] = []
        for module_name, probe in probes.items():
            try:
                statuses.append(self._status_from_payload(module_name, probe()))
            except Exception as exc:
                statuses.append(
                    OperationalModuleStatus(
                        module_name=module_name,
                        status="WARNING",
                        message=f"{module_name} unavailable for monitoring: {exc}",
                    )
                )
        return statuses

    def calculate_health_score(self, statuses: list[OperationalModuleStatus], warning_count: int, alert_count: int) -> int:
        score = 100
        score -= len([status for status in statuses if status.status == "WARNING"]) * 8
        score -= len([status for status in statuses if status.status == "FAILED"]) * 20
        score -= len([status for status in statuses if status.status == "DISABLED"]) * 4
        score -= min(warning_count * 3, 18)
        score -= min(alert_count * 2, 10)
        return max(0, min(100, score))

    def overall_status(self, score: int, statuses: list[OperationalModuleStatus]) -> str:
        if any(status.status == "FAILED" for status in statuses) or score < 50:
            return "CRITICAL"
        if score < 70:
            return "DEGRADED"
        if score < 90 or any(status.status == "WARNING" for status in statuses):
            return "WARNING"
        return "HEALTHY"
