import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

HEALTH_PATH = PROJECT_ROOT / "backend/analytics/strategy_health_monitor_service.py"
ALERT_PATH = PROJECT_ROOT / "backend/analytics/risk_alert_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
REPORTING_PATH = PROJECT_ROOT / "backend/client_analytics/reporting_engine_service.py"

ROUTES = {
    "/analytics/strategy-health/status",
    "/analytics/strategy-health/current",
    "/analytics/strategy-health/history",
    "/analytics/risk-alerts/status",
    "/analytics/risk-alerts/current",
    "/analytics/risk-alerts/history",
    "/client-analytics/reports-v5/strategy-health",
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


def sample_backtest_result() -> Any:
    metrics = SimpleNamespace(total_trades=12, winning_trades=8, net_profit=60.0, average_rr=1.8, expectancy=5.0)
    return SimpleNamespace(
        metrics=metrics,
        total_trades=12,
        winning_trades=8,
        net_profit=60.0,
        average_rr=1.8,
        start_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 5, 13, tzinfo=timezone.utc),
        trade_history=[],
    )


def closed_trade(ticket: str, result: str, pnl: float, day: int) -> dict[str, Any]:
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
        "opened_at": f"2026-06-{day:02d}T10:00:00+00:00",
        "closed_at": f"2026-06-{day:02d}T11:00:00+00:00",
        "close_price": 1.11 if pnl > 0 else 1.095 if pnl < 0 else 1.1,
        "profit_loss": pnl,
        "net_pnl": pnl,
        "realized_pnl": pnl,
        "duration_minutes": 60,
        "exit_reason": "TAKE_PROFIT" if result == "WIN" else "STOP_LOSS" if result == "LOSS" else "MANUAL",
        "result": result,
        "notes": "sample closed strategy health trade",
    }


def seed_healthy(journal) -> None:
    journal.record_trade_closed(closed_trade("1", "WIN", 4.0, 1))
    journal.record_trade_closed(closed_trade("2", "WIN", 3.0, 2))
    journal.record_trade_closed(closed_trade("3", "LOSS", -1.0, 3))
    journal.record_trade_closed(closed_trade("4", "WIN", 2.5, 4))


def seed_alerting(journal) -> None:
    journal.record_trade_closed(closed_trade("1", "WIN", 2.0, 1))
    journal.record_trade_closed(closed_trade("2", "LOSS", -3.0, 2))
    journal.record_trade_closed(closed_trade("3", "LOSS", -4.0, 3))
    journal.record_trade_closed(closed_trade("4", "LOSS", -5.0, 4))


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/analytics/strategy-health/status")
        alerts = client.get("/analytics/risk-alerts/status")
        report = client.get("/client-analytics/reports-v5/strategy-health")
        passed = not missing and status.status_code == 200 and alerts.status_code == 200 and report.status_code == 200 and safety_ok(status.json()) and safety_ok(alerts.json()) and safety_ok(report.json())
        return show("Strategy health and risk alert routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Strategy health and risk alert routes exist", False, str(exc))


def verify_health_scoring() -> bool:
    try:
        from backend.analytics.performance_validation_service import PerformanceValidationService
        from backend.analytics.strategy_health_monitor_service import StrategyHealthMonitorService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            seed_healthy(journal)
            validation = PerformanceValidationService(journal, FakeBacktestStorage([sample_backtest_result()]))
            service = StrategyHealthMonitorService(journal, validation)
            health = service.get_current_health()
            passed = (
                health["status"] == "READY"
                and health["health_score"] > 0
                and health["classification"] in {"EXCELLENT", "GOOD", "WATCHLIST", "DEGRADED", "CRITICAL"}
                and health["components"]["win_rate_health"] > 0
                and health["components"]["rr_health"] > 0
                and health["components"]["drawdown_health"] >= 0
                and safety_ok(health)
            )
            return show("Health scoring works from closed demo trades", passed, str(health))
    except Exception as exc:
        return show("Health scoring works from closed demo trades", False, str(exc))


