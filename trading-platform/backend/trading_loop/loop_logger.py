from typing import Any

from backend.database.persistence_service import PersistenceService
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class LoopLogger:
    """Persist loop lifecycle and simulation decision events when available."""

    def log_event(self, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> dict:
        logger.info("%s: %s", event_type, message)
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return {"persisted": False, "message": "Database initialization unavailable."}
            record = service.save_audit_log(
                {
                    "component": "trading_loop.engine",
                    "event_type": event_type,
                    "message": message,
                    "severity": "INFO",
                    "metadata_json": {
                        "simulation_only": True,
                        "live_execution_enabled": False,
                        **(metadata or {}),
                    },
                }
            )
            return {"persisted": True, "audit_log_id": record["id"]}
        except Exception as exc:
            logger.warning("Trading-loop audit persistence unavailable: %s", exc)
            return {"persisted": False, "message": "Audit persistence unavailable."}
        finally:
            service.close()
