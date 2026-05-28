from backend.phase3_readiness.phase3_module_registry import Phase3ModuleRegistry


class Phase3ClientReadinessReportBuilder:
    """Build a client-facing Phase 3 MVP readiness summary."""

    def __init__(self, registry: Phase3ModuleRegistry | None = None) -> None:
        self.registry = registry or Phase3ModuleRegistry()

    def build_report(self) -> dict:
        return {
            "phase": "Phase 3",
            "client_mvp_status": "BACKEND_READY_FOR_VPS_DASHBOARD_PREPARATION",
            "completed_backend_modules": list(self.registry.required_routes().keys()),
            "supported_markets": ["EURUSD", "XAUUSD", "NIFTY50"],
            "supported_brokers": ["STARTRADER", "FXPRO", "VANTAGE"],
            "pending_client_delivery_items": [
                "VPS dashboard",
                "MT5 demo execution",
                "Indian broker integration",
                "deployment hardening",
                "live execution approval",
            ],
            "safety_summary": "Phase 3 remains simulation-only with live execution disabled.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
