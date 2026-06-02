import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/client_analytics/__init__.py",
        "backend/client_analytics/analytics_models.py",
        "backend/client_analytics/analytics_data_collector.py",
        "backend/client_analytics/performance_calculator.py",
        "backend/client_analytics/client_analytics_service.py",
        "backend/client_analytics/analytics_store.py",
        "backend/api/client_analytics_routes.py",
        "docs/phase-11-day-1-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Client analytics package, routes, and docs exist", not missing, ", ".join(missing))


def verify_imports_and_calculator() -> bool:
    try:
        from backend.client_analytics.analytics_data_collector import AnalyticsDataCollector
        from backend.client_analytics.analytics_models import (
            ClientAnalyticsOverview,
            RiskAnalyticsSummary,
            SessionPerformanceSummary,
            SymbolPerformanceSummary,
        )
        from backend.client_analytics.analytics_store import AnalyticsStore
        from backend.client_analytics.client_analytics_service import ClientAnalyticsService
        from backend.client_analytics.performance_calculator import PerformanceCalculator

        collector = AnalyticsDataCollector()
        calculator = PerformanceCalculator()
        service = ClientAnalyticsService(collector=collector, calculator=calculator, store=AnalyticsStore())
        overview = service.get_overview()
        passed = (
            all(
                item is not None
                for item in [
                    AnalyticsDataCollector,
                    PerformanceCalculator,
                    ClientAnalyticsService,
                    AnalyticsStore,
                    ClientAnalyticsOverview,
                    SymbolPerformanceSummary,
                    SessionPerformanceSummary,
                    RiskAnalyticsSummary,
                ]
            )
            and isinstance(collector.collect_all(), dict)
            and calculator.calculate_win_rate(0, 0) == 0.0
            and calculator.calculate_net_pnl([]) == 0.0
            and calculator.calculate_profit_factor([]) == 0.0
            and calculator.calculate_max_drawdown([]) == 0.0
            and overview.net_pnl == 0.0
            and overview.win_rate == 0.0
            and overview.simulation_only is True
            and overview.demo_execution is True
            and overview.live_execution_enabled is False
            and overview.broker_execution_enabled is False
        )
        return show("Analytics imports, collector, calculator, and safe zero-PnL defaults work", passed)
    except Exception as exc:
        return show("Analytics imports, collector, calculator, and safe zero-PnL defaults work", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = [
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/symbols",
            "/client-analytics/symbols/{symbol}",
            "/client-analytics/sessions",
            "/client-analytics/risk",
            "/client-analytics/snapshots/latest",
        ]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        status = client.get("/client-analytics/status")
        overview = client.get("/client-analytics/overview")
        symbols = client.get("/client-analytics/symbols")
        nifty = client.get("/client-analytics/symbols/NIFTY50")
        sessions = client.get("/client-analytics/sessions")
        risk = client.get("/client-analytics/risk")
        latest = client.get("/client-analytics/snapshots/latest")
        status_payload = status.json()
        overview_payload = overview.json()
        nifty_payload = nifty.json()
        passed = (
            routes_ok
            and all(response.status_code == 200 for response in [status, overview, symbols, nifty, sessions, risk, latest])
            and status_payload["status"] == "OPERATIONAL"
            and status_payload["nifty50_status"] == "PLACEHOLDER_ONLY"
            and overview_payload["net_pnl"] == 0.0
            and overview_payload["win_rate"] == 0.0
            and overview_payload["simulation_only"] is True
            and overview_payload["demo_execution"] is True
            and overview_payload["live_execution_enabled"] is False
            and overview_payload["broker_execution_enabled"] is False
            and nifty_payload["symbol"] == "NIFTY50"
            and nifty_payload["total_signals"] == 0
            and nifty_payload["net_pnl"] == 0.0
        )
        return show("Client analytics routes work with safe NIFTY50 placeholder and no fake PnL", passed)
    except Exception as exc:
        return show("Client analytics routes work with safe NIFTY50 placeholder and no fake PnL", False, str(exc))


def verify_preserved_routes_and_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/strategy-execution-bridge/demo-approval/status",
            "/strategy-execution-bridge/operations/status",
            "/production-readiness/status",
            "/backup/status",
            "/security/status",
            "/client-analytics/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 9 and Phase 10 routes are preserved and no new order_send exists", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 9 and Phase 10 routes are preserved and no new order_send exists", False, str(exc))


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        analytics = [module for module in modules if module["name"] == "client_analytics"]
        passed = (
            len(analytics) == 1
            and analytics[0]["route"] == "/client-analytics/status"
            and analytics[0]["simulation_only"] is True
            and analytics[0]["live_execution_enabled"] is False
        )
        return show("System module registry includes client analytics", passed)
    except Exception as exc:
        return show("System module registry includes client analytics", False, str(exc))


def main() -> int:
    print("Phase 11 Day 1 Client Analytics Foundation Verification")
    print("=" * 62)
    checks = [
        verify_files(),
        verify_imports_and_calculator(),
        verify_routes(),
        verify_preserved_routes_and_safety(),
        verify_module_registry(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
