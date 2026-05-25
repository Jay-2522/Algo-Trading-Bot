import sys
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError


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


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
            "/ai/status",
            "/news/status",
            "/orchestration/status",
            "/backtesting/status",
            "/streaming/status",
            "/trading-loop/status",
            "/trade-journal/status",
            "/trade-journal/recent",
            "/trade-journal/risk-analytics",
            "/trade-journal/exposure",
            "/trade-journal/risk-alerts",
            "/trade-journal/overall-performance",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("FastAPI app imports and old/trade-journal routes are registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports and old/trade-journal routes are registered", False, str(exc))
        return False


def verify_journal_creation_and_safety() -> bool:
    try:
        from backend.trade_journal.journal_models import JournalEntry
        from backend.trade_journal.journal_service import JournalService

        class MemoryStorage:
            def __init__(self):
                self.entries = []
                self.alerts = []

            def save_entry(self, entry):
                self.entries.append(entry)
                return True

            def get_recent_entries(self, limit=50):
                return list(reversed(self.entries))[:limit]

            def save_alert(self, alert):
                self.alerts.append(alert)
                return True

        class NoAuditLogger:
            def log_event(self, *args, **kwargs):
                return {"persisted": False}

        storage = MemoryStorage()
        service = JournalService(storage=storage, logger=NoAuditLogger())
        entry = service.add_entry(
            JournalEntry(symbol="eurusd", pnl=40.0, rr=2.0, outcome="WIN", strategy_name="Trend", session_name="london")
        )
        blocked = False
        try:
            JournalEntry(symbol="XAUUSD", simulated=False)
        except ValidationError:
            blocked = True
        passed = entry.symbol == "EURUSD" and len(service.get_recent_entries()) == 1 and blocked
        print_result("Journal creation stores simulated records and rejects live records", passed)
        return passed
    except Exception as exc:
        print_result("Journal creation stores simulated records and rejects live records", False, str(exc))
        return False


def verify_performance_tracker() -> bool:
    try:
        from backend.trade_journal.journal_models import JournalEntry
        from backend.trade_journal.performance_tracker import PerformanceTracker

        tracker = PerformanceTracker()
        zero = tracker.calculate([])
        metrics = tracker.calculate(
            [
                JournalEntry(pnl=100, rr=2, outcome="WIN"),
                JournalEntry(pnl=-50, rr=-1, outcome="LOSS"),
            ]
        )
        passed = (
            zero["total_trades"] == 0
            and zero["win_rate"] == 0.0
            and metrics["win_rate"] == 50.0
            and metrics["profit_factor"] == 2.0
            and metrics["expectancy"] == 25.0
        )
        print_result("Performance tracker calculates safely for zero and populated datasets", passed)
        return passed
    except Exception as exc:
        print_result("Performance tracker calculates safely for zero and populated datasets", False, str(exc))
        return False


def verify_risk_analytics() -> bool:
    try:
        from backend.trade_journal.journal_models import JournalEntry
        from backend.trade_journal.risk_analytics import RiskAnalyticsService

        entries = [
            JournalEntry(pnl=-300, outcome="LOSS"),
            JournalEntry(pnl=-300, outcome="LOSS"),
            JournalEntry(pnl=-300, outcome="LOSS"),
        ]
        analytics = RiskAnalyticsService().calculate_risk_analytics(entries)
        passed = (
            analytics.daily_drawdown_percent > 0
            and analytics.consecutive_losses == 3
            and analytics.max_consecutive_losses == 3
            and any("concentrated" in message for message in analytics.risk_alerts)
        )
        print_result("Risk analytics calculates drawdown, loss streak, and session concentration", passed)
        return passed
    except Exception as exc:
        print_result("Risk analytics calculates drawdown, loss streak, and session concentration", False, str(exc))
        return False


def verify_drawdown_tracker() -> bool:
    try:
        from backend.trade_journal.drawdown_tracker import DrawdownTracker

        tracker = DrawdownTracker(10000)
        tracker.update_equity(10500)
        status = tracker.update_equity(9450)
        passed = status["peak_balance"] == 10500.0 and status["current_drawdown_percent"] == 10.0
        print_result("Drawdown tracker maintains peak and realized drawdown", passed)
        return passed
    except Exception as exc:
        print_result("Drawdown tracker maintains peak and realized drawdown", False, str(exc))
        return False


