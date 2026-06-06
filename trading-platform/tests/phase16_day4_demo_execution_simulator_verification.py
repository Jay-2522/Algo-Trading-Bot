import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_execution_simulator_models.py",
    "backend/mt5_demo/demo_execution_simulator_service.py",
    "docs/phase16-day4-demo-execution-simulator.md",
]

ROUTES = {
    "/mt5-demo/execution-simulator/status",
    "/mt5-demo/execution-simulator/run",
    "/mt5-demo/execution-simulator/latest",
    "/mt5-demo/execution-simulator/history",
}

AUTHORIZATION_REQUEST = {
    "environment": "DEMO",
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "max_demo_lot": 0.01,
}

DRY_RUN_REQUEST = {
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "entry_price": 1.12345,
    "stop_loss": 1.12,
    "take_profit": 1.13,
    "risk_decision_id": "risk-demo-approved-preview",
    "gate_decision_id": "gate-demo-ready-preview",
    "manual_confirmation": True,
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
        if key in {"would_send_to_mt5", "mt5_order_sent", "execution_allowed", "live_execution_enabled", "broker_execution_enabled"} and value is True:
            return False
    return True


def fake_spread(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "bid": 1.1234,
        "ask": 1.12345,
        "spread": 0.00005,
        "status": "OK",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Simulator models, service, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_simulation() -> bool:
    try:
        from backend.main import app
        from backend.api import mt5_demo_routes

        mt5_demo_routes.demo_order_preflight_service.market_data_service.get_symbol_spread = fake_spread
        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/execution-simulator/status")
        client.post("/mt5-demo/demo-authorization/request", json=AUTHORIZATION_REQUEST)
        dry_run = client.post("/mt5-demo/demo-order-dry-run/create", json=DRY_RUN_REQUEST).json()
        preflight_request = {
            "dry_run_id": dry_run["dry_run_id"],
            "symbol": "EURUSD",
            "action": "BUY",
            "lot": 0.01,
            "entry_price": 1.12345,
            "stop_loss": 1.12,
            "take_profit": 1.13,
        }
        preflight = client.post("/mt5-demo/preflight/run", json=preflight_request).json()
        simulation_request = {
            "preflight_id": preflight["preflight_id"],
            "symbol": "EURUSD",
            "action": "BUY",
            "lot": 0.01,
            "entry_price": 1.12345,
            "stop_loss": 1.12,
            "take_profit": 1.13,
        }
        simulation = client.post("/mt5-demo/execution-simulator/run", json=simulation_request)
        latest = client.get("/mt5-demo/execution-simulator/latest")
        history = client.get("/mt5-demo/execution-simulator/history")
        payloads = [status.json(), simulation.json(), latest.json(), history.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, simulation, latest, history])
            and preflight["validation_passed"] is True
            and simulation.json()["simulation_passed"] is True
            and simulation.json()["simulated_risk_amount"] is not None
            and simulation.json()["simulated_reward_amount"] is not None
            and simulation.json()["risk_reward_ratio"] is not None
            and simulation.json()["estimated_margin"] is not None
            and simulation.json()["simulated_order_payload"]["symbol"] == "EURUSD"
            and simulation.json()["would_send_to_mt5"] is False
            and simulation.json()["mt5_order_sent"] is False
            and simulation.json()["execution_allowed"] is False
            and simulation.json()["live_execution_enabled"] is False
            and simulation.json()["broker_execution_enabled"] is False
            and "ESTIMATED_VALUES_ONLY" in simulation.json()["warnings"]
            and "NO_ORDER_SENT" in simulation.json()["warnings"]
            and latest.json()["simulation_id"] == simulation.json()["simulation_id"]
            and isinstance(history.json(), list)
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Simulator routes run virtual execution safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Simulator routes run virtual execution safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 4 Demo Execution Simulator Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_simulation(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
