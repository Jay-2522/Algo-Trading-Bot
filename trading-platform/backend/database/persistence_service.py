from datetime import datetime
from typing import Any

from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal, init_db
from backend.database.repositories import (
    ExecutionLogRepository,
    MT5AccountSnapshotRepository,
    MarketSnapshotRepository,
    RiskEventRepository,
    StrategySnapshotRepository,
    SystemAuditLogRepository,
    TradeRepository,
)


class PersistenceService:
    """Repository facade for durable trading-platform memory records."""

    def __init__(self, db: Session | None = None) -> None:
        self._owns_session = db is None
        self.db = db or SessionLocal()
        self.trades = TradeRepository(self.db)
        self.execution_logs = ExecutionLogRepository(self.db)
        self.risk_events = RiskEventRepository(self.db)
        self.strategy_snapshots = StrategySnapshotRepository(self.db)
        self.mt5_account_snapshots = MT5AccountSnapshotRepository(self.db)
        self.market_snapshots = MarketSnapshotRepository(self.db)
        self.audit_logs = SystemAuditLogRepository(self.db)

    def initialize_database(self) -> bool:
        return init_db()

    def save_trade(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.trades.create_trade(data))

    def save_execution_log(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.execution_logs.create_log(data))

    def save_risk_event(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.risk_events.create_risk_event(data))

    def save_strategy_snapshot(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.strategy_snapshots.create_snapshot(data))

    def save_mt5_account_snapshot(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.mt5_account_snapshots.create_snapshot(data))

    def save_market_snapshot(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.market_snapshots.create_snapshot(data))

    def save_audit_log(self, data: dict[str, Any]) -> dict:
        return self._serialize(self.audit_logs.create_audit_log(data))

    def get_recent_trades(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.trades.get_recent_trades(limit))

    def get_recent_execution_logs(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.execution_logs.get_recent_logs(limit))

    def get_recent_risk_events(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.risk_events.get_recent_risk_events(limit))

    def get_recent_strategy_snapshots(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.strategy_snapshots.get_recent_snapshots(limit=limit))

    def get_recent_market_snapshots(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.market_snapshots.get_recent_snapshots(limit=limit))

    def get_recent_audit_logs(self, limit: int = 50) -> list[dict]:
        return self._serialize_many(self.audit_logs.get_recent_audit_logs(limit))

    def close(self) -> None:
        if self._owns_session:
            self.db.close()

    def _serialize_many(self, records: list) -> list[dict]:
        return [self._serialize(record) for record in records]

    def _serialize(self, record) -> dict:
        result: dict[str, Any] = {}
        for attribute in inspect(record).mapper.column_attrs:
            value = getattr(record, attribute.key)
            result[attribute.key] = value.isoformat() if isinstance(value, datetime) else value
        return result

