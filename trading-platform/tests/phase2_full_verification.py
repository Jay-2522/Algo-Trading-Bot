import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


class UnavailableData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("No market data required for full Phase 2 verification.")

    def close(self):
        return None


def verify_application_and_route_groups() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        route_groups = {
            "foundation": "/institutional/context/{symbol}",
            "sweeps": "/institutional/sweeps/{symbol}",
            "fvg": "/institutional/fvg/{symbol}",
            "order_blocks": "/institutional/order-blocks/{symbol}",
            "breakers": "/institutional/breakers/{symbol}",
            "structure_shift": "/institutional/structure-shift/{symbol}",
            "confluence": "/institutional/confluence/{symbol}",
            "alignment": "/institutional/alignment/{symbol}",
            "session": "/institutional/session/{symbol}",
            "entry_models": "/institutional/entry-models/{symbol}",
            "setup_validation": "/institutional/setup-validation/{symbol}",
            "simulation_decision": "/institutional/simulation-decision/{symbol}",
            "paper_trades": "/institutional/paper-trades/{symbol}",
            "position_management": "/institutional/position-management/{symbol}",
            "orchestration": "/institutional/orchestration/{symbol}",
            "reasoning": "/institutional/reasoning/{symbol}",
            "performance": "/institutional/performance/{symbol}",
            "dashboard": "/institutional/dashboard/{symbol}",
            "phase2_completion": "/institutional/phase2/completion-report",
            "demo": "/institutional/demo/{symbol}",
        }
        missing = [name for name, route in route_groups.items() if route not in routes]
        return show("FastAPI imports and all Phase 2 route groups are registered", not missing, ", ".join(missing))
    except Exception as exc:
        return show("FastAPI imports and all Phase 2 route groups are registered", False, str(exc))


def verify_completion_and_safety() -> bool:
    try:
        from backend.institutional_intelligence.phase2_safety_auditor import Phase2SafetyAuditor
        from backend.main import app

        client = TestClient(app)
        completion = client.get("/institutional/phase2/completion-report").json()
        platform_safety = client.get("/system/safety-scan").json()
        phase2_safety = Phase2SafetyAuditor().run_safety_audit()
        passed = (
            completion["overall_status"] == "READY"
            and completion["simulation_only"] is True
            and completion["live_execution_enabled"] is False
            and completion["dashboard_ready"] is True
            and completion["reasoning_ready"] is True
            and completion["orchestration_ready"] is True
            and completion["performance_ready"] is True
            and phase2_safety.passed is True
            and phase2_safety.order_send_found is False
            and phase2_safety.live_execution_enabled is False
            and platform_safety["passed"] is True
            and platform_safety["order_send_found"] is False
        )
        return show("Completion report and safety audits preserve simulation-only certification", passed)
    except Exception as exc:
        return show("Completion report and safety audits preserve simulation-only certification", False, str(exc))


def verify_client_dashboard_reasoning_json() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        client = TestClient(app)
        try:
            demo = client.get("/institutional/demo/XAUUSD")
            summary = client.get("/institutional/demo/summary/XAUUSD")
            modules = client.get("/institutional/demo/modules/XAUUSD")
            talking_points = client.get("/institutional/demo/talking-points/XAUUSD")
            dashboard = client.get("/institutional/dashboard/XAUUSD")
            reasoning = client.get("/institutional/reasoning/summary/XAUUSD")
        finally:
            institutional_routes.smc_service = original
        responses = [demo, summary, modules, talking_points, dashboard, reasoning]
        payloads = [response.json() for response in responses]
        serialized = json.dumps(payloads)
        demo_payload = payloads[0]
        talking_payload = payloads[3]
        passed = (
            all(response.status_code == 200 for response in responses)
            and demo_payload["safe_to_demo"] is True
            and demo_payload["summary"]["simulation_only"] is True
            and demo_payload["summary"]["live_execution_enabled"] is False
            and len(demo_payload["modules"]) == 19
            and len(payloads[2]) == 19
            and talking_payload["safe_to_demo"] is True
            and '"simulation_only": true' in serialized
            and '"live_execution_enabled": false' in serialized
        )
        return show("Demo, dashboard, and reasoning responses are concise JSON-safe outputs", passed)
    except Exception as exc:
        return show("Demo, dashboard, and reasoning responses are concise JSON-safe outputs", False, str(exc))


def verify_documentation() -> bool:
    files = [
        "docs/phase-2-final-summary.md",
        "docs/phase-2-client-demo-guide.md",
        "tests/phase2_full_verification.py",
    ]
    return show("Final architecture, demonstration, and verification artifacts exist", all(
        (PROJECT_ROOT / item).is_file() for item in files
    ))


def main() -> int:
    print("Full Phase 2 Institutional Intelligence Verification")
    print("=" * 55)
    checks = [
        verify_application_and_route_groups(),
        verify_completion_and_safety(),
        verify_client_dashboard_reasoning_json(),
        verify_documentation(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
