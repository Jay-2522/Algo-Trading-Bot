from backend.nifty50.nifty_broker_order_preview import NIFTYBrokerOrderPreview
from backend.nifty50.nifty_execution_models import NIFTYExecutionAuditEvent, NIFTYExecutionIntent, NIFTYOrderPreview
from backend.nifty50.nifty_execution_store import NIFTYExecutionStore
from backend.nifty50.nifty_execution_validator import NIFTYExecutionValidator
from backend.nifty50.nifty_risk_models import NIFTYTradeCandidate


class NIFTYExecutionBridge:
    def __init__(
        self,
        store: NIFTYExecutionStore | None = None,
        validator: NIFTYExecutionValidator | None = None,
        previewer: NIFTYBrokerOrderPreview | None = None,
    ) -> None:
        self.store = store or NIFTYExecutionStore()
        self.validator = validator or NIFTYExecutionValidator()
        self.previewer = previewer or NIFTYBrokerOrderPreview(self.validator)

    def get_status(self) -> dict:
        return {
            "status": "EXECUTION_BRIDGE_READY",
            "preview_only": True,
            "execution_ready": False,
            "execution_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def create_intent_from_candidate(self, candidate: NIFTYTradeCandidate, broker_id: str | None = None, quantity: int = 1) -> NIFTYExecutionIntent:
        reasons = self.validator.validate_candidate(candidate)
        intent = NIFTYExecutionIntent(
            candidate_id=candidate.candidate_id,
            action=candidate.action,
            quantity=quantity,
            broker_id=broker_id,
            strategy_confidence=candidate.confidence,
            risk_decision_id=candidate.risk_decision_id,
        )
        self.store.store_intent(intent)
        self.store.store_audit_event(
            NIFTYExecutionAuditEvent(
                stage="CREATE_INTENT",
                status="PREVIEW_ONLY" if not reasons else "VALIDATION_WARNINGS",
                entity_id=intent.intent_id,
                message="; ".join(reasons) if reasons else "Execution intent created for preview only.",
            )
        )
        return intent

    def preview_order(self, intent: NIFTYExecutionIntent) -> NIFTYOrderPreview:
        preview = self.previewer.create_preview(intent)
        self.store.store_preview(preview)
        self.store.store_audit_event(
            NIFTYExecutionAuditEvent(
                stage="PREVIEW_ORDER",
                status=preview.preview_status,
                entity_id=preview.preview_id,
                message="Order preview generated; no broker order was placed.",
            )
        )
        return preview

    def list_previews(self) -> list[NIFTYOrderPreview]:
        return self.store.list_previews()

    def get_preview(self, preview_id: str) -> NIFTYOrderPreview | None:
        return self.store.get_preview(preview_id)
