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
        "backend/client_acceptance/__init__.py",
        "backend/client_acceptance/acceptance_models.py",
        "backend/client_acceptance/readiness_score_builder.py",
        "backend/client_acceptance/delivery_readiness_service.py",
        "backend/api/client_acceptance_routes.py",
        "docs/phase-4-day-10-progress.md",
    ]
    return show("Client acceptance package and documentation exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/client-acceptance/status",
            "/client-acceptance/readiness",
            "/client-acceptance/checklist",
            "/client-acceptance/remaining-items",
        }
        client = TestClient(app)
        status = client.get("/client-acceptance/status")
        readiness = client.get("/client-acceptance/readiness")
        checklist = client.get("/client-acceptance/checklist")
        remaining = client.get("/client-acceptance/remaining-items")
        readiness_json = readiness.json()
        checklist_labels = {item.get("label") for item in checklist.json()}
        remaining_items = remaining.json().get("remaining_items", [])
        passed = (
            expected <= routes
            and status.status_code == 200
            and readiness.status_code == 200
            and checklist.status_code == 200
            and remaining.status_code == 200
            and isinstance(readiness_json.get("overall_score"), int)
            and readiness_json.get("simulation_only") is True
            and readiness_json.get("live_execution_enabled") is False
            and {"Dashboard", "Monitoring", "Portfolio", "Demo Mode", "Control Center", "Webhooks", "Routing", "Allocation", "Queue"} <= checklist_labels
            and "MT5 Demo Execution Bridge" in remaining_items
            and "VPS Deployment" in remaining_items
        )
        return show("Client acceptance routes return readiness, checklist, and remaining work", passed)
    except Exception as exc:
        return show("Client acceptance routes return readiness, checklist, and remaining work", False, str(exc))


def verify_frontend_files() -> bool:
    files = [
        "frontend/components/dashboard/DeliveryReadinessPanel.tsx",
        "frontend/components/dashboard/AcceptanceChecklist.tsx",
        "frontend/components/dashboard/ReadinessScoreCard.tsx",
        "frontend/components/dashboard/RemainingWorkPanel.tsx",
    ]
    return show("Client acceptance dashboard components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_frontend_integration() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        passed = (
            "/client-acceptance/status" in api
            and "/client-acceptance/readiness" in api
            and "/client-acceptance/checklist" in api
            and "/client-acceptance/remaining-items" in api
            and "DeliveryReadinessPanel" in shell
        )
        return show("Dashboard API helper and shell include client acceptance layer", passed)
    except Exception as exc:
        return show("Dashboard API helper and shell include client acceptance layer", False, str(exc))


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
    print("Phase 4 Day 10 Client Acceptance Verification")
    print("=" * 52)
    checks = [
        verify_backend_files(),
        verify_routes_and_payloads(),
        verify_frontend_files(),
        verify_frontend_integration(),
        verify_safety(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
