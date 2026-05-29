from backend.client_acceptance.acceptance_models import DeliveryReadiness
from backend.dashboard.dashboard_state_provider import DashboardStateProvider, dashboard_state_provider


class ReadinessScoreBuilder:
    """Build final client delivery readiness scores for dashboard display."""

    REMAINING_ITEMS = [
        "MT5 Demo Execution Bridge",
        "Multi-Account Trade Copier",
        "Execution Confirmation Tracking",
        "VPS Deployment",
        "Indian Broker Integration",
    ]

    def __init__(self, state_provider: DashboardStateProvider | None = None) -> None:
        self.state_provider = state_provider or dashboard_state_provider

    def build_readiness(self) -> DeliveryReadiness:
        state = self.state_provider.build_state()
        readiness_flags = {
            "dashboard_ready": state.dashboard_ready,
            "orchestration_ready": state.client_demo_ready,
            "monitoring_ready": state.dashboard_status in {"HEALTHY", "WARNING", "READY"},
            "broker_ready": state.client_demo_ready,
            "portfolio_ready": state.client_demo_ready,
            "control_center_ready": state.client_demo_ready,
            "simulation_ready": state.client_demo_ready,
            "deployment_ready": state.deployment_ready,
            "client_demo_ready": state.client_demo_ready,
        }
        completed = sum(1 for value in readiness_flags.values() if value)
        score = state.client_readiness_score
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
