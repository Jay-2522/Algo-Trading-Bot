from backend.phase3_readiness.phase3_readiness_models import Phase3ModuleStatus


class Phase3ModuleRegistry:
    """Phase 3 module inventory and primary route map."""

    MODULE_ROUTES = {
        "replay": "/replay/status",
        "replay_analytics": "/replay/report/latest",
        "replay_calibration": "/replay/calibration/latest",
        "replay_comparison": "/replay/compare/recent",
        "client_symbols": "/replay/symbols",
        "broker_compatibility": "/brokers/status",
        "mt5_demo_readiness": "/brokers/mt5/readiness",
        "broker_observation": "/brokers/observation/status",
        "broker_feed_quality": "/brokers/feed-quality/status",
        "canonical_feed": "/brokers/canonical-feed/status",
        "candle_feed": "/brokers/candles/status",
        "tradingview_webhooks": "/webhooks/status",
        "webhook_orchestration": "/webhooks/orchestration/status",
        "webhook_security": "/webhooks/security/status",
        "account_routing": "/accounts/status",
        "account_allocation": "/accounts/allocation/status",
        "execution_queue": "/execution-queue/status",
        "execution_lifecycle": "/execution-queue/lifecycle/status",
        "monitoring_alerting": "/monitoring/status",
    }

    def list_modules(self, app_routes: set[str] | None = None) -> list[Phase3ModuleStatus]:
        routes = app_routes or set()
        statuses: list[Phase3ModuleStatus] = []
        for module_name, route in self.MODULE_ROUTES.items():
            available = route in routes if routes else True
            statuses.append(
                Phase3ModuleStatus(
                    module_name=module_name,
                    route_available=available,
                    status="READY" if available else "MISSING_ROUTE",
                    simulation_only=True,
                    live_execution_enabled=False,
                    message=f"Primary route {route} {'is available' if available else 'is missing'}.",
                )
            )
        return statuses

    def required_routes(self) -> dict[str, str]:
        return dict(self.MODULE_ROUTES)
