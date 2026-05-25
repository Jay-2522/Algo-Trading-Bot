import sys
from pathlib import Path

from fastapi.testclient import TestClient


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

        get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        websocket_routes = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
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
            "/backtesting/status",
            "/streaming/status",
            "/streaming/tick/{symbol}",
            "/streaming/clients",
        }
        missing = sorted(required_get - get_routes)
        missing_ws = "/ws/market/{symbol}" not in websocket_routes
        passed = not missing and not missing_ws
        detail = ", ".join(missing + (["/ws/market/{symbol}"] if missing_ws else []))
        print_result("FastAPI app imports with old, streaming, and WebSocket routes registered", passed, detail)
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with old, streaming, and WebSocket routes registered", False, str(exc))
        return False


def verify_stream_state() -> bool:
    try:
        from backend.streaming.stream_state import StreamState

        state = StreamState()
        initial = state.get_status()
        state.start_stream("xauusd")
        active = state.is_streaming("XAUUSD")
        state.stop_stream("XAUUSD")
        passed = (
            initial.active_streams == []
            and initial.mode == "SIMULATION_OR_MT5_READ_ONLY"
            and active
            and not state.is_streaming("XAUUSD")
        )
        print_result("StreamState safely starts and stops streams", passed)
        return passed
    except Exception as exc:
        print_result("StreamState safely starts and stops streams", False, str(exc))
        return False


def verify_tick_fallback() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
        from backend.streaming.tick_streamer import TickStreamer

        tick = TickStreamer(MT5ConnectionManager(mt5_module=None)).get_tick("XAUUSD")
        passed = (
            tick.source == "SIMULATION_FALLBACK"
            and tick.symbol == "XAUUSD"
            and tick.ask > tick.bid
            and tick.spread > 0
        )
        print_result("TickStreamer returns simulated tick when MT5 is unavailable", passed)
        return passed
    except Exception as exc:
        print_result("TickStreamer returns simulated tick when MT5 is unavailable", False, str(exc))
        return False


def verify_market_stream_service() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
        from backend.streaming.market_stream_service import MarketStreamService
        from backend.streaming.tick_streamer import TickStreamer

        class NoPersistenceLogger:
            def log_event(self, event_type: str, symbol: str, message: str, metadata=None) -> dict:
                return {"persisted": False}

        service = MarketStreamService(
            tick_streamer=TickStreamer(MT5ConnectionManager(mt5_module=None)),
            stream_logger=NoPersistenceLogger(),
        )
        status = service.get_status()
        start = service.start_stream("XAUUSD")
        tick = service.get_tick_once("XAUUSD")
        stop = service.stop_stream("XAUUSD")
        passed = (
            status.connected_clients == 0
            and status.status == "operational"
            and start.success
            and tick.source == "SIMULATION_FALLBACK"
            and stop.success
        )
        print_result("MarketStreamService status and controls work safely", passed)
        return passed
    except Exception as exc:
        print_result("MarketStreamService status and controls work safely", False, str(exc))
        return False


def verify_api_responses() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/streaming/status")
        tick = client.get("/streaming/tick/XAUUSD")
        clients = client.get("/streaming/clients")
        passed = (
            status.status_code == 200
            and status.json()["mode"] == "SIMULATION_OR_MT5_READ_ONLY"
            and tick.status_code == 200
            and tick.json()["source"] in {"SIMULATION_FALLBACK", "MT5_READ_ONLY"}
            and clients.status_code == 200
            and clients.json()["connected_clients"] == 0
        )
        print_result("Streaming REST endpoints return JSON-safe responses", passed)
        return passed
    except Exception as exc:
        print_result("Streaming REST endpoints return JSON-safe responses", False, str(exc))
        return False


def main() -> int:
    print("Day 12 Live Streaming Engine Verification")
    print("=" * 41)
    checks = [
        verify_path("backend/streaming", "streaming package exists", is_dir=True),
        verify_path("backend/streaming/stream_models.py", "stream_models.py exists"),
        verify_path("backend/streaming/connection_manager.py", "connection_manager.py exists"),
        verify_path("backend/streaming/tick_streamer.py", "tick_streamer.py exists"),
        verify_path("backend/streaming/market_stream_service.py", "market_stream_service.py exists"),
        verify_path("backend/streaming/stream_state.py", "stream_state.py exists"),
        verify_path("backend/streaming/stream_logger.py", "stream_logger.py exists"),
        verify_path("backend/api/streaming_routes.py", "streaming_routes.py exists"),
        verify_routes(),
        verify_stream_state(),
        verify_tick_fallback(),
        verify_market_stream_service(),
        verify_api_responses(),
    ]
    print("=" * 41)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
