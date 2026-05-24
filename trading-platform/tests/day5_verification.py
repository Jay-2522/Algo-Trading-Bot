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


def verify_app_and_routes() -> bool:
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
        }
        missing = sorted(required - routes)
        print_result("FastAPI app imports and old/execution routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and old/execution routes registered", False, str(exc))
        return False


def valid_order():
    from backend.execution_engine.execution_models import OrderRequest

    return OrderRequest(
        symbol="XAUUSD",
        side="BUY",
        order_type="MARKET",
        lot_size=0.2,
        stop_loss=2290.0,
        take_profit=2320.0,
        comment="Day 5 simulation",
    )


def verify_validator_rejects_invalid() -> bool:
    try:
        from backend.execution_engine.execution_models import OrderRequest
        from backend.execution_engine.order_validator import OrderValidator

        result = OrderValidator().validate_order(
            OrderRequest(symbol="", side="HOLD", order_type="LIVE", lot_size=101)
        )
        passed = not result.valid and len(result.errors) >= 4
        print_result("OrderValidator rejects invalid order", passed, str(result) if not passed else "")
        return passed
    except Exception as exc:
        print_result("OrderValidator rejects invalid order", False, str(exc))
        return False


def verify_validator_accepts_valid() -> bool:
    try:
        from backend.execution_engine.order_validator import OrderValidator

        result = OrderValidator().validate_order(valid_order())
        passed = result.valid and not result.errors
        print_result("OrderValidator accepts valid order", passed, str(result) if not passed else "")
        return passed
    except Exception as exc:
        print_result("OrderValidator accepts valid order", False, str(exc))
        return False


def verify_simulated_executor() -> bool:
    try:
        from backend.execution_engine.simulated_executor import SimulatedExecutor

        result = SimulatedExecutor().execute(valid_order())
        passed = result.success and result.status == "SIMULATED_FILLED" and result.execution_mode == "SIMULATION"
        print_result("SimulatedExecutor returns SIMULATED_FILLED", passed)
        return passed
    except Exception as exc:
        print_result("SimulatedExecutor returns SIMULATED_FILLED", False, str(exc))
        return False


def verify_mt5_disabled() -> bool:
    try:
        from backend.execution_engine.mt5_executor import MT5Executor

        result = MT5Executor().execute(valid_order())
        passed = (
            not result.success
            and result.status == "REAL_EXECUTION_DISABLED"
            and "disabled" in result.message.lower()
        )
        print_result("MT5Executor does not execute real trade", passed)
        return passed
    except Exception as exc:
        print_result("MT5Executor does not execute real trade", False, str(exc))
        return False


def verify_execution_logger() -> bool:
    try:
        from backend.execution_engine.execution_logger import ExecutionLogger

        logger = ExecutionLogger()
        logger.log_event("exec-1", "TEST", "verification event")
        passed = len(logger.get_logs("exec-1")) == 1 and len(logger.get_recent_logs()) == 1
        print_result("ExecutionLogger records logs", passed)
        return passed
    except Exception as exc:
        print_result("ExecutionLogger records logs", False, str(exc))
        return False


def verify_execution_service() -> bool:
    try:
        from backend.execution_engine.execution_service import ExecutionService
        from backend.risk_engine.risk_service import RiskService

        service = ExecutionService(risk_service=RiskService())
        result = service.simulate_order(valid_order())
        logs = service.get_execution_logs(result.execution_id)
        passed = result.status == "SIMULATED_FILLED" and len(logs) == 3
        print_result("ExecutionService simulate_order works", passed, str(result) if not passed else "")
        return passed
    except Exception as exc:
        print_result("ExecutionService simulate_order works", False, str(exc))
        return False


def verify_risk_blocks_simulation() -> bool:
    try:
        from backend.execution_engine.execution_service import ExecutionService
        from backend.risk_engine.risk_service import RiskService

        risk_service = RiskService()
        risk_service.activate_kill_switch("Day 5 verification")
        result = ExecutionService(risk_service=risk_service).simulate_order(valid_order())
        risk_service.deactivate_kill_switch()
        passed = not result.success and result.status == "RISK_BLOCKED"
        print_result("Risk service blocks unsafe simulation", passed)
        return passed
    except Exception as exc:
        print_result("Risk service blocks unsafe simulation", False, str(exc))
        return False


def main() -> int:
    print("Day 5 Execution Engine Verification")
    print("=" * 39)

    checks = [
        verify_path("backend/execution_engine", "execution_engine folder exists", is_dir=True),
        verify_path("backend/execution_engine/execution_models.py", "execution_models.py exists"),
        verify_path("backend/execution_engine/order_validator.py", "order_validator.py exists"),
        verify_path("backend/execution_engine/execution_logger.py", "execution_logger.py exists"),
        verify_path("backend/execution_engine/simulated_executor.py", "simulated_executor.py exists"),
        verify_path("backend/execution_engine/mt5_executor.py", "mt5_executor.py exists"),
        verify_path("backend/execution_engine/execution_service.py", "execution_service.py exists"),
        verify_path("backend/execution_engine/validators.py", "validators.py exists"),
        verify_path("backend/api/execution_routes.py", "execution_routes.py exists"),
        verify_app_and_routes(),
        verify_validator_rejects_invalid(),
        verify_validator_accepts_valid(),
        verify_simulated_executor(),
        verify_mt5_disabled(),
        verify_execution_logger(),
        verify_execution_service(),
        verify_risk_blocks_simulation(),
    ]

    print("=" * 39)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
