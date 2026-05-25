from backend.database.persistence_service import PersistenceService
from backend.trade_journal.journal_models import JournalEntry, RiskAlert
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class JournalStorage:
    """Database adapter that leaves analytics usable if persistence is unavailable."""

    def save_entry(self, entry: JournalEntry) -> bool:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return False
            service.save_trade_journal_entry(
                {
                    "journal_id": entry.journal_id,
                    "symbol": entry.symbol,
                    "timeframe": entry.timeframe,
                    "strategy_name": entry.strategy_name,
                    "session_name": entry.session_name,
                    "pnl": entry.pnl,
                    "outcome": entry.outcome,
                    "simulated": entry.simulated,
                    "timestamp": entry.timestamp,
                    "entry_json": entry.model_dump(mode="json"),
                }
            )
            return True
        except Exception as exc:
            logger.warning("Trade journal persistence failed safely: %s", exc)
            return False
        finally:
            service.close()

    def get_recent_entries(self, limit: int = 50) -> list[JournalEntry]:
        return self._load(lambda service: service.get_recent_trade_journal_entries(limit))

    def get_entries_by_symbol(self, symbol: str, limit: int = 500) -> list[JournalEntry]:
        normalized = symbol.strip().upper()
        return self._load(lambda service: service.get_trade_journal_entries_by_symbol(normalized, limit))

    def get_entries_by_timeframe(self, timeframe: str, limit: int = 500) -> list[JournalEntry]:
        normalized = timeframe.strip().upper()
        return self._load(lambda service: service.get_trade_journal_entries_by_timeframe(normalized, limit))

    def save_alert(self, alert: RiskAlert) -> bool:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return False
            service.save_risk_alert_entry(
                {
                    "alert_id": alert.alert_id,
                    "severity": alert.severity,
                    "category": alert.category,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                    "alert_json": alert.model_dump(mode="json"),
                }
            )
            return True
        except Exception as exc:
            logger.warning("Risk alert persistence failed safely: %s", exc)
            return False
        finally:
            service.close()

    def get_recent_alerts(self, limit: int = 50) -> list[RiskAlert]:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return []
            return [
                RiskAlert.model_validate(row["alert_json"])
                for row in service.get_recent_risk_alert_entries(limit)
            ]
        except Exception as exc:
            logger.warning("Risk alert retrieval failed safely: %s", exc)
            return []
        finally:
            service.close()

    def _load(self, query) -> list[JournalEntry]:
        service = PersistenceService()
        try:
            if not service.initialize_database():
                return []
            return [JournalEntry.model_validate(row["entry_json"]) for row in query(service)]
        except Exception as exc:
            logger.warning("Trade journal retrieval failed safely: %s", exc)
            return []
        finally:
            service.close()
