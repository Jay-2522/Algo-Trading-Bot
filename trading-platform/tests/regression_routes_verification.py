import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_GET_ROUTES = {
    "/health",
    "/status",
    "/market-data/timeframes",
    "/strategy/confluence/xauusd",
    "/strategy/fvg/xauusd",
    "/strategy/liquidity/xauusd",
    "/strategy/order-block/xauusd",
    "/strategy/regime/xauusd",
    "/strategy/session",
    "/strategy/session-context",
    "/strategy/signals",
    "/strategy/status",
    "/strategy/structure/xauusd",
    "/risk/status",
    "/risk/config",
    "/execution/status",
    "/execution-queue/status",
    "/mt5/status",
    "/mt5/health",
    "/multi-account-execution/status",
    "/trade-copier/status",
    "/trade-copier/batches",
    "/monitoring/status",
    "/client-acceptance/status",
    "/control-center/status",
    "/demo-execution/status",
    "/demo-execution/eligible-queue-items",
    "/demo-execution/audit-events",
    "/demo-mode/status",
    "/execution-confirmation/status",
    "/execution-confirmation/confirmations",
    "/execution-confirmation/reconciliation-summary",
    "/execution-confirmation/audit-events",
    "/execution-risk/status",
    "/execution-risk/policy",
    "/execution-risk/decisions",
    "/execution-risk/audit-events",
    "/execution-dashboard/status",
    "/execution-dashboard/overview",
    "/execution-dashboard/cards",
    "/execution-dashboard/summary",
    "/database/status",
    "/ai/status",
    "/accounts/status",
    "/accounts/allocation/status",
    "/dashboard/status",
    "/news/status",
    "/news/command-center",
    "/news/health",
    "/news/readiness-dashboard",
    "/news/phase7/status",
    "/news/supported-sources",
    "/news/supported-events",
    "/news/calendar-placeholder",
    "/news/calendar",
    "/news/upcoming-events",
    "/news/risk-context",
    "/news/filter/status",
    "/news/filter/current/xauusd",
    "/news/macro/status",
    "/news/macro/context",
    "/news/macro/xauusd-bias",
    "/news/headlines",
    "/news/headlines/recent",
    "/news/headlines/risk-context",
    "/news/unified-risk/status",
    "/news/unified-risk/xauusd",
    "/news/readiness",
    "/operational-intelligence/status",
    "/orchestration/status",
    "/phase3/status",
    "/portfolio/status",
    "/backtesting/status",
    "/replay/status",
    "/brokers/status",
    "/brokers/candles/status",
    "/webhooks/status",
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
    "/institutional/confluence/{symbol}",
    "/institutional/alignment/{symbol}",
    "/institutional/session/{symbol}",
    "/institutional/entry-models/{symbol}",
    "/institutional/setup-validation/{symbol}",
    "/institutional/simulation-decision/{symbol}",
    "/institutional/paper-trades/{symbol}",
    "/institutional/position-management/{symbol}",
    "/institutional/orchestration/{symbol}",
    "/institutional/reasoning/{symbol}",
    "/institutional/performance/{symbol}",
    "/institutional/dashboard/{symbol}",
    "/institutional/phase2/status",
    "/institutional/demo/{symbol}",
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
