from collections import Counter

from fastapi import FastAPI

from backend.system_health.health_models import RouteAuditResult


REQUIRED_ROUTES = [
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
    "/system/readiness",
    "/system/safety-scan",
    "/system/routes",
    "/system/phase-report",
]


class RouteAuditor:
    """Validate the stable API surface without calling application services."""

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def audit(self) -> RouteAuditResult:
        routes = list(self.app.routes)
        paths = {route.path for route in routes}
        missing = sorted(set(REQUIRED_ROUTES) - paths)
        operation_keys: list[str] = []
        for route in routes:
            methods = getattr(route, "methods", None)
            if methods:
                operation_keys.extend(f"{method} {route.path}" for method in methods)
            else:
                operation_keys.append(f"WEBSOCKET {route.path}")
        duplicates = sorted(key for key, count in Counter(operation_keys).items() if count > 1)
        return RouteAuditResult(
            total_routes=len(routes),
            required_routes=REQUIRED_ROUTES,
            missing_routes=missing,
            duplicate_paths=duplicates,
            passed=not missing and not duplicates,
        )
