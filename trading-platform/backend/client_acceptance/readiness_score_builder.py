from backend.client_acceptance.acceptance_models import DeliveryReadiness


class ReadinessScoreBuilder:
    """Build final client delivery readiness scores for dashboard display."""

    REMAINING_ITEMS = [
        "MT5 Demo Execution Bridge",
        "Multi-Account Trade Copier",
        "Execution Confirmation Tracking",
        "VPS Deployment",
        "Indian Broker Integration",
    ]

    def build_readiness(self) -> DeliveryReadiness:
        readiness_flags = {
            "dashboard_ready": True,
            "orchestration_ready": True,
            "monitoring_ready": True,
            "broker_ready": True,
            "portfolio_ready": True,
            "control_center_ready": True,
            "simulation_ready": True,
            "deployment_ready": False,
            "client_demo_ready": True,
        }
        completed = sum(1 for value in readiness_flags.values() if value)
        score = round((completed / len(readiness_flags)) * 100)
        return DeliveryReadiness(
            overall_score=score,
            remaining_items=self.REMAINING_ITEMS,
            simulation_only=True,
            live_execution_enabled=False,
            **readiness_flags,
        )

    def build_checklist(self) -> list[dict]:
        readiness = self.build_readiness()
        return [
            {"label": "Dashboard", "complete": readiness.dashboard_ready, "status": "COMPLETE"},
            {"label": "Monitoring", "complete": readiness.monitoring_ready, "status": "COMPLETE"},
            {"label": "Portfolio", "complete": readiness.portfolio_ready, "status": "COMPLETE"},
            {"label": "Demo Mode", "complete": readiness.client_demo_ready, "status": "COMPLETE"},
            {"label": "Control Center", "complete": readiness.control_center_ready, "status": "COMPLETE"},
            {"label": "Webhooks", "complete": readiness.orchestration_ready, "status": "COMPLETE"},
            {"label": "Routing", "complete": True, "status": "COMPLETE"},
            {"label": "Allocation", "complete": True, "status": "COMPLETE"},
            {"label": "Queue", "complete": readiness.simulation_ready, "status": "COMPLETE"},
            {"label": "VPS Deployment", "complete": readiness.deployment_ready, "status": "PENDING"},
        ]
