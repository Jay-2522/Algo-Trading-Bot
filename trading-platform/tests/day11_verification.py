import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str, is_dir: bool = False) -> bool:
    target = PROJECT_ROOT / path
    passed = target.is_dir() if is_dir else target.is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def fixed_request():
    from backend.backtesting.backtest_models import BacktestRequest

    return BacktestRequest(
        symbol="XAUUSD",
        timeframe="M15",
        start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
        max_candles=400,
        initial_balance=10000,
    )


def verify_routes() -> bool:
    try:
        from backend.main import app

        methods_by_path = {
            (route.path, method)
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
        }
        required = {
            ("/health", "GET"),
            ("/status", "GET"),
            ("/market-data/timeframes", "GET"),
            ("/strategy/session", "GET"),
            ("/risk/status", "GET"),
            ("/execution/status", "GET"),
            ("/mt5/status", "GET"),
            ("/database/status", "GET"),
            ("/ai/status", "GET"),
            ("/news/status", "GET"),
            ("/orchestration/status", "GET"),
            ("/backtesting/status", "GET"),
            ("/backtesting/run/{symbol}", "POST"),
            ("/backtesting/results/recent", "GET"),
            ("/backtesting/result/{backtest_id}", "GET"),
            ("/backtesting/metrics/{backtest_id}", "GET"),
            ("/backtesting/equity/{backtest_id}", "GET"),
        }
        missing = sorted(required - methods_by_path)
        print_result("FastAPI app imports with old and backtesting routes registered", not missing, str(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports with old and backtesting routes registered", False, str(exc))
        return False


def verify_historical_data() -> bool:
    try:
        from backend.backtesting.historical_data_loader import HistoricalDataLoader

        loader = HistoricalDataLoader()
        first = loader.load_candles(fixed_request())
        second = loader.load_candles(fixed_request())
        passed = (
            len(first) == 400
            and first[0].model_dump() == second[0].model_dump()
            and first[-1].model_dump() == second[-1].model_dump()
            and first[0].high >= first[0].close >= first[0].low
        )
        print_result("HistoricalDataLoader generates deterministic OHLCV candles", passed)
        return passed
    except Exception as exc:
        print_result("HistoricalDataLoader generates deterministic OHLCV candles", False, str(exc))
        return False


def verify_engine_and_bad_candles() -> bool:
    try:
        from backend.backtesting.backtest_engine import BacktestEngine
        from backend.backtesting.historical_data_loader import HistoricalDataLoader

        engine = BacktestEngine()
        result = engine.run(fixed_request(), persist=False)
        good_candle = HistoricalDataLoader().load_candles(fixed_request())[0]
        partial = engine.run(
            fixed_request(),
            candles=[
                good_candle,
                {"timestamp": good_candle.timestamp, "open": 2, "high": 1, "low": 3, "close": 2, "volume": 5},
            ],
            persist=False,
        )
        passed = (
            result.status == "COMPLETED"
            and result.execution_mode == "SIMULATION_ONLY"
            and result.total_trades > 0
            and len(result.equity_curve) == result.total_trades + 1
            and len(partial.errors) == 1
        )
        print_result("BacktestEngine replays trades and skips bad candles safely", passed)
        return passed
    except Exception as exc:
        print_result("BacktestEngine replays trades and skips bad candles safely", False, str(exc))
        return False


def verify_metrics_safety() -> bool:
    try:
        from backend.backtesting.equity_curve import EquityCurveBuilder
        from backend.backtesting.performance_analyzer import PerformanceAnalyzer

        timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        curve = EquityCurveBuilder().build(10000, [], timestamp)
        metrics = PerformanceAnalyzer().analyze(10000, [], curve)
        passed = (
            metrics.total_trades == 0
            and metrics.profit_factor == 0
            and metrics.sharpe_ratio == 0
            and metrics.max_drawdown == 0
        )
        print_result("PerformanceAnalyzer handles zero-trade datasets safely", passed)
        return passed
    except Exception as exc:
        print_result("PerformanceAnalyzer handles zero-trade datasets safely", False, str(exc))
        return False


def verify_database_storage() -> bool:
    try:
        from backend.backtesting.backtest_engine import BacktestEngine
        from backend.backtesting.backtest_storage import BacktestStorage
        from backend.database.models import BacktestRunRecord, BacktestTradeRecord

        storage = BacktestStorage()
        result = BacktestEngine(storage=storage).run(fixed_request(), persist=True)
        fetched = storage.get_result(result.backtest_id)
        passed = (
            BacktestRunRecord.__tablename__ == "backtest_runs"
            and BacktestTradeRecord.__tablename__ == "backtest_trades"
            and fetched is not None
            and fetched.backtest_id == result.backtest_id
            and storage.get_metrics(result.backtest_id) is not None
        )
        print_result("BacktestStorage persists reports and trade tables", passed)
        return passed
    except Exception as exc:
        print_result("BacktestStorage persists reports and trade tables", False, str(exc))
        return False


def verify_api_responses() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/backtesting/status")
        response = client.post(
            "/backtesting/run/XAUUSD",
            json={
                "timeframe": "M15",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-06T00:00:00Z",
                "initial_balance": 10000,
                "max_candles": 400,
            },
        )
        payload = response.json()
        backtest_id = payload.get("backtest_id", "")
        recent = client.get("/backtesting/results/recent")
        metrics = client.get(f"/backtesting/metrics/{backtest_id}")
        equity = client.get(f"/backtesting/equity/{backtest_id}")
        passed = (
            status.status_code == 200
            and status.json()["execution_mode"] == "SIMULATION_ONLY"
            and response.status_code == 200
            and payload["execution_mode"] == "SIMULATION_ONLY"
            and payload["approved"] is True
            and recent.status_code == 200
            and metrics.status_code == 200
            and equity.status_code == 200
        )
        print_result("Backtesting API returns stored simulation-only reports", passed)
        return passed
    except Exception as exc:
        print_result("Backtesting API returns stored simulation-only reports", False, str(exc))
        return False


def main() -> int:
    print("Day 11 Backtesting Engine Verification")
    print("=" * 38)
    checks = [
        verify_path("backend/backtesting", "backtesting folder exists", is_dir=True),
        verify_path("backend/backtesting/backtest_models.py", "backtest_models.py exists"),
        verify_path("backend/backtesting/historical_data_loader.py", "historical_data_loader.py exists"),
        verify_path("backend/backtesting/trade_simulator.py", "trade_simulator.py exists"),
        verify_path("backend/backtesting/performance_analyzer.py", "performance_analyzer.py exists"),
        verify_path("backend/backtesting/equity_curve.py", "equity_curve.py exists"),
        verify_path("backend/backtesting/backtest_engine.py", "backtest_engine.py exists"),
        verify_path("backend/backtesting/backtest_service.py", "backtest_service.py exists"),
        verify_path("backend/backtesting/backtest_storage.py", "backtest_storage.py exists"),
        verify_path("backend/api/backtesting_routes.py", "backtesting_routes.py exists"),
        verify_routes(),
        verify_historical_data(),
        verify_engine_and_bad_candles(),
        verify_metrics_safety(),
        verify_database_storage(),
        verify_api_responses(),
    ]
    print("=" * 38)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
