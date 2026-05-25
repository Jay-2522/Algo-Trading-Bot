from typing import Any

from backend.database.persistence_service import PersistenceService
from backend.orchestration.orchestration_models import PipelineResult
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class OrchestrationLogger:
    """Capture orchestration outcomes in memory and in durable audit logs when possible."""

    def __init__(self) -> None:
        self._recent_results: list[dict[str, Any]] = []

    def log_pipeline_result(self, result: PipelineResult) -> dict[str, Any]:
        serialized = result.model_dump(mode="json")
        self._recent_results.append(serialized)
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return {"persisted": False, "message": "Database initialization unavailable."}
            record = service.save_audit_log(
                {
                    "component": "orchestration.engine",
                    "event_type": "PIPELINE_DECISION",
                    "message": "; ".join(result.decision.reasons),
                    "severity": "INFO" if result.decision.approved else "WARNING",
                    "metadata_json": {
                        "symbol": result.symbol,
                        "approved": result.decision.approved,
                        "final_action": result.decision.final_action,
                        "blocked_by": result.decision.blocked_by,
                        "confidence": result.decision.confidence,
                        "ai_action": result.decision.ai_decision.get("action"),
                        "strategy_trend": result.decision.strategy_snapshot.get("trend_analysis", {}).get("trend"),
                        "news_risk_level": result.decision.news_status.get("risk_level"),
                        "risk_level": result.decision.risk_status.get("risk_level"),
                        "simulation_only": True,
                        "errors": result.errors,
                    },
                }
            )
            return {"persisted": True, "audit_log_id": record["id"]}
        except Exception as exc:
            logger.warning("Orchestration audit persistence unavailable: %s", exc)
            return {"persisted": False, "message": "Audit persistence unavailable."}
        finally:
            service.close()

    def get_recent_results(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._recent_results[-limit:]
