import asyncio
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError


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


def verify_routes() -> bool:
    try:
        from backend.main import app

        methods = {
            (route.path, method)
            for route in app.routes
            if hasattr(route, "methods")
            for method in route.methods
        }
        required = {
            ("/health", "GET"),
            ("/status", "GET"),
            ("/market-data/timeframes", "GET"),
            ("/strategy/session", "GET"),
            ("/risk/status", "GET"),
            ("/execution/status", "GET"),
            ("/mt5/status", "GET"),
            ("/database/status", "GET"),
            ("/ai/status", "GET"),
            ("/news/status", "GET"),
            ("/orchestration/status", "GET"),
            ("/backtesting/status", "GET"),
            ("/streaming/status", "GET"),
            ("/trading-loop/status", "GET"),
            ("/trading-loop/config", "GET"),
            ("/trading-loop/symbols", "GET"),
            ("/trading-loop/start", "POST"),
            ("/trading-loop/stop", "POST"),
            ("/trading-loop/pause", "POST"),
            ("/trading-loop/resume", "POST"),
            ("/trading-loop/run-once", "POST"),
            ("/trading-loop/symbols/{symbol}", "POST"),
            ("/trading-loop/symbols/{symbol}", "DELETE"),
        }
        missing = sorted(required - methods)
        print_result("FastAPI app imports with existing and trading-loop routes registered", not missing, str(missing))
        return not missing
    except Exception as exc:
        print_result("FastAPI app imports with existing and trading-loop routes registered", False, str(exc))
        return False


def verify_config_safety() -> bool:
    try:
        from backend.trading_loop.loop_config import get_default_loop_config
        from backend.trading_loop.loop_models import LoopConfig

        config = get_default_loop_config()
        interval_blocked = False
        live_blocked = False
        try:
            LoopConfig(interval_seconds=4)
        except ValidationError:
            interval_blocked = True
        try:
            LoopConfig(simulation_only=False, live_execution_enabled=True)
        except ValidationError:
            live_blocked = True
        passed = (
            config.simulation_only
            and not config.live_execution_enabled
            and config.interval_seconds >= 5
            and interval_blocked
            and live_blocked
        )
        print_result("LoopConfig enforces interval and simulation-only safety", passed)
        return passed
    except Exception as exc:
        print_result("LoopConfig enforces interval and simulation-only safety", False, str(exc))
        return False


def verify_state() -> bool:
    try:
        from backend.trading_loop.loop_state import LoopState

        state = LoopState()
        first_start = state.start()
        duplicate_start = state.start()
        paused = state.pause()
        resumed = state.resume()
        stopped = state.stop()
        passed = first_start and not duplicate_start and paused and resumed and stopped and not state.is_running()
        print_result("LoopState prevents duplicate starts and tracks lifecycle", passed)
        return passed
    except Exception as exc:
        print_result("LoopState prevents duplicate starts and tracks lifecycle", False, str(exc))
        return False


def stub_pipeline():
    from backend.orchestration.orchestration_models import OrchestrationDecision, PipelineResult

    return PipelineResult(
        success=True,
        symbol="XAUUSD",
        decision=OrchestrationDecision(
            symbol="XAUUSD",
            approved=False,
            final_action="AVOID",
            confidence=55,
            blocked_by="NEWS",
            reasons=["Verification-only simulated block."],
        ),
        steps_run=["verification_stub"],
    )


def verify_runner() -> bool:
    try:
        from backend.trading_loop.loop_runner import LoopRunner

        class StubOrchestrator:
            def run_symbol_pipeline(self, symbol: str, timeframe: str = "M15"):
                return stub_pipeline()

        result = asyncio.run(LoopRunner(orchestrator=StubOrchestrator()).run_symbol("XAUUSD"))
        passed = result.success and result.decision["execution_mode"] == "SIMULATION_ONLY"
        print_result("LoopRunner safely evaluates one symbol through simulation-only orchestration", passed)
        return passed
    except Exception as exc:
        print_result("LoopRunner safely evaluates one symbol through simulation-only orchestration", False, str(exc))
        return False


def verify_service_and_scheduler() -> bool:
    try:
        from backend.trading_loop.loop_models import LoopRunResult
        from backend.trading_loop.loop_service import TradingLoopService
        from backend.trading_loop.loop_state import LoopState

        class StubRunner:
            async def run_once(self, symbols: list[str]) -> list[LoopRunResult]:
                return [
                    LoopRunResult(
                        symbol=symbol,
                        success=True,
                        decision={"final_action": "AVOID", "execution_mode": "SIMULATION_ONLY"},
                    )
                    for symbol in symbols
                ]

        class NoPersistenceLogger:
            def log_event(self, event_type: str, message: str, metadata=None) -> dict:
                return {"persisted": False}

        async def exercise():
            service = TradingLoopService(
                state=LoopState(),
                runner=StubRunner(),
                loop_logger=NoPersistenceLogger(),
            )
            initial = service.get_status()
            manual = await service.run_once()
            started = await service.start_loop()
            duplicate = await service.start_loop()
            paused = await service.pause_loop()
            resumed = await service.resume_loop()
            stopped = await service.stop_loop()
            return initial, manual, started, duplicate, paused, resumed, stopped, service.get_status()

        initial, manual, started, duplicate, paused, resumed, stopped, final = asyncio.run(exercise())
        passed = (
            not initial.live_execution_enabled
            and initial.simulation_only
            and len(manual) == 1
            and started.success
            and not duplicate.success
            and paused.success
            and resumed.success
            and stopped.success
            and not final.running
            and final.total_runs >= 1
        )
        print_result("TradingLoopService controls one cancellable scheduler safely", passed)
        return passed
    except Exception as exc:
        print_result("TradingLoopService controls one cancellable scheduler safely", False, str(exc))
        return False


def verify_status_api() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/trading-loop/status")
        config = client.get("/trading-loop/config")
        symbols = client.get("/trading-loop/symbols")
        passed = (
            status.status_code == 200
            and status.json()["live_execution_enabled"] is False
            and status.json()["simulation_only"] is True
            and config.status_code == 200
            and config.json()["interval_seconds"] >= 5
            and symbols.status_code == 200
            and "XAUUSD" in symbols.json()["symbols"]
        )
        print_result("Trading-loop monitoring APIs return safe JSON status", passed)
        return passed
    except Exception as exc:
        print_result("Trading-loop monitoring APIs return safe JSON status", False, str(exc))
        return False


def main() -> int:
    print("Day 13 Background Trading Loop Verification")
    print("=" * 43)
    checks = [
        verify_path("backend/trading_loop", "trading_loop package exists", is_dir=True),
        verify_path("backend/trading_loop/loop_models.py", "loop_models.py exists"),
        verify_path("backend/trading_loop/loop_state.py", "loop_state.py exists"),
        verify_path("backend/trading_loop/loop_config.py", "loop_config.py exists"),
        verify_path("backend/trading_loop/loop_runner.py", "loop_runner.py exists"),
        verify_path("backend/trading_loop/loop_scheduler.py", "loop_scheduler.py exists"),
        verify_path("backend/trading_loop/loop_logger.py", "loop_logger.py exists"),
        verify_path("backend/trading_loop/loop_service.py", "loop_service.py exists"),
        verify_path("backend/api/trading_loop_routes.py", "trading_loop_routes.py exists"),
        verify_routes(),
        verify_config_safety(),
        verify_state(),
        verify_runner(),
        verify_service_and_scheduler(),
        verify_status_api(),
    ]
    print("=" * 43)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
