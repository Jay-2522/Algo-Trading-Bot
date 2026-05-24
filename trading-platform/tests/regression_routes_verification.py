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
}


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

        print("=" * 37)
        if missing:
            print(f"FAIL - Missing routes: {', '.join(missing)}")
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
