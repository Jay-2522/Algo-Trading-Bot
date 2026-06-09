import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/analytics/performance_validation_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
REPORTING_PATH = PROJECT_ROOT / "backend/client_analytics/reporting_engine_service.py"

ROUTES = {
    "/analytics/performance-validation/status",
    "/analytics/performance-validation/live",
    "/analytics/performance-validation/historical",
    "/analytics/performance-validation/compare",
    "/analytics/performance-validation/drift",
}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk(item)


def safety_ok(payload: Any) -> bool:
    for key, value in walk(payload):
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed", "mt5_order_send_used"} and value is not False:
            return False
    return True


class FakeBacktestStorage:
    def __init__(self, results: list[Any]) -> None:
        self.results = results

    def get_recent_results(self, limit: int = 50) -> list[Any]:
        return self.results[:limit]


def closed_trade(ticket: str, result: str, pnl: float, closed_at: str) -> dict[str, Any]:
    return {
        "trade_id": f"mt5_demo_{ticket}",
        "source": "MT5_DEMO",
        "environment": "DEMO",
        "symbol": "EURUSD",
        "side": "BUY",
        "lot": 0.01,
        "entry_price": 1.1,
        "stop_loss": 1.095,
        "take_profit": 1.11,
        "risk_reward_ratio": 2.0,
        "mt5_ticket": ticket,
        "opened_at": "2026-06-08T10:00:00+00:00",
        "closed_at": closed_at,
        "close_price": 1.11 if pnl > 0 else 1.095 if pnl < 0 else 1.1,
        "profit_loss": pnl,
        "net_pnl": pnl,
        "realized_pnl": pnl,
        "duration_minutes": 60,
        "exit_reason": "TAKE_PROFIT" if result == "WIN" else "STOP_LOSS" if result == "LOSS" else "MANUAL",
        "result": result,
        "notes": "sample closed validation trade",
    }


def sample_backtest_result() -> Any:
    metrics = SimpleNamespace(
        total_trades=10,
        winning_trades=8,
        net_profit=100.0,
        average_rr=2.0,
        expectancy=10.0,
    )
    trade_history = [
        SimpleNamespace(entry_time=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc), exit_time=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc)),
        SimpleNamespace(entry_time=datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc), exit_time=datetime(2026, 5, 2, 11, 30, tzinfo=timezone.utc)),
    ]
    return SimpleNamespace(
        metrics=metrics,
        total_trades=10,
        winning_trades=8,
        net_profit=100.0,
        average_rr=2.0,
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 11, tzinfo=timezone.utc),
        trade_history=trade_history,
    )


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/analytics/performance-validation/status")
        passed = not missing and status.status_code == 200 and safety_ok(status.json())
        return show("Performance validation routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Performance validation routes exist", False, str(exc))


def verify_comparison_engine() -> bool:
    try:
        from backend.analytics.performance_validation_service import PerformanceValidationService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_trade_closed(closed_trade("1", "WIN", 8.0, "2026-06-08T11:00:00+00:00"))
            journal.record_trade_closed(closed_trade("2", "LOSS", -2.0, "2026-06-09T11:00:00+00:00"))
            service = PerformanceValidationService(journal, FakeBacktestStorage([sample_backtest_result()]))
            comparison = service.compare()
            passed = (
                comparison["status"] == "READY"
                and comparison["live"]["trade_count"] == 2
                and comparison["historical"]["trade_count"] == 10
                and comparison["live"]["metrics"]["win_rate"] == 50.0
                and comparison["historical"]["metrics"]["win_rate"] == 80.0
                and comparison["variance"]["win_rate"] == -30.0
                and comparison["deviation"]["win_rate"] == -37.5
                and comparison["drift_score"] is not None
                and comparison["confidence_score"] is not None
                and safety_ok(comparison)
            )
            return show("Comparison engine works from real journal and backtest inputs", passed, str(comparison))
    except Exception as exc:
        return show("Comparison engine works from real journal and backtest inputs", False, str(exc))


