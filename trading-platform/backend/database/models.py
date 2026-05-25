from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base, CreatedAtMixin


class TradeRecord(CreatedAtMixin, Base):
    __tablename__ = "trade_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    order_type: Mapped[str] = mapped_column(String(16), nullable=False)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionLogRecord(CreatedAtMixin, Base):
    __tablename__ = "execution_log_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RiskEventRecord(CreatedAtMixin, Base):
    __tablename__ = "risk_event_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class StrategySnapshotRecord(CreatedAtMixin, Base):
    __tablename__ = "strategy_snapshot_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    trend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    liquidity_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    structure_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class MT5AccountSnapshotRecord(CreatedAtMixin, Base):
    __tablename__ = "mt5_account_snapshot_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    login: Mapped[int | None] = mapped_column(Integer, nullable=True)
    server: Mapped[str | None] = mapped_column(String(128), nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    leverage: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MarketSnapshotRecord(CreatedAtMixin, Base):
    __tablename__ = "market_snapshot_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    ask: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class SystemAuditLogRecord(CreatedAtMixin, Base):
    __tablename__ = "system_audit_log_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    component: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class BacktestRunRecord(CreatedAtMixin, Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    backtest_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    ending_balance: Mapped[float] = mapped_column(Float, nullable=False)
    net_profit: Mapped[float] = mapped_column(Float, nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    equity_curve_json: Mapped[list] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class BacktestTradeRecord(CreatedAtMixin, Base):
    __tablename__ = "backtest_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    backtest_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    trade_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    pnl: Mapped[float] = mapped_column(Float, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_json: Mapped[dict] = mapped_column(JSON, nullable=False)


# Compatibility exports retained for the Day 1 foundation checks.
Trade = TradeRecord
RiskEvent = RiskEventRecord
MarketSnapshot = MarketSnapshotRecord
StrategyLog = StrategySnapshotRecord
SystemLog = SystemAuditLogRecord


class Position(CreatedAtMixin, Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    asset_class: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
