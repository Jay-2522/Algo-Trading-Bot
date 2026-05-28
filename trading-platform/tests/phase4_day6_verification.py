import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_backend_files() -> bool:
    files = [
        "backend/control_center/__init__.py",
        "backend/control_center/control_models.py",
        "backend/control_center/safety_lock_manager.py",
        "backend/control_center/manual_override_service.py",
        "backend/control_center/control_audit_store.py",
        "backend/control_center/control_center_service.py",
        "backend/api/control_center_routes.py",
        "docs/phase-4-day-6-progress.md",
    ]
    return show("Control center backend files exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_frontend_files() -> bool:
    files = [
        "frontend/components/dashboard/ManualControlPanel.tsx",
        "frontend/components/dashboard/SafetyLockPanel.tsx",
        "frontend/components/dashboard/ControlAuditPanel.tsx",
        "frontend/components/dashboard/ConfirmActionModal.tsx",
    ]
    return show("Manual control dashboard components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes_registered() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/control-center/status",
            "/control-center/safety-state",
            "/control-center/audit-events",
            "/control-center/queue/pause",
            "/control-center/queue/resume",
            "/control-center/queue/{queue_id}/cancel",
            "/control-center/alerts/{alert_id}/acknowledge",
            "/control-center/emergency-stop-placeholder",
        }
        return show("Control center routes registered", expected <= routes)
    except Exception as exc:
        return show("Control center routes registered", False, str(exc))


def verify_control_center_api() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/control-center/status")
        state = client.get("/control-center/safety-state")
        pause = client.post("/control-center/queue/pause", json={"reason": "verification pause"})
        paused_state = client.get("/control-center/safety-state")
        resume = client.post("/control-center/queue/resume", json={"reason": "verification resume"})
        emergency = client.post("/control-center/emergency-stop-placeholder", json={"reason": "verification placeholder"})
        audit = client.get("/control-center/audit-events")

        payloads = [status.json(), state.json(), pause.json(), paused_state.json(), resume.json(), emergency.json()]
        passed = (
            status.status_code == 200
            and state.status_code == 200
            and pause.status_code == 200
            and resume.status_code == 200
            and emergency.status_code == 200
            and audit.status_code == 200
            and all(payload.get("live_execution_enabled") is False for payload in payloads if isinstance(payload, dict))
            and state.json().get("simulation_only") is True
            and pause.json().get("accepted") is True
            and paused_state.json().get("queue_paused") is True
            and resume.json().get("accepted") is True
            and emergency.json().get("live_execution_enabled") is False
            and len(audit.json()) >= 3
        )
        return show("Safety state, pause/resume, emergency placeholder, and audit events work", passed)
    except Exception as exc:
        return show("Safety state, pause/resume, emergency placeholder, and audit events work", False, str(exc))


def verify_frontend_integration() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        passed = (
            "/control-center/status" in api
            and "/control-center/safety-state" in api
            and "/control-center/audit-events" in api
            and "pauseSimulationQueue" in api
            and "resumeSimulationQueue" in api
            and "emergencyStopPlaceholder" in api
            and "ManualControlPanel" in shell
            and "SafetyLockPanel" in shell
            and "ControlAuditPanel" in shell
        )
        return show("Dashboard API helper and shell include manual controls", passed)
    except Exception as exc:
        return show("Dashboard API helper and shell include manual controls", False, str(exc))


def verify_safety() -> bool:
    try:
        source_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx"}
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for root in ("backend", "frontend")
            for path in (PROJECT_ROOT / root).rglob("*")
            if path.is_file()
            and path.suffix in source_suffixes
            and "node_modules" not in path.parts
            and ".next" not in path.parts
        )
        passed = (
            "mt5.order_send" not in text
            and "order_send(" not in text
            and "live_execution_enabled=True" not in text
            and "broker_execution_enabled=True" not in text
            and "real_trading_enabled=True" not in text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Phase 4 Day 6 Manual Override Verification")
    print("=" * 49)
    checks = [
        verify_backend_files(),
        verify_frontend_files(),
        verify_routes_registered(),
        verify_control_center_api(),
        verify_frontend_integration(),
        verify_safety(),
    ]
    print("=" * 49)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
