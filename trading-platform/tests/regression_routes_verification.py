import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_GET_ROUTES = {
    "/health",
    "/status",
    "/market-data/timeframes",
    "/strategy/analyze/eurusd",
    "/strategy/confluence/xauusd",
    "/strategy/eurusd/indicator-context",
    "/strategy/eurusd/confluence",
    "/strategy/eurusd/fvg",
    "/strategy/eurusd/liquidity",
    "/strategy/eurusd/order-block",
    "/strategy/eurusd/regime",
    "/strategy/eurusd/session-context",
    "/strategy/eurusd/structure",
    "/strategy/fvg/xauusd",
    "/strategy/liquidity/xauusd",
    "/strategy/order-block/xauusd",
    "/strategy/regime/xauusd",
    "/strategy/session",
    "/strategy/session-context",
    "/strategy/signals",
    "/strategy/status",
    "/strategy/structure/xauusd",
    "/strategy-execution-bridge/decisions",
    "/strategy-execution-bridge/demo-approval/approvals",
    "/strategy-execution-bridge/demo-approval/candidates",
    "/strategy-execution-bridge/demo-approval/history",
    "/strategy-execution-bridge/demo-approval/status",
    "/strategy-execution-bridge/e2e/flows",
    "/strategy-execution-bridge/e2e/status",
    "/strategy-execution-bridge/final-demo-execution/executions",
    "/strategy-execution-bridge/final-demo-execution/status",
    "/strategy-execution-bridge/operations/health",
    "/strategy-execution-bridge/operations/overview",
    "/strategy-execution-bridge/operations/pipeline-events",
    "/strategy-execution-bridge/operations/readiness",
    "/strategy-execution-bridge/operations/recent-executions",
    "/strategy-execution-bridge/operations/recent-rejections",
    "/strategy-execution-bridge/operations/status",
    "/strategy-execution-bridge/status",
    "/risk/status",
    "/risk/config",
    "/execution/status",
    "/execution-queue/status",
    "/mt5/status",
    "/mt5/health",
    "/multi-account-execution/status",
    "/trade-copier/status",
    "/trade-copier/batches",
    "/trade-copier/execution-results",
    "/monitoring/status",
    "/monitoring/health",
    "/monitoring/metrics",
    "/monitoring/processes",
    "/monitoring/apis",
    "/monitoring/mt5",
    "/monitoring/logs",
    "/monitoring/logs/errors",
    "/monitoring/logs/warnings",
    "/client-acceptance/status",
    "/client-analytics/status",
    "/client-analytics/overview",
    "/client-analytics/symbols",
    "/client-analytics/symbols/{symbol}",
    "/client-analytics/sessions",
    "/client-analytics/risk",
    "/client-analytics/snapshots/latest",
    "/client-analytics/accounts",
    "/client-analytics/accounts/master",
    "/client-analytics/accounts/copiers",
    "/client-analytics/accounts/sync-status",
    "/client-analytics/accounts/{account_id}",
    "/client-analytics/executive/status",
    "/client-analytics/executive/summary",
    "/client-analytics/executive/readiness",
    "/client-analytics/executive/instruments",
    "/client-analytics/executive/system-health",
    "/client-analytics/executive/completion",
    "/client-analytics/strategy/status",
    "/client-analytics/strategy/overview",
    "/client-analytics/strategy/performance",
    "/client-analytics/strategy/performance/{symbol}",
    "/client-analytics/strategy/rankings",
    "/client-analytics/strategy/session-efficiency",
    "/client-analytics/strategy/comparison",
    "/client-analytics/reports/status",
    "/client-analytics/reports/daily",
    "/client-analytics/reports/weekly",
    "/client-analytics/reports/symbol/{symbol}",
    "/client-analytics/reports/risk",
    "/client-analytics/reports/trade-journal",
    "/client-analytics/reports/export/json",
    "/client-analytics/reports/export/csv",
    "/control-center/status",
    "/demo-execution/status",
    "/demo-execution/eligible-queue-items",
    "/demo-execution/audit-events",
    "/demo-mode/status",
    "/deployment/status",
    "/deployment/readiness",
    "/deployment/checklist",
    "/deployment/blockers",
    "/deployment/warnings",
    "/deployment/runtime/status",
    "/deployment/runtime/backend",
    "/deployment/runtime/frontend",
    "/deployment/runtime/healthcheck",
    "/deployment/runtime/mt5-notes",
    "/deployment/runtime/audit-events",
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
    "/nifty50/status",
    "/nifty50/instrument",
    "/nifty50/brokers",
    "/nifty50/brokers/recommended",
    "/nifty50/session",
    "/nifty50/market-data/snapshot",
    "/nifty50/readiness",
    "/nifty50/blockers",
    "/nifty50/strategy/status",
    "/nifty50/strategy/liquidity",
    "/nifty50/strategy/structure",
    "/nifty50/strategy/fvg",
    "/nifty50/strategy/order-block",
    "/nifty50/strategy/snapshot",
    "/operational-intelligence/status",
    "/orchestration/status",
    "/phase3/status",
    "/portfolio/status",
    "/production-readiness/status",
    "/production-readiness/report",
    "/production-readiness/assessment",
    "/production-readiness/blockers",
    "/production-readiness/recommendations",
    "/backtesting/status",
    "/backup/status",
    "/backup/strategy",
    "/backup/recovery",
    "/backup/rollback",
    "/backup/incident-response",
    "/replay/status",
    "/security/status",
    "/security/secrets-audit",
    "/security/access-policy",
    "/security/blockers",
    "/security/warnings",
    "/security/audit-events",
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
