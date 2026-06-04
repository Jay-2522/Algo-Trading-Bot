from typing import Any

from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.strategy_engine.strategy_service import StrategyService
from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision
from backend.strategy_execution_bridge.queue_preview_adapter import QueuePreviewAdapter
from backend.strategy_execution_bridge.signal_eligibility_validator import SignalEligibilityValidator
from backend.strategy_execution_bridge.strategy_to_intent_mapper import StrategyToIntentMapper


class StrategyExecutionBridgeService:
    """Convert strategy signals into safe execution intent previews, never orders."""

    def __init__(
        self,
        validator: SignalEligibilityValidator | None = None,
        mapper: StrategyToIntentMapper | None = None,
        store: BridgeDecisionStore | None = None,
        strategy_service: StrategyService | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        queue_preview_adapter: QueuePreviewAdapter | None = None,
    ) -> None:
        self.validator = validator or SignalEligibilityValidator()
        self.mapper = mapper or StrategyToIntentMapper()
        self.store = store or BridgeDecisionStore()
        self.strategy_service = strategy_service or StrategyService()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator()
        self.queue_preview_adapter = queue_preview_adapter or QueuePreviewAdapter()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "STRATEGY_TO_EXECUTION_INTENT_BRIDGE",
            "queue_preview_only": True,
            "preview_only": True,
            "execution_allowed": False,
            "queue_preview_adapter_ready": True,
            "end_to_end_demo_flow_ready": True,
            "min_confidence": self.validator.MIN_CONFIDENCE,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def evaluate_signal(self, signal: Any) -> StrategyBridgeDecision:
        return self._evaluate(signal, create_preview=False)

    def create_queue_preview_from_signal(self, signal: Any) -> StrategyBridgeDecision:
        return self._evaluate(signal, create_preview=True)

    def evaluate_and_preview_signal(self, signal: Any) -> StrategyBridgeDecision:
        return self._evaluate(signal, create_preview=True)

    def _evaluate(self, signal: Any, create_preview: bool) -> StrategyBridgeDecision:
        signal_id = str(self._get(signal, "signal_id", "manual-signal"))
        symbol = str(self._get(signal, "symbol", "UNKNOWN")).upper()
        action = str(self._get(signal, "action", "WAIT")).upper()
        confidence = float(self._get(signal, "confidence", 0.0) or 0.0)

        try:
            eligible, status, reasons = self.validator.validate(signal)
            if not eligible:
                return self.store.store_decision(
                    StrategyBridgeDecision(
                        signal_id=signal_id,
                        symbol=symbol,
                        action=action,
                        confidence=confidence,
                        eligible=False,
                        rejection_reasons=reasons,
                        queue_preview_created=False,
                        queue_preview_status="REJECTED",
                        intent_status="REJECTED",
                        risk_approved=False,
                        bridge_status=status,
                    )
                )

            intent = self.mapper.map_signal_to_intent(signal)
            risk_decision = self.risk_evaluator.evaluate_single_account_request(
                {
                    "request_id": intent.intent_id,
                    "signal_id": intent.source_signal_id,
                    "symbol": intent.symbol,
                    "canonical_symbol": intent.symbol,
                    "action": intent.action,
                    "lot": intent.total_lot,
                    "requested_lot": intent.total_lot,
                    "confirm_demo_execution": True,
                    "live_execution_enabled": False,
                    "broker_execution_enabled": False,
                }
            )
            if not risk_decision.approved:
                return self.store.store_decision(
                    StrategyBridgeDecision(
                        signal_id=signal_id,
                        symbol=symbol,
                        action=action,
                        confidence=confidence,
                        eligible=False,
                        rejection_reasons=risk_decision.rejection_reasons,
                        mapped_intent=intent,
                        risk_decision_id=risk_decision.decision_id,
                        queue_preview_created=False,
                        queue_preview_status="REJECTED",
                        intent_status="MAPPED",
                        risk_approved=False,
                        bridge_status="REJECTED_RISK_ENGINE",
                    )
                )

            if not create_preview:
                return self.store.store_decision(
                    StrategyBridgeDecision(
                        signal_id=signal_id,
                        symbol=symbol,
                        action=action,
                        confidence=confidence,
                        eligible=True,
                        mapped_intent=intent,
                        risk_decision_id=risk_decision.decision_id,
                        queue_preview_created=False,
                        queue_preview_status="NOT_CREATED",
                        intent_status="MAPPED",
                        risk_approved=True,
                        bridge_status="APPROVED_FOR_QUEUE_PREVIEW",
                    )
                )

            preview = self.queue_preview_adapter.create_preview_from_intent(intent, risk_decision=risk_decision)
            return self.store.store_decision(
                StrategyBridgeDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    action=action,
                    confidence=confidence,
                    eligible=True,
                    mapped_intent=intent,
                    queue_preview_id=preview["queue_preview_id"],
                    risk_decision_id=risk_decision.decision_id,
                    queue_preview_created=True,
                    queue_preview_status="CREATED",
                    intent_status="MAPPED",
                    risk_approved=True,
                    bridge_status="APPROVED_FOR_QUEUE_PREVIEW",
                )
            )
        except Exception as exc:
            return self.store.store_decision(
                StrategyBridgeDecision(
                    signal_id=signal_id,
                    symbol=symbol,
                    action=action,
                    confidence=confidence,
                    eligible=False,
                    rejection_reasons=[f"Bridge failed safe: {exc}"],
                    queue_preview_created=False,
                    queue_preview_status="FAILED_SAFE",
                    intent_status="REJECTED",
                    risk_approved=False,
                    queue_error=str(exc),
                    bridge_status="FAILED_SAFE",
                )
            )

    def bridge_latest_xauusd_signal(self) -> StrategyBridgeDecision:
        signal = self.strategy_service.analyze_xauusd()
        return self.evaluate_signal(signal)

    def bridge_latest_eurusd_signal(self) -> StrategyBridgeDecision:
        signal = self.strategy_service.analyze_eurusd()
        return self.evaluate_signal(signal)

    def list_decisions(self, limit: int = 100):
        return self.store.list_decisions(limit)

    def get_decision(self, decision_id: str):
        return self.store.get_decision(decision_id)

    def close(self) -> None:
        self.strategy_service.close()

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
