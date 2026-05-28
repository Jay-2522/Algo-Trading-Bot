from backend.phase3_readiness.phase3_module_registry import Phase3ModuleRegistry


class Phase3RouteAuditor:
    """Audit critical Phase 3 route availability."""

    CRITICAL_ROUTES = {
        "/replay/status",
        "/brokers/status",
        "/brokers/candles/status",
        "/webhooks/status",
        "/webhooks/orchestration/status",
        "/webhooks/security/status",
        "/accounts/status",
        "/accounts/allocation/status",
        "/execution-queue/status",
        "/execution-queue/lifecycle/status",
        "/monitoring/status",
    }

    def __init__(self, registry: Phase3ModuleRegistry | None = None) -> None:
        self.registry = registry or Phase3ModuleRegistry()

    def audit_routes(self, app=None) -> dict:
        if app is not None:
            routes = {route.path for route in app.routes}
        else:
            try:
                from backend.main import app as main_app

                routes = {route.path for route in main_app.routes}
            except Exception:
                routes = set()
        missing = sorted(self.CRITICAL_ROUTES - routes)
        module_statuses = self.registry.list_modules(routes)
        return {
            "total_routes": len(routes),
            "critical_routes": sorted(self.CRITICAL_ROUTES),
            "missing_routes": missing,
            "route_available": not missing,
            "module_statuses": [status.model_dump(mode="json") for status in module_statuses],
            "simulation_only": True,
            "live_execution_enabled": False,
        }
