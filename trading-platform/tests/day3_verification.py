import importlib
import sys
from datetime import datetime, timezone
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


def verify_import(module_name: str, label: str) -> bool:
    try:
        importlib.import_module(module_name)
        print_result(label, True)
        return True
    except Exception as exc:
        print_result(label, False, str(exc))
        return False


def verify_strategy_router_registered() -> bool:
    try:
        from backend.main import app

        paths = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required_paths = {
            "/strategy/trend/{symbol}",
            "/strategy/liquidity/{symbol}",
            "/strategy/structure/{symbol}",
            "/strategy/session",
            "/strategy/snapshot/{symbol}",
        }
        missing = sorted(required_paths - paths)
        print_result("strategy router registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("strategy router registered", False, str(exc))
        return False


def verify_session_manager_works() -> bool:
    try:
        from backend.strategy_engine.session_manager import SessionManager

        manager = SessionManager()
        info = manager.get_session_info(datetime(2026, 5, 25, 8, 0, tzinfo=timezone.utc))
        passed = info["current_session"] == "Asian" and "utc_ranges" in info
        print_result("session manager works", passed, str(info) if not passed else "")
        return passed
    except Exception as exc:
        print_result("session manager works", False, str(exc))
        return False


def verify_strategy_snapshot_model() -> bool:
    try:
        from backend.strategy_engine.signal_models import StrategySnapshot

        snapshot = StrategySnapshot(
            symbol="XAUUSD",
            timeframe="M15",
            confidence=0.5,
            trend_analysis={"trend": "bullish"},
            liquidity_analysis={"equal_highs": [], "equal_lows": []},
            structure_analysis={"bos": {"detected": False}, "choch": {"detected": False}},
            session_info={"current_session": "London", "high_liquidity": True},
            metadata={"verification": True},
        )
        payload = snapshot.to_dict()
        passed = payload["symbol"] == "XAUUSD" and payload["status"] == "analysis_ready"
        print_result("strategy snapshot model works", passed)
        return passed
    except Exception as exc:
        print_result("strategy snapshot model works", False, str(exc))
        return False


def verify_session_endpoint_without_mt5() -> bool:
    try:
        from fastapi.testclient import TestClient

        from backend.main import app

        response = TestClient(app).get("/strategy/session")
        payload = response.json()
        passed = response.status_code == 200 and "current_session" in payload
        print_result("strategy session endpoint works without MT5", passed, str(payload) if not passed else "")
        return passed
    except Exception as exc:
        print_result("strategy session endpoint works without MT5", False, str(exc))
        return False


def main() -> int:
    print("Day 3 Strategy Engine Verification")
    print("=" * 38)

    checks = [
        verify_path("backend/strategy_engine", "strategy_engine folder exists", is_dir=True),
        verify_path("backend/strategy_engine/trend_analyzer.py", "trend_analyzer exists"),
        verify_path("backend/strategy_engine/liquidity_detector.py", "liquidity_detector exists"),
        verify_path("backend/strategy_engine/structure_analyzer.py", "structure_analyzer exists"),
        verify_path("backend/strategy_engine/session_manager.py", "session_manager exists"),
        verify_path("backend/strategy_engine/signal_models.py", "signal_models exists"),
        verify_path("backend/strategy_engine/strategy_service.py", "strategy_service exists"),
        verify_path("backend/api/strategy_routes.py", "strategy_routes exists"),
        verify_strategy_router_registered(),
        verify_session_manager_works(),
        verify_import("backend.strategy_engine.trend_analyzer", "trend analyzer imports"),
        verify_import("backend.strategy_engine.liquidity_detector", "liquidity detector imports"),
        verify_import("backend.strategy_engine.structure_analyzer", "structure analyzer imports"),
        verify_strategy_snapshot_model(),
        verify_session_endpoint_without_mt5(),
    ]

    print("=" * 38)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

