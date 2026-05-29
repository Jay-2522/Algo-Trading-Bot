from backend.client_acceptance.acceptance_models import DeliveryReadiness
from backend.client_acceptance.readiness_score_builder import ReadinessScoreBuilder


class DeliveryReadinessService:
    """Client acceptance facade for final delivery readiness dashboard outputs."""

    def __init__(self, score_builder: ReadinessScoreBuilder | None = None) -> None:
        self.score_builder = score_builder or ReadinessScoreBuilder()

    def get_status(self) -> dict:
        readiness = self.get_readiness()
        return {
            "status": "CLIENT_ACCEPTANCE_READY",
            "mode": "DELIVERY_READINESS_DISPLAY_ONLY",
            "overall_score": readiness.overall_score,
            "deployment_ready": readiness.deployment_ready,
            "client_demo_ready": readiness.client_demo_ready,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "message": "Client acceptance dashboard is ready for delivery review. Live execution remains disabled.",
        }

    def get_readiness(self) -> DeliveryReadiness:
        return self.score_builder.build_readiness()

    def get_checklist(self) -> list[dict]:
        return self.score_builder.build_checklist()

    def get_remaining_items(self) -> dict:
        readiness = self.get_readiness()
        return {
            "remaining_items": readiness.remaining_items,
            "summary": "These items are planned for the next production/delivery phase.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
