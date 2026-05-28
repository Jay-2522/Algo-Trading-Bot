import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/monitoring/__init__.py",
        "backend/monitoring/monitoring_models.py",
        "backend/monitoring/system_monitor.py",
        "backend/monitoring/module_health_tracker.py",
        "backend/monitoring/execution_monitor.py",
        "backend/monitoring/webhook_monitor.py",
        "backend/monitoring/broker_monitor.py",
        "backend/monitoring/alert_engine.py",
        "backend/monitoring/alert_store.py",
        "backend/monitoring/monitoring_service.py",
        "backend/api/monitoring_routes.py",
        "docs/phase-3-day-19-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/monitoring/status",
            "/monitoring/system-health",
            "/monitoring/modules",
            "/monitoring/execution",
            "/monitoring/webhooks",
            "/monitoring/brokers",
            "/monitoring/alerts",
            "/monitoring/alerts/{alert_id}/acknowledge",
            "/execution-queue/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Monitoring files and routes exist", files_ok and routes_ok)


def verify_system_and_modules() -> bool:
    try:
        from backend.monitoring.module_health_tracker import ModuleHealthTracker
        from backend.monitoring.system_monitor import SystemMonitor

        tracker = ModuleHealthTracker()
        statuses = tracker.get_module_statuses()
        healthy_snapshot = SystemMonitor(tracker).generate_snapshot()
        tracker.register_warning("webhooks", "Webhook replay warnings detected.")
        warning_status = tracker.check_module("webhooks")
        tracker.register_failure("execution_queue", "Queue failed-safe state detected.")
        failed_status = tracker.check_module("execution_queue")
        degraded_snapshot = SystemMonitor(tracker).generate_snapshot()
        passed = (
            len(statuses) > 0
            and healthy_snapshot.overall_status == "HEALTHY"
            and healthy_snapshot.simulation_only is True
            and healthy_snapshot.live_execution_enabled is False
            and warning_status.status == "WARNING"
            and warning_status.healthy is True
            and failed_status.status == "FAILED"
            and failed_status.healthy is False
            and degraded_snapshot.overall_status in {"DEGRADED", "CRITICAL"}
        )
        return show("System monitor and module tracker work", passed)
    except Exception as exc:
        return show("System monitor and module tracker work", False, str(exc))


def verify_alerts_and_monitors() -> bool:
    try:
        from backend.monitoring.alert_engine import AlertEngine
        from backend.monitoring.alert_store import AlertStore
        from backend.monitoring.broker_monitor import BrokerMonitor
        from backend.monitoring.execution_monitor import ExecutionMonitor
        from backend.monitoring.monitoring_service import MonitoringService
        from backend.monitoring.webhook_monitor import WebhookMonitor

        store = AlertStore()
        engine = AlertEngine(store)
        alert = engine.create_alert("WARNING", "test", "Test alert", "Monitoring verification.")
        classified = engine.classify_event({"event_type": "REPLAY_ATTACK", "source": "webhooks"})
        acknowledged = store.acknowledge_alert(alert.alert_id)
        execution_summary = ExecutionMonitor().generate_execution_summary()
        webhook_metrics = WebhookMonitor().get_webhook_metrics()
        broker_health = BrokerMonitor().get_broker_health()
        service = MonitoringService(alert_store=store)
        passed = (
            alert.acknowledged is True
            and acknowledged is not None
            and classified is not None
            and len(store.list_alerts()) >= 2
            and execution_summary.queued_items >= 0
            and execution_summary.cancelled >= 0
            and webhook_metrics["simulation_only"] is True
            and webhook_metrics["live_execution_enabled"] is False
            and "STARTRADER" in broker_health["tracked_brokers"]
            and broker_health["simulation_only"] is True
            and service.get_status()["simulation_only"] is True
        )
        return show("Alert engine, execution monitor, webhook monitor, and broker monitor work", passed)
    except Exception as exc:
        return show("Alert engine, execution monitor, webhook monitor, and broker monitor work", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/monitoring/status")
        system = client.get("/monitoring/system-health")
        modules = client.get("/monitoring/modules")
        execution = client.get("/monitoring/execution")
        webhooks = client.get("/monitoring/webhooks")
        brokers = client.get("/monitoring/brokers")
        alerts = client.get("/monitoring/alerts")
        alert_id = None
        if alerts.json():
            alert_id = alerts.json()[0]["alert_id"]
        ack = client.post(f"/monitoring/alerts/{alert_id}/acknowledge") if alert_id else None
        queue = client.get("/execution-queue/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and system.status_code == 200
            and system.json()["simulation_only"] is True
            and system.json()["live_execution_enabled"] is False
            and modules.status_code == 200
            and len(modules.json()) > 0
            and execution.status_code == 200
            and webhooks.status_code == 200
            and webhooks.json()["simulation_only"] is True
            and brokers.status_code == 200
            and brokers.json()["live_execution_enabled"] is False
            and alerts.status_code == 200
            and (ack is None or ack.status_code == 200)
            and queue.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Monitoring APIs are JSON-safe and preserve execution queue routes", passed)
    except Exception as exc:
        return show("Monitoring APIs are JSON-safe and preserve execution queue routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 19 Monitoring Verification")
    print("=" * 48)
    checks = [
        verify_files_and_routes(),
        verify_system_and_modules(),
        verify_alerts_and_monitors(),
        verify_api_and_safety(),
    ]
    print("=" * 48)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
