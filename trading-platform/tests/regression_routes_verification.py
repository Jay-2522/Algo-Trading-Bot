import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_GET_ROUTES = {
    "/health",
    "/status",
    "/market-data/timeframes",
    "/strategy/session",
    "/risk/status",
    "/risk/config",
    "/execution/status",
    "/mt5/status",
    "/mt5/health",
    "/database/status",
    "/ai/status",
    "/news/status",
    "/orchestration/status",
    "/backtesting/status",
    "/streaming/status",
    "/trading-loop/status",
    "/trade-journal/status",
    "/system/status",
    "/institutional/status",
    "/institutional/sweeps/{symbol}",
    "/institutional/fvg/{symbol}",
    "/institutional/order-blocks/{symbol}",
    "/institutional/breakers/{symbol}",
    "/institutional/structure-shift/{symbol}",
}

REQUIRED_WEBSOCKET_ROUTES = {"/ws/market/{symbol}"}


def main() -> int:
    print("FastAPI Route Regression Verification")
    print("=" * 37)

    try:
        from backend.main import app

        registered_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_routes)
        for path in sorted(REQUIRED_GET_ROUTES):
            status = "PASS" if path in registered_routes else "FAIL"
            print(f"[{status}] GET {path}")
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        missing_websockets = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        for path in sorted(REQUIRED_WEBSOCKET_ROUTES):
            status = "PASS" if path in registered_websockets else "FAIL"
            print(f"[{status}] WS  {path}")

        print("=" * 37)
        if missing or missing_websockets:
            all_missing = missing + missing_websockets
            print(f"FAIL - Missing routes: {', '.join(all_missing)}")
            return 1
        print("PASS")
        return 0
    except Exception as exc:
        print(f"[FAIL] FastAPI app import - {exc}")
        print("=" * 37)
        print("FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
