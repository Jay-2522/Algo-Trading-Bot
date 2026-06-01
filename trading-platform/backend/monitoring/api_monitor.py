from datetime import datetime, timezone
from typing import Any


class APIMonitor:
    """Summarize registered API routes by platform area."""

    def get_api_health(self, app: Any | None = None) -> dict:
        routes = self._routes(app)
        return {
            "total_routes": len(routes),
            "deployment_routes": len([route for route in routes if route.startswith("/deployment")]),
            "strategy_routes": len([route for route in routes if route.startswith("/strategy")]),
            "execution_routes": len([route for route in routes if "execution" in route or route.startswith("/trade-copier")]),
            "monitoring_routes": len([route for route in routes if route.startswith("/monitoring")]),
            "timestamp": datetime.now(timezone.utc),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _routes(self, app: Any | None) -> list[str]:
        if app is None:
            try:
                from backend.main import app as fastapi_app

                app = fastapi_app
            except Exception:
                return []
        return [
            route.path
            for route in app.routes
            if hasattr(route, "methods") and route.path not in {"/openapi.json", "/docs", "/redoc"}
        ]