def verify_exposure_and_alerts() -> bool:
    try:
        from backend.trade_journal.exposure_monitor import ExposureMonitor
        from backend.trade_journal.journal_models import JournalEntry
        from backend.trade_journal.performance_tracker import PerformanceTracker
        from backend.trade_journal.risk_alerts import RiskAlertService
        from backend.trade_journal.risk_analytics import RiskAnalyticsService

        entries = [
            JournalEntry(symbol="XAUUSD", entry_price=100, stop_loss=97, outcome="OPEN"),
            JournalEntry(pnl=-100, outcome="LOSS"),
            JournalEntry(pnl=-100, outcome="LOSS"),
            JournalEntry(pnl=-100, outcome="LOSS"),
        ]
        exposure = ExposureMonitor().calculate_exposure(entries)
        analytics = RiskAnalyticsService().calculate_risk_analytics(entries)
        alerts = RiskAlertService().generate_alerts(analytics, exposure, PerformanceTracker().calculate(entries))
        passed = (
            exposure.total_exposure_percent == 3.0
            and exposure.highest_risk_symbol == "XAUUSD"
            and any(alert.category == "OVEREXPOSURE" for alert in alerts)
            and all(alert.severity in {"INFO", "WARNING", "CRITICAL"} for alert in alerts)
        )
        print_result("Exposure monitor and risk alert generation operate safely", passed)
        return passed
    except Exception as exc:
        print_result("Exposure monitor and risk alert generation operate safely", False, str(exc))
        return False


def verify_api() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/trade-journal/status")
        created = client.post("/trade-journal/add-test-entry")
        recent = client.get("/trade-journal/recent")
        symbol = client.get("/trade-journal/symbol-performance/XAUUSD")
        session = client.get("/trade-journal/session-performance/LONDON")
        risk = client.get("/trade-journal/risk-analytics")
        exposure = client.get("/trade-journal/exposure")
        alerts = client.get("/trade-journal/risk-alerts")
        overall = client.get("/trade-journal/overall-performance")
        passed = (
            status.status_code == 200
            and status.json()["mode"] == "SIMULATION_ANALYTICS_ONLY"
            and status.json()["live_execution_enabled"] is False
            and created.status_code == 200
            and created.json()["simulated"] is True
            and recent.status_code == 200
            and len(recent.json()) >= 1
            and symbol.status_code == 200
            and session.status_code == 200
            and risk.status_code == 200
            and exposure.status_code == 200
            and alerts.status_code == 200
            and overall.status_code == 200
        )
        print_result("Journal analytics APIs return JSON-safe simulation-only results", passed)
        return passed
    except Exception as exc:
        print_result("Journal analytics APIs return JSON-safe simulation-only results", False, str(exc))
        return False


def main() -> int:
    print("Day 14 Advanced Risk Analytics and Trade Journal Verification")
    print("=" * 59)
    checks = [
        verify_path("backend/trade_journal", "trade_journal package exists", is_dir=True),
        verify_path("backend/trade_journal/journal_models.py", "journal_models.py exists"),
        verify_path("backend/trade_journal/journal_storage.py", "journal_storage.py exists"),
        verify_path("backend/trade_journal/journal_service.py", "journal_service.py exists"),
        verify_path("backend/trade_journal/performance_tracker.py", "performance_tracker.py exists"),
        verify_path("backend/trade_journal/risk_analytics.py", "risk_analytics.py exists"),
        verify_path("backend/trade_journal/exposure_monitor.py", "exposure_monitor.py exists"),
        verify_path("backend/trade_journal/drawdown_tracker.py", "drawdown_tracker.py exists"),
        verify_path("backend/trade_journal/risk_alerts.py", "risk_alerts.py exists"),
        verify_path("backend/trade_journal/journal_logger.py", "journal_logger.py exists"),
        verify_path("backend/api/trade_journal_routes.py", "trade_journal_routes.py exists"),
        verify_routes(),
        verify_journal_creation_and_safety(),
        verify_performance_tracker(),
        verify_risk_analytics(),
        verify_drawdown_tracker(),
        verify_exposure_and_alerts(),
        verify_api(),
    ]
    print("=" * 59)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
