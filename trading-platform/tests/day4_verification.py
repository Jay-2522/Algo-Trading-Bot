import importlib
import sys
from pathlib import Path


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


def verify_fastapi_import() -> bool:
    try:
        importlib.import_module("backend.main")
        print_result("FastAPI app imports", True)
        return True
    except Exception as exc:
        print_result("FastAPI app imports", False, str(exc))
        return False


def verify_route_registration() -> bool:
    try:
        from backend.main import app

        paths = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/risk/config",
        }
        missing = sorted(required - paths)
        print_result("existing and risk GET routes are registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("existing and risk GET routes are registered", False, str(exc))
        return False


def verify_risk_post_routes() -> bool:
    try:
        from backend.main import app

        posts = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "POST" in route.methods
        }
        required = {
            "/risk/calculate-position-size",
            "/risk/check-trade",
            "/risk/kill-switch/activate",
            "/risk/kill-switch/deactivate",
        }
        missing = sorted(required - posts)
        print_result("risk POST routes are registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("risk POST routes are registered", False, str(exc))
        return False


def verify_regression_route_responses() -> bool:
    try:
        from fastapi.testclient import TestClient

        from backend.main import app

        expected_payloads = {
            "/health": {
                "status": "healthy",
                "service": "AI Algorithmic Trading Platform",
            },
            "/status": {
                "status": "running",
                "environment": "development",
                "service": "AI Algorithmic Trading Platform",
                "version": "1.0.0",
            },
            "/market-data/timeframes": {
                "supported_timeframes": ["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
            },
        }
        client = TestClient(app)
        passed = True
        details: list[str] = []
        for path, expected in expected_payloads.items():
            response = client.get(path)
            if response.status_code != 200 or response.json() != expected:
                passed = False
                details.append(f"{path}={response.status_code}:{response.json()}")

        session_response = client.get("/strategy/session")
        if session_response.status_code != 200 or "current_session" not in session_response.json():
            passed = False
            details.append(f"/strategy/session={session_response.status_code}:{session_response.json()}")

        print_result("legacy endpoint responses remain available", passed, "; ".join(details))
        return passed
    except Exception as exc:
        print_result("legacy endpoint responses remain available", False, str(exc))
        return False


def verify_position_sizer() -> bool:
    try:
        from backend.risk_engine.position_sizer import PositionSizer

        result = PositionSizer().calculate_lot_size(
            account_balance=10000,
            risk_percent=1,
            stop_loss_pips=50,
            pip_value=10,
        )
        passed = result.lot_size == 0.2 and result.risk_amount == 100.0
        print_result("PositionSizer calculates valid lot size", passed, str(result) if not passed else "")
        return passed
    except Exception as exc:
        print_result("PositionSizer calculates valid lot size", False, str(exc))
        return False


def verify_drawdown_guard() -> bool:
    try:
        from backend.risk_engine.drawdown_guard import DrawdownGuard

        result = DrawdownGuard().check_daily_drawdown(3.0, 3.0)
        passed = result["allowed"] is False
        print_result("DrawdownGuard blocks at limit", passed)
        return passed
    except Exception as exc:
        print_result("DrawdownGuard blocks at limit", False, str(exc))
        return False


def verify_loss_guard() -> bool:
    try:
        from backend.risk_engine.loss_guard import ConsecutiveLossGuard

        result = ConsecutiveLossGuard().check_consecutive_losses(3, 3)
        passed = result["allowed"] is False
        print_result("ConsecutiveLossGuard blocks at limit", passed)
        return passed
    except Exception as exc:
        print_result("ConsecutiveLossGuard blocks at limit", False, str(exc))
        return False


def verify_spread_guard() -> bool:
    try:
        from backend.risk_engine.spread_guard import SpreadGuard

        result = SpreadGuard().check_spread(31, 30)
        passed = result["allowed"] is False
        print_result("SpreadGuard blocks high spread", passed)
        return passed
    except Exception as exc:
        print_result("SpreadGuard blocks high spread", False, str(exc))
        return False


def verify_kill_switch() -> bool:
    try:
        from backend.risk_engine.kill_switch import KillSwitch

        switch = KillSwitch()
        activated = switch.activate("verification")
        active_passed = switch.is_active() and activated["active"]
        deactivated = switch.deactivate()
        passed = active_passed and not switch.is_active() and not deactivated["active"]
        print_result("KillSwitch activates and deactivates", passed)
        return passed
    except Exception as exc:
        print_result("KillSwitch activates and deactivates", False, str(exc))
        return False


def verify_risk_service_status() -> bool:
    try:
        from backend.risk_engine.risk_service import RiskService

        status = RiskService().get_risk_status()
        passed = status.overall_status == "OPERATIONAL" and status.trading_enabled
        print_result("RiskService returns status", passed, str(status) if not passed else "")
        return passed
    except Exception as exc:
        print_result("RiskService returns status", False, str(exc))
        return False


def main() -> int:
    print("Day 4 Risk Management Engine Verification")
    print("=" * 43)

    checks = [
        verify_path("backend/risk_engine", "risk_engine folder exists", is_dir=True),
        verify_path("backend/risk_engine/risk_models.py", "risk_models.py exists"),
        verify_path("backend/risk_engine/risk_config.py", "risk_config.py exists"),
        verify_path("backend/risk_engine/position_sizer.py", "position_sizer.py exists"),
        verify_path("backend/risk_engine/drawdown_guard.py", "drawdown_guard.py exists"),
        verify_path("backend/risk_engine/loss_guard.py", "loss_guard.py exists"),
        verify_path("backend/risk_engine/spread_guard.py", "spread_guard.py exists"),
        verify_path("backend/risk_engine/kill_switch.py", "kill_switch.py exists"),
        verify_path("backend/risk_engine/risk_service.py", "risk_service.py exists"),
        verify_path("backend/risk_engine/validators.py", "validators.py exists"),
        verify_path("backend/api/risk_routes.py", "risk_routes.py exists"),
        verify_fastapi_import(),
        verify_route_registration(),
        verify_risk_post_routes(),
        verify_regression_route_responses(),
        verify_position_sizer(),
        verify_drawdown_guard(),
        verify_loss_guard(),
        verify_spread_guard(),
        verify_kill_switch(),
        verify_risk_service_status(),
    ]

    print("=" * 43)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
