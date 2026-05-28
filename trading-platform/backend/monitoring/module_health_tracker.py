from backend.monitoring.monitoring_models import ModuleHealthStatus
from backend.system_health.module_registry import get_module_registry


class ModuleHealthTracker:
    """Track health state for registered platform modules."""

    TRACKED_MODULES = {
        "webhooks",
        "orchestration",
        "account_routing",
        "account_allocation",
        "execution_queue",
        "monitoring",
    }

    def __init__(self) -> None:
        self.warnings: dict[str, list[str]] = {}
        self.failures: dict[str, str] = {}

    def get_module_statuses(self) -> list[ModuleHealthStatus]:
        statuses: list[ModuleHealthStatus] = []
        registered = {module["name"] for module in get_module_registry()}
        module_names = sorted(registered | self.TRACKED_MODULES)
        for name in module_names:
            statuses.append(self.check_module(name))
        return statuses

    def check_module(self, name: str) -> ModuleHealthStatus:
        if name in self.failures:
            return ModuleHealthStatus(
                module_name=name,
                status="FAILED",
                warnings=[self.failures[name], *self.warnings.get(name, [])],
                healthy=False,
            )
        warnings = self.warnings.get(name, [])
        if warnings:
            return ModuleHealthStatus(module_name=name, status="WARNING", warnings=warnings, healthy=True)
        return ModuleHealthStatus(module_name=name, status="HEALTHY", warnings=[], healthy=True)

    def register_warning(self, name: str, warning: str) -> None:
        self.warnings.setdefault(name, []).append(warning)

    def register_failure(self, name: str, reason: str) -> None:
        self.failures[name] = reason
