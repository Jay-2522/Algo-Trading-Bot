from typing import Any, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database.models import (
    ExecutionLogRecord,
    MT5AccountSnapshotRecord,
    MarketSnapshotRecord,
    RiskEventRecord,
    RiskAlertEntryRecord,
    StrategySnapshotRecord,
    SystemAuditLogRecord,
    TradeJournalEntryRecord,
    TradeRecord,
)


RecordType = TypeVar("RecordType")


class BaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _create(self, model: type[RecordType], record_data: dict[str, Any]) -> RecordType:
        record = model(**record_data)
        try:
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record
        except SQLAlchemyError:
            self.db.rollback()
            raise


class TradeRepository(BaseRepository):
    def create_trade(self, record_data: dict[str, Any]) -> TradeRecord:
        return self._create(TradeRecord, record_data)

    def get_recent_trades(self, limit: int = 50) -> list[TradeRecord]:
        return self.db.query(TradeRecord).order_by(TradeRecord.created_at.desc()).limit(limit).all()

    def get_trade_by_execution_id(self, execution_id: str) -> TradeRecord | None:
        return self.db.query(TradeRecord).filter(TradeRecord.execution_id == execution_id).first()


class ExecutionLogRepository(BaseRepository):
    def create_log(self, record_data: dict[str, Any]) -> ExecutionLogRecord:
        return self._create(ExecutionLogRecord, record_data)

    def get_logs_by_execution_id(self, execution_id: str) -> list[ExecutionLogRecord]:
        return (
            self.db.query(ExecutionLogRecord)
            .filter(ExecutionLogRecord.execution_id == execution_id)
            .order_by(ExecutionLogRecord.created_at.desc())
            .all()
        )

    def get_recent_logs(self, limit: int = 50) -> list[ExecutionLogRecord]:
        return self.db.query(ExecutionLogRecord).order_by(ExecutionLogRecord.created_at.desc()).limit(limit).all()


class RiskEventRepository(BaseRepository):
    def create_risk_event(self, record_data: dict[str, Any]) -> RiskEventRecord:
        return self._create(RiskEventRecord, record_data)

    def get_recent_risk_events(self, limit: int = 50) -> list[RiskEventRecord]:
        return self.db.query(RiskEventRecord).order_by(RiskEventRecord.created_at.desc()).limit(limit).all()


class StrategySnapshotRepository(BaseRepository):
    def create_snapshot(self, record_data: dict[str, Any]) -> StrategySnapshotRecord:
        return self._create(StrategySnapshotRecord, record_data)

    def get_recent_snapshots(self, symbol: str | None = None, limit: int = 50) -> list[StrategySnapshotRecord]:
        query = self.db.query(StrategySnapshotRecord)
        if symbol:
            query = query.filter(StrategySnapshotRecord.symbol == symbol)
        return query.order_by(StrategySnapshotRecord.created_at.desc()).limit(limit).all()


class MT5AccountSnapshotRepository(BaseRepository):
    def create_snapshot(self, record_data: dict[str, Any]) -> MT5AccountSnapshotRecord:
        return self._create(MT5AccountSnapshotRecord, record_data)

    def get_latest_snapshot(self) -> MT5AccountSnapshotRecord | None:
        return self.db.query(MT5AccountSnapshotRecord).order_by(MT5AccountSnapshotRecord.created_at.desc()).first()


class MarketSnapshotRepository(BaseRepository):
    def create_snapshot(self, record_data: dict[str, Any]) -> MarketSnapshotRecord:
        return self._create(MarketSnapshotRecord, record_data)

    def get_recent_snapshots(self, symbol: str | None = None, limit: int = 50) -> list[MarketSnapshotRecord]:
        query = self.db.query(MarketSnapshotRecord)
        if symbol:
            query = query.filter(MarketSnapshotRecord.symbol == symbol)
        return query.order_by(MarketSnapshotRecord.created_at.desc()).limit(limit).all()


class SystemAuditLogRepository(BaseRepository):
    def create_audit_log(self, record_data: dict[str, Any]) -> SystemAuditLogRecord:
        return self._create(SystemAuditLogRecord, record_data)

    def get_recent_audit_logs(self, limit: int = 50) -> list[SystemAuditLogRecord]:
        return self.db.query(SystemAuditLogRecord).order_by(SystemAuditLogRecord.created_at.desc()).limit(limit).all()


class TradeJournalRepository(BaseRepository):
    def create_entry(self, record_data: dict[str, Any]) -> TradeJournalEntryRecord:
        return self._create(TradeJournalEntryRecord, record_data)

    def get_recent_entries(self, limit: int = 50) -> list[TradeJournalEntryRecord]:
        return self.db.query(TradeJournalEntryRecord).order_by(TradeJournalEntryRecord.timestamp.desc()).limit(limit).all()

    def get_entries_by_symbol(self, symbol: str, limit: int = 500) -> list[TradeJournalEntryRecord]:
        return (
            self.db.query(TradeJournalEntryRecord)
            .filter(TradeJournalEntryRecord.symbol == symbol)
            .order_by(TradeJournalEntryRecord.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_entries_by_timeframe(self, timeframe: str, limit: int = 500) -> list[TradeJournalEntryRecord]:
        return (
            self.db.query(TradeJournalEntryRecord)
            .filter(TradeJournalEntryRecord.timeframe == timeframe)
            .order_by(TradeJournalEntryRecord.timestamp.desc())
            .limit(limit)
            .all()
        )


class RiskAlertEntryRepository(BaseRepository):
    def create_alert(self, record_data: dict[str, Any]) -> RiskAlertEntryRecord:
        return self._create(RiskAlertEntryRecord, record_data)

    def get_recent_alerts(self, limit: int = 50) -> list[RiskAlertEntryRecord]:
        return self.db.query(RiskAlertEntryRecord).order_by(RiskAlertEntryRecord.timestamp.desc()).limit(limit).all()
