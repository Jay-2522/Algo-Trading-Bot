from sqlalchemy.exc import SQLAlchemyError

from backend.backtesting.backtest_models import BacktestResult, PerformanceMetrics
from backend.database.database import SessionLocal, init_db
from backend.database.models import BacktestRunRecord, BacktestTradeRecord
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class BacktestStorage:
    """Durably store historical simulation reports without touching broker records."""

    def initialize(self) -> bool:
        return init_db()

    def save_result(self, result: BacktestResult) -> bool:
        if not self.initialize():
            return False
        serialized = result.model_dump(mode="json")
        try:
            with SessionLocal() as db:
                db.add(
                    BacktestRunRecord(
                        backtest_id=result.backtest_id,
                        symbol=result.symbol,
                        timeframe=result.timeframe,
                        start_date=result.start_date,
                        end_date=result.end_date,
                        initial_balance=result.initial_balance,
                        ending_balance=result.ending_balance,
                        net_profit=result.net_profit,
                        approved=result.approved,
                        status=result.status,
                        execution_mode=result.execution_mode,
                        metrics_json=result.metrics.model_dump(mode="json"),
                        equity_curve_json=[point.model_dump(mode="json") for point in result.equity_curve],
                        result_json=serialized,
                    )
                )
                for trade in result.trade_history:
                    db.add(
                        BacktestTradeRecord(
                            backtest_id=result.backtest_id,
                            trade_id=trade.trade_id,
                            symbol=trade.symbol,
                            side=trade.side,
                            entry_time=trade.entry_time,
                            exit_time=trade.exit_time,
                            entry_price=trade.entry_price,
                            exit_price=trade.exit_price,
                            pnl=trade.pnl,
                            outcome=trade.outcome,
                            trade_json=trade.model_dump(mode="json"),
                        )
                    )
                db.commit()
            return True
        except SQLAlchemyError as exc:
            logger.warning("Backtest result persistence failed safely: %s", exc)
            return False

    def get_recent_results(self, limit: int = 50) -> list[BacktestResult]:
        if not self.initialize():
            return []
        with SessionLocal() as db:
            rows = (
                db.query(BacktestRunRecord)
                .order_by(BacktestRunRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [BacktestResult.model_validate(row.result_json) for row in rows]

    def get_result(self, backtest_id: str) -> BacktestResult | None:
        if not self.initialize():
            return None
        with SessionLocal() as db:
            row = (
                db.query(BacktestRunRecord)
                .filter(BacktestRunRecord.backtest_id == backtest_id)
                .first()
            )
            return BacktestResult.model_validate(row.result_json) if row else None

    def get_metrics(self, backtest_id: str) -> PerformanceMetrics | None:
        result = self.get_result(backtest_id)
        return result.metrics if result else None

    def get_equity_curve(self, backtest_id: str) -> list[dict] | None:
        result = self.get_result(backtest_id)
        return [point.model_dump(mode="json") for point in result.equity_curve] if result else None
