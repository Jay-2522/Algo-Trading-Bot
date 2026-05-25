from backend.database.persistence_service import PersistenceService
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class JournalLogger:
    """Write journal audit activity when persistence is present."""

    def log_event(self, event_type: str, message: str, metadata: dict | None = None) -> dict:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return {"persisted": False, "message": "Database initialization unavailable."}
            record = service.save_audit_log(
                {
                    "component": "trade_journal.analytics",
                    "event_type": event_type,
                    "message": message,
                    "severity": "INFO",
                    "metadata_json": metadata or {},
                }
            )
            return {"persisted": True, "audit_log_id": record["id"]}
        except Exception as exc:
            logger.warning("Journal audit logging failed safely: %s", exc)
            return {"persisted": False, "message": "Journal audit persistence unavailable."}
        finally:
            service.close()