def verify_drift_classification() -> bool:
    try:
        from backend.analytics.performance_validation_service import PerformanceValidationService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_trade_closed(closed_trade("1", "LOSS", -20.0, "2026-06-08T11:00:00+00:00"))
            service = PerformanceValidationService(journal, FakeBacktestStorage([sample_backtest_result()]))
            drift = service.detect_drift()
            passed = (
                drift["status"] == "READY"
                and drift["drift_status"] in {"MODERATE_DRIFT", "MAJOR_DRIFT"}
                and drift["contributing_metrics"]
                and "suggested_action" in drift
                and safety_ok(drift)
            )
            return show("Strategy drift classification works", passed, str(drift))
    except Exception as exc:
        return show("Strategy drift classification works", False, str(exc))


def verify_insufficient_data_no_fake_values() -> bool:
    try:
        from backend.analytics.performance_validation_service import PerformanceValidationService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            service = PerformanceValidationService(PersistentTradeJournalService(Path(tmp) / "trade_journal.json"), FakeBacktestStorage([]))
            comparison = service.compare()
            drift = service.detect_drift()
            passed = (
                comparison["status"] == "INSUFFICIENT_DATA"
                and comparison["live"]["metrics"]["net_pnl"] == 0.0
                and comparison["historical"]["metrics"]["net_pnl"] == 0.0
                and comparison["comparison_available"] is False
                and drift["drift_status"] == "INSUFFICIENT_DATA"
                and safety_ok(comparison)
                and safety_ok(drift)
            )
            return show("Insufficient data handling avoids fake trades and fake PnL", passed, str({"comparison": comparison, "drift": drift}))
    except Exception as exc:
        return show("Insufficient data handling avoids fake trades and fake PnL", False, str(exc))


def verify_reporting_v4() -> bool:
    try:
        from backend.client_analytics.reporting_engine_service import ReportingEngineService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_trade_closed(closed_trade("1", "WIN", 8.0, "2026-06-08T11:00:00+00:00"))
            reporting = ReportingEngineService(journal)
            reporting.performance_validation.backtest_storage = FakeBacktestStorage([sample_backtest_result()])
            report = reporting.build_performance_validation_v4()
            passed = (
                report["status"] == "READY"
                and report["report_type"] == "PERFORMANCE_VALIDATION_V4"
                and report["performance_validation_report"]["live_vs_historical_comparison"]["status"] == "READY"
                and report["performance_validation_report"]["drift_explanation"]["drift_status"] in {"NORMAL", "MINOR_DRIFT", "MODERATE_DRIFT", "MAJOR_DRIFT"}
                and safety_ok(report)
            )
            return show("Reports V4 performance validation builds", passed, str(report))
    except Exception as exc:
        return show("Reports V4 performance validation builds", False, str(exc))


def verify_dashboard_panel_exists() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "DEMO Validation Panel",
        "Historical vs Live Performance",
        "/analytics/performance-validation/compare",
        "/analytics/performance-validation/drift",
        "Historical Win Rate",
        "Live Win Rate",
        "Confidence Score",
    ]
    missing = [token for token in required if token not in text]
    return show("Dashboard validation panel exists", not missing, ", ".join(missing))


def verify_no_execution_logic() -> bool:
    service_text = SERVICE_PATH.read_text(encoding="utf-8")
    reporting_text = REPORTING_PATH.read_text(encoding="utf-8")
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    forbidden = ["mt5.order_send", "order_send(", "position_close", "close_order", "live_execution_enabled=True", "broker_execution_enabled=True"]
    present = [item for item in forbidden if item in service_text or item in reporting_text]
    return show("No execution logic modified or enabled", not present and sorted(matches) == allowed, ", ".join(present + matches))


def main() -> int:
    print("Phase 18 Day 6 Performance Validation Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_comparison_engine(),
        verify_drift_classification(),
        verify_insufficient_data_no_fake_values(),
        verify_reporting_v4(),
        verify_dashboard_panel_exists(),
        verify_no_execution_logic(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
