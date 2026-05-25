from fastapi import FastAPI

from backend.system_health.health_models import ModuleHealth, SystemReadiness
from backend.system_health.module_registry import get_module_registry
from backend.system_health.safety_scanner import SafetyScanner


class ReadinessChecker:
    """Confirm each registered platform module is routed and remains non-live."""

    def __init__(self, app: FastAPI, scanner: SafetyScanner | None = None) -> None:
        self.app = app
        self.scanner = scanner or SafetyScanner()

    def check(self) -> SystemReadiness:
        registered_paths = {route.path for route in self.app.routes}
        modules = []
        for registered in get_module_registry():
            available = registered["route"] in registered_paths
            modules.append(
                ModuleHealth(
                    module_name=registered["name"],
                    status="READY" if available else "UNAVAILABLE",
                    route_available=available,
                    simulation_only=registered["simulation_only"],
                    live_execution_enabled=registered["live_execution_enabled"],
                    message="Status route registered." if available else "Expected status route missing.",
                )
            )
        safety = self.scanner.scan()
        ready = all(module.route_available for module in modules) and safety.passed
        return SystemReadiness(
            overall_status="READY" if ready else "DEGRADED",
            modules=modules,
            safety_passed=safety.passed,
            live_execution_enabled=False,
            total_routes=len(self.app.routes),
        )
