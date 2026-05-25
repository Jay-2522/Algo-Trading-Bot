from backend.backtesting.backtest_engine import BacktestEngine
from backend.backtesting.backtest_models import BacktestRequest, BacktestResult, PerformanceMetrics
from backend.backtesting.backtest_storage import BacktestStorage


class BacktestService:
    """API-facing facade for offline replay and stored performance reports."""

    def __init__(
        self,
        engine: BacktestEngine | None = None,
        storage: BacktestStorage | None = None,
    ) -> None:
        self.storage = storage or BacktestStorage()
        self.engine = engine or BacktestEngine(storage=self.storage)

    def get_status(self) -> dict:
        return {
            "status": "operational",
            "mode": "DETERMINISTIC_HISTORICAL_REPLAY",
            "execution_mode": "SIMULATION_ONLY",
            "external_data_enabled": False,
            "live_execution_enabled": False,
            "supported_timeframes": ["M1", "M5", "M15", "H1", "H4"],
        }

    def run_backtest(self, request: BacktestRequest) -> BacktestResult:
        return self.engine.run(request, persist=True)

    def get_recent_results(self, limit: int = 50) -> list[BacktestResult]:
        return self.storage.get_recent_results(limit)

    def get_result(self, backtest_id: str) -> BacktestResult | None:
        return self.storage.get_result(backtest_id)

    def get_metrics(self, backtest_id: str) -> PerformanceMetrics | None:
        return self.storage.get_metrics(backtest_id)

    def get_equity_curve(self, backtest_id: str) -> list[dict] | None:
        return self.storage.get_equity_curve(backtest_id)
