import json

from backend.ai_engine.ai_models import DecisionExplanation, TradeDecision
from backend.database.persistence_service import PersistenceService
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class DecisionLogger:
    """Persist advisory AI decisions for audit and later analytical study."""

    def log_decision(
        self,
        decision: TradeDecision,
        explanation: DecisionExplanation,
        context: dict | None = None,
    ) -> dict:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return {"persisted": False, "message": "Database initialization unavailable."}
            decision_payload = decision.model_dump(mode="json")
            explanation_payload = explanation.model_dump(mode="json")
            analysis_context = context or {}
            trend = analysis_context.get("trend_analysis", {}).get("trend")
            session_name = analysis_context.get("session_info", {}).get("current_session")
            audit = service.save_audit_log(
                {
                    "component": "ai.decision_engine",
                    "event_type": "AI_TRADE_QUALITY_DECISION",
                    "message": explanation.summary,
                    "severity": "INFO" if decision.approved else "WARNING",
                    "metadata_json": {
                        "decision": decision_payload,
                        "explanation": explanation_payload,
                    },
                }
            )
            snapshot = service.save_strategy_snapshot(
                {
                    "symbol": decision.symbol,
                    "timeframe": "M15",
                    "trend": trend,
                    "liquidity_summary": json.dumps(decision.signal_score.model_dump(mode="json")),
                    "structure_summary": explanation.summary,
                    "session_name": session_name,
                    "confidence": decision.confidence,
                    "metadata_json": {
                        "ai_decision": decision_payload,
                        "explanation": explanation_payload,
                        "market_regime": decision.regime.model_dump(mode="json"),
                    },
                }
            )
            return {"persisted": True, "audit_log_id": audit["id"], "snapshot_id": snapshot["id"]}
        except Exception as exc:
            logger.warning("Unable to persist AI decision: %s", exc)
            return {"persisted": False, "message": "AI decision persistence unavailable."}
        finally:
            service.close()