def verify_alert_generation() -> bool:
    try:
        from backend.analytics.performance_validation_service import PerformanceValidationService
        from backend.analytics.risk_alert_service import RiskAlertService
        from backend.analytics.strategy_health_monitor_service import StrategyHealthMonitorService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            seed_alerting(journal)
            validation = PerformanceValidationService(journal, FakeBacktestStorage([sample_backtest_result()]))
            health = StrategyHealthMonitorService(journal, validation)
            alerts = RiskAlertService(journal, validation, health).get_current_alerts()
            types = {alert["alert_type"] for alert in alerts["alerts"]}
            passed = (
                alerts["status"] == "READY"
                and alerts["active_alerts"] >= 2
                and "CONSECUTIVE_LOSSES" in types
                and "NEGATIVE_EXPECTANCY" in types
                and all(alert["severity"] in {"INFO", "WARNING", "HIGH", "CRITICAL"} for alert in alerts["alerts"])
                and safety_ok(alerts)
            )
            return show("Risk alert generation works", passed, str(alerts))
    except Exception as exc:
        return show("Risk alert generation works", False, str(exc))


def verify_insufficient_data_no_fake_values() -> bool:
    try:
        from backend.analytics.risk_alert_service import RiskAlertService
        from backend.analytics.strategy_health_monitor_service import StrategyHealthMonitorService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            health = StrategyHealthMonitorService(journal).get_current_health()
            alerts = RiskAlertService(journal).get_current_alerts()
            passed = (
                health["status"] == "INSUFFICIENT_DATA"
                and health["health_score"] is None
                and alerts["status"] == "INSUFFICIENT_DATA"
                and alerts["active_alerts"] == 0
                and alerts["alerts"] == []
                and safety_ok(health)
                and safety_ok(alerts)
            )
            return show("Insufficient data handling avoids fake trades and PnL", passed, str({"health": health, "alerts": alerts}))
    except Exception as exc:
        return show("Insufficient data handling avoids fake trades and PnL", False, str(exc))


def verify_reports_v5() -> bool:
    try:
        from backend.client_analytics.reporting_engine_service import ReportingEngineService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            seed_alerting(journal)
            reporting = ReportingEngineService(journal)
            reporting.performance_validation.backtest_storage = FakeBacktestStorage([sample_backtest_result()])
            report = reporting.build_strategy_health_v5()
            passed = (
                report["status"] == "READY"
                and report["report_type"] == "STRATEGY_HEALTH_V5"
                and report["strategy_health_report"]["overall_health_score"] is not None
                and report["strategy_health_report"]["active_alerts"]
                and report["strategy_health_report"]["recommendations"]
                and safety_ok(report)
            )
            return show("Reports V5 strategy health builds", passed, str(report))
    except Exception as exc:
        return show("Reports V5 strategy health builds", False, str(exc))


def verify_dashboard_panels_exist() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "Strategy Health Panel",
        "Risk Alerts Panel",
        "/analytics/strategy-health/current",
        "/analytics/risk-alerts/current",
        "Health Score",
        "Win Rate Health",
        "No active strategy alerts.",
    ]
    missing = [token for token in required if token not in text]
    return show("Dashboard strategy health and alert panels exist", not missing, ", ".join(missing))


def verify_no_execution_logic() -> bool:
    health_text = HEALTH_PATH.read_text(encoding="utf-8")
    alert_text = ALERT_PATH.read_text(encoding="utf-8")
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
    present = [item for item in forbidden if item in health_text or item in alert_text or item in reporting_text]
    return show("No execution logic modified or enabled", not present and sorted(matches) == allowed, ", ".join(present + matches))


def main() -> int:
    print("Phase 18 Day 7 Strategy Health Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_health_scoring(),
        verify_alert_generation(),
        verify_insufficient_data_no_fake_values(),
        verify_reports_v5(),
        verify_dashboard_panels_exist(),
        verify_no_execution_logic(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
