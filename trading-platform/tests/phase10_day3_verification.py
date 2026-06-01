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
        "backend/monitoring/__init__.py",
        "backend/monitoring/logging_config.py",
        "backend/monitoring/log_store.py",
        "backend/monitoring/process_monitor.py",
        "backend/monitoring/system_metrics.py",
        "backend/monitoring/api_monitor.py",
        "backend/monitoring/mt5_monitor.py",
        "backend/monitoring/platform_health_service.py",
        "backend/api/monitoring_routes.py",
        "docs/phase-10-day-3-progress.md",
        "docs/monitoring-guide.md",
        "logs/.gitkeep",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Monitoring package, docs, and logs directory exist", not missing, ", ".join(missing))


def verify_imports_and_logging() -> bool:
    try:
        from backend.monitoring.api_monitor import APIMonitor
        from backend.monitoring.log_store import LogStore
        from backend.monitoring.logging_config import PLATFORM_LOG, configure_logging
        from backend.monitoring.mt5_monitor import MT5Monitor
        from backend.monitoring.platform_health_service import PlatformHealthOverview, PlatformHealthService
        from backend.monitoring.process_monitor import ProcessMonitor
        from backend.monitoring.system_metrics import SystemMetrics

        logger = configure_logging()
        logger.info("Phase 10 Day 3 verification log entry.")
        imported = all(
            item is not None
            for item in [
                APIMonitor,
                LogStore,
                MT5Monitor,
                PlatformHealthOverview,
                PlatformHealthService,
                ProcessMonitor,
                SystemMetrics,
            ]
        )
        return show("Monitoring modules import and platform log is configured", imported and PLATFORM_LOG.exists())
    except Exception as exc:
        return show("Monitoring modules import and platform log is configured", False, str(exc))


def verify_routes_and_endpoints() -> bool:
    try:
        from backend.main import app

        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        required = [
            "/monitoring/status",
            "/monitoring/health",
            "/monitoring/metrics",
            "/monitoring/processes",
            "/monitoring/apis",
            "/monitoring/mt5",
            "/monitoring/logs",
            "/monitoring/logs/errors",
            "/monitoring/logs/warnings",
        ]
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        status = client.get("/monitoring/status")
        health = client.get("/monitoring/health")
        metrics = client.get("/monitoring/metrics")
        processes = client.get("/monitoring/processes")
        apis = client.get("/monitoring/apis")
        mt5 = client.get("/monitoring/mt5")
        logs = client.get("/monitoring/logs")
        errors = client.get("/monitoring/logs/errors")
        warnings = client.get("/monitoring/logs/warnings")

        status_payload = status.json()
        health_payload = health.json()
        process_payload = processes.json()
        api_payload = apis.json()
        mt5_payload = mt5.json()
        passed = (
            routes_ok
            and status.status_code == 200
            and health.status_code == 200
            and metrics.status_code == 200
            and processes.status_code == 200
            and apis.status_code == 200
            and mt5.status_code == 200
            and logs.status_code == 200
            and errors.status_code == 200
            and warnings.status_code == 200
            and status_payload["status"] in {"OPERATIONAL", "operational"}
            and health_payload["health_score"] >= 70
            and "cpu_percent" in metrics.json()
            and process_payload["backend_process"]["running"] is True
            and api_payload["total_routes"] > 0
            and mt5_payload["demo_mode"] is True
        )
        safety = all(
            payload["simulation_only"] is True
            and payload["demo_execution"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
            for payload in [status_payload, health_payload, process_payload, api_payload, mt5_payload]
        )
        return show("Monitoring routes and endpoints work with safety flags", passed and safety)
    except Exception as exc:
        return show("Monitoring routes and endpoints work with safety flags", False, str(exc))


def verify_deployment_integration_and_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        client = TestClient(app)
        readiness = client.get("/deployment/readiness").json()
        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/deployment/status",
            "/deployment/readiness",
            "/monitoring/status",
            "/monitoring/health",
            "/strategy-execution-bridge/operations/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = (
            readiness["monitoring_ready"] is True
            and readiness["simulation_only"] is True
            and readiness["demo_execution"] is True
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and not missing
            and not missing_ws
            and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        )
        return show("Monitoring readiness integrated and Phase 10/Phase 9 safety preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Monitoring readiness integrated and Phase 10/Phase 9 safety preserved", False, str(exc))


def main() -> int:
    print("Phase 10 Day 3 Monitoring Verification")
    print("=" * 48)
    checks = [
        verify_files(),
        verify_imports_and_logging(),
        verify_routes_and_endpoints(),
        verify_deployment_integration_and_safety(),
    ]
    print("=" * 48)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
