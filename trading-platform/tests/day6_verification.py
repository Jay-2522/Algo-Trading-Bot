import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str) -> bool:
    passed = (PROJECT_ROOT / path).is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def verify_app_routes() -> bool:
    try:
        from backend.main import app

        routes = {
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
            "/execution/status",
            "/mt5/status",
            "/mt5/health",
        }
        missing = sorted(required - routes)
        print_result("FastAPI app imports and MT5/old routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and MT5/old routes registered", False, str(exc))
        return False


def verify_data_models() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_data_models import (
            MT5AccountInfo,
            MT5ConnectionStatus,
            MT5HealthStatus,
            MT5PositionInfo,
            MT5SymbolInfo,
            MT5TickInfo,
        )

        connection = MT5ConnectionStatus(
            connected=False,
            initialized=False,
            terminal_available=False,
            message="Not available.",
            timestamp="2026-05-25T00:00:00+00:00",
        )
        objects = [
            MT5AccountInfo(),
            MT5SymbolInfo(symbol="XAUUSD"),
            MT5TickInfo(symbol="XAUUSD"),
            MT5PositionInfo(),
            MT5HealthStatus(
                connection=connection,
                account_available=False,
                terminal_info_available=False,
                symbols_checked=[],
                overall_status="UNAVAILABLE",
                timestamp="2026-05-25T00:00:00+00:00",
            ),
        ]
        passed = all(item.model_dump(mode="json") is not None for item in objects)
        print_result("MT5 data models can be instantiated", passed)
        return passed
    except Exception as exc:
        print_result("MT5 data models can be instantiated", False, str(exc))
        return False


def verify_missing_mt5_is_safe() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager

        status = MT5ConnectionManager(mt5_module=None).initialize()
        passed = (
            not status.connected
            and not status.initialized
            and not status.terminal_available
            and "unavailable" in status.message.lower()
        )
        print_result("MT5ConnectionManager handles missing MT5 safely", passed, str(status) if not passed else "")
        return passed
    except Exception as exc:
        print_result("MT5ConnectionManager handles missing MT5 safely", False, str(exc))
        return False


def verify_health_service_is_structured() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
        from backend.broker_integrations.mt5.mt5_health_service import MT5HealthService

        service = MT5HealthService(MT5ConnectionManager(mt5_module=None))
        health = service.get_health_status(["XAUUSD"])
        payload = health.model_dump(mode="json")
        passed = (
            payload["overall_status"] == "UNAVAILABLE"
            and payload["connection"]["connected"] is False
            and payload["symbols_checked"] == []
        )
        print_result("MT5HealthService returns structured response", passed, str(payload) if not passed else "")
        return passed
    except Exception as exc:
        print_result("MT5HealthService returns structured response", False, str(exc))
        return False


def main() -> int:
    print("Day 6 MT5 Broker Data Layer Verification")
    print("=" * 42)

    checks = [
        verify_path("backend/broker_integrations/mt5/mt5_connection_manager.py", "mt5_connection_manager.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_account_service.py", "mt5_account_service.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_symbol_service.py", "mt5_symbol_service.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_tick_service.py", "mt5_tick_service.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_position_service.py", "mt5_position_service.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_health_service.py", "mt5_health_service.py exists"),
        verify_path("backend/broker_integrations/mt5/mt5_data_models.py", "mt5_data_models.py exists"),
        verify_path("backend/api/mt5_routes.py", "mt5_routes.py exists"),
        verify_app_routes(),
        verify_data_models(),
        verify_missing_mt5_is_safe(),
        verify_health_service_is_structured(),
    ]

    print("=" * 42)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

