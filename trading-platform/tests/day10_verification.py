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


def safe_context():
    from backend.orchestration.pipeline_context import PipelineContext

    context = PipelineContext(symbol="XAUUSD", timeframe="M15")
    context.strategy_snapshot = {"trend_analysis": {"trend": "bullish"}}
    context.ai_decision = {"action": "BUY", "approved": True, "confidence": 88.0}
    context.news_status = {
        "trading_allowed": False,
        "risk_level": "BLOCKED",
        "reason": "Active high-impact blackout.",
    }
    context.risk_status = {"allowed": True, "risk_level": "LOW", "reasons": []}
    return context


def verify_routes() -> bool:
    try:
        from backend.main import app

        get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        required_get = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
            "/ai/status",
            "/news/status",
            "/orchestration/status",
            "/orchestration/symbols",
            "/orchestration/config",
            "/orchestration/last-decision/{symbol}",
        }
        post_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "POST" in route.methods
        }
        delete_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "DELETE" in route.methods
        }
        missing = sorted(
            (required_get - get_routes)
            | ({"/orchestration/run/{symbol}", "/orchestration/symbols/{symbol}"} - post_routes)
            | ({"/orchestration/symbols/{symbol}"} - delete_routes)
        )
        print_result("FastAPI app imports and orchestration/old routes registered", not missing, ", ".join(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports and orchestration/old routes registered", False, str(exc))
        return False


def verify_pipeline_context() -> bool:
    try:
        context = safe_context()
        context.add_error("market_data", "read feed unavailable")
        passed = context.to_dict()["errors"] == ["market_data: read feed unavailable"]
        print_result("PipelineContext works", passed)
        return passed
    except Exception as exc:
        print_result("PipelineContext works", False, str(exc))
        return False


def verify_decision_coordinator() -> bool:
    try:
        from backend.orchestration.decision_coordinator import DecisionCoordinator

        decision = DecisionCoordinator().create_final_decision(safe_context())
        passed = not decision.approved and decision.final_action == "AVOID" and decision.blocked_by == "NEWS"
        print_result("DecisionCoordinator blocks when news blocks", passed, str(decision) if not passed else "")
        return passed
    except Exception as exc:
        print_result("DecisionCoordinator blocks when news blocks", False, str(exc))
        return False


def verify_symbol_monitor() -> bool:
    try:
        from backend.orchestration.symbol_monitor import SymbolMonitor

        monitor = SymbolMonitor()
        passed = monitor.get_symbols() == ["XAUUSD"] and monitor.get_config().simulation_only
        print_result("SymbolMonitor has XAUUSD by default", passed)
        return passed
    except Exception as exc:
        print_result("SymbolMonitor has XAUUSD by default", False, str(exc))
        return False


def verify_service() -> bool:
    try:
        from backend.orchestration.orchestration_models import PipelineResult
        from backend.orchestration.orchestrator_service import OrchestratorService

        class StubRunner:
            def collect_context(self, symbol: str, timeframe: str):
                return safe_context(), [
                    "collect_market_data",
                    "run_strategy_analysis",
                    "run_ai_decision",
                    "run_news_filter",
                    "run_risk_check",
                    "prepare_execution_decision",
                ]

            def simulate_if_approved(self, context, decision):
                raise AssertionError("Simulation must not run while news blocks.")

        class StubLogger:
            def log_pipeline_result(self, result: PipelineResult) -> dict:
                return {"persisted": False, "message": "Verification uses no database writes."}

        service = OrchestratorService(pipeline_runner=StubRunner(), orchestration_logger=StubLogger())
        status = service.get_orchestration_status()
        result = service.run_symbol_pipeline("XAUUSD")
        passed = (
            status["mode"] == "SIMULATION_ONLY"
            and not status["live_execution_enabled"]
            and isinstance(result, PipelineResult)
            and result.decision.blocked_by == "NEWS"
        )
        print_result("OrchestratorService status and pipeline work without live dependencies", passed)
        return passed
    except Exception as exc:
        print_result("OrchestratorService status and pipeline work without live dependencies", False, str(exc))
        return False


def main() -> int:
    print("Day 10 Trading Orchestration Verification")
    print("=" * 40)
    checks = [
        verify_path("backend/orchestration", "orchestration folder exists", is_dir=True),
        verify_path("backend/orchestration/orchestration_models.py", "orchestration_models.py exists"),
        verify_path("backend/orchestration/pipeline_context.py", "pipeline_context.py exists"),
        verify_path("backend/orchestration/pipeline_runner.py", "pipeline_runner.py exists"),
        verify_path("backend/orchestration/decision_coordinator.py", "decision_coordinator.py exists"),
        verify_path("backend/orchestration/symbol_monitor.py", "symbol_monitor.py exists"),
        verify_path("backend/orchestration/orchestration_logger.py", "orchestration_logger.py exists"),
        verify_path("backend/orchestration/orchestrator_service.py", "orchestrator_service.py exists"),
        verify_path("backend/api/orchestration_routes.py", "orchestration_routes.py exists"),
        verify_routes(),
        verify_pipeline_context(),
        verify_decision_coordinator(),
        verify_symbol_monitor(),
        verify_service(),
    ]
    print("=" * 40)
    all_passed = all(checks)
    print("PASS" if all_passed else "FAIL")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
