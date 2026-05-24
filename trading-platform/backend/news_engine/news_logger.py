from backend.database.persistence_service import PersistenceService
from backend.news_engine.news_models import NewsRiskStatus
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class NewsLogger:
    """Persist macro-risk checks into platform audit history when available."""

    def log_risk_check(self, symbol: str, status: NewsRiskStatus) -> dict:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return {"persisted": False, "message": "Database initialization unavailable."}
            record = service.save_audit_log(
                {
                    "component": "news.intelligence",
                    "event_type": "NEWS_RISK_CHECK",
                    "message": status.reason,
                    "severity": status.risk_level,
                    "metadata_json": {
                        "symbol": symbol,
                        "risk_status": status.model_dump(mode="json"),
                    },
                }
            )
            return {"persisted": True, "audit_log_id": record["id"]}
        except Exception as exc:
            logger.warning("Unable to persist news risk check: %s", exc)
            return {"persisted": False, "message": "News risk persistence unavailable."}
        finally:
            service.close()

