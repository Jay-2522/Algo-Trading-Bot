import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/replay/__init__.py",
        "backend/replay/replay_models.py",
        "backend/replay/historical_replay_loader.py",
        "backend/replay/replay_clock.py",
        "backend/replay/replay_window_builder.py",
        "backend/replay/replay_engine.py",
        "backend/replay/replay_event_logger.py",
        "backend/replay/replay_metrics.py",
        "backend/replay/replay_service.py",
        "backend/replay/replay_storage.py",
        "backend/api/replay_routes.py",
        "docs/phase-3-day-1-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/replay/status",
            "/replay/run/{symbol}",
            "/replay/recent",
            "/replay/result/{replay_id}",
            "/replay/metrics/{replay_id}",
            "/institutional/phase2/status",
            "/institutional/demo/{symbol}",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Replay package, router, and preserved Phase 2 routes exist", files_ok and routes_ok)


def verify_loader_clock_and_window() -> bool:
    try:
        from backend.replay.historical_replay_loader import HistoricalReplayLoader
        from backend.replay.replay_clock import ReplayClock
        from backend.replay.replay_window_builder import ReplayWindowBuilder

        loader = HistoricalReplayLoader()
        candles_a = loader.load_candles("XAUUSD", "M15", limit=30)
        candles_b = loader.load_candles("XAUUSD", "M15", limit=30)
        steps = ReplayClock().build_steps(candles_a, window_size=10, step_size=4, max_steps=3)
        window = ReplayWindowBuilder().build_window(candles_a, steps[0], 10)
        passed = (
            candles_a == candles_b
            and len(candles_a) == 30
            and all(key in candles_a[0] for key in {"timestamp", "open", "high", "low", "close", "volume"})
            and steps == [9, 13, 17]
            and len(window) == 10
            and window[-1] == candles_a[9]
            and candles_a[10] not in window
        )
        return show("Loader is deterministic and clock/window prevent lookahead bias", passed)
    except Exception as exc:
        return show("Loader is deterministic and clock/window prevent lookahead bias", False, str(exc))


def verify_engine_metrics_and_service() -> bool:
    try:
        from backend.replay.replay_engine import AdvancedHistoricalReplayEngine
        from backend.replay.replay_metrics import ReplayMetricsCalculator
        from backend.replay.replay_models import ReplayRequest, ReplayStatus
        from backend.replay.replay_service import ReplayService

        request = ReplayRequest(symbol="XAUUSD", timeframe="M15", window_size=30, step_size=10, max_steps=3)
        result = AdvancedHistoricalReplayEngine().run_replay(request)
        empty = ReplayMetricsCalculator().calculate_metrics([], "RPL-EMPTY", "XAUUSD", "M15")
        service = ReplayService()
        status = service.get_status()
        stored = service.run_replay("XAUUSD", request=request)
        passed = (
            result.total_steps == 3
            and all(step.candles_visible <= request.window_size for step in result.step_results)
            and result.simulation_only is True
            and result.live_execution_enabled is False
            and empty.total_steps == 0
            and isinstance(status, ReplayStatus)
            and status.simulation_only is True
            and status.live_execution_enabled is False
            and service.get_replay_result(stored.replay_id) is not None
        )
        return show("Replay engine, metrics, and service run safely with JSON-ready models", passed)
    except Exception as exc:
        return show("Replay engine, metrics, and service run safely with JSON-ready models", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/replay/status")
        run = client.post(
            "/replay/run/XAUUSD",
            json={"window_size": 30, "step_size": 10, "max_steps": 2, "simulation_only": True},
        )
        replay_id = run.json()["replay_id"]
        recent = client.get("/replay/recent")
        metrics = client.get(f"/replay/metrics/{replay_id}")
        readiness = client.get("/system/readiness").json()
        safety = client.get("/system/safety-scan").json()
        passed = (
            status.status_code == 200
            and run.status_code == 200
            and recent.status_code == 200
            and metrics.status_code == 200
            and status.json()["simulation_only"] is True
            and run.json()["simulation_only"] is True
            and run.json()["live_execution_enabled"] is False
            and metrics.json()["live_execution_enabled"] is False
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
            and any(module["module_name"] == "advanced_historical_replay" for module in readiness["modules"])
        )
        return show("Replay API is JSON-safe, registered, and preserves simulation-only safety", passed)
    except Exception as exc:
        return show("Replay API is JSON-safe, registered, and preserves simulation-only safety", False, str(exc))


def main() -> int:
    print("Phase 3 Day 1 Advanced Historical Replay Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_loader_clock_and_window(),
        verify_engine_metrics_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
